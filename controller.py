#!/usr/bin/env python3
import os
import socket
import time
import threading
import json
import re
import PIL.Image
import google.generativeai as genai
import signal
import sys
import atexit

class PokemonGameController:
    def __init__(self, config_path='config.json'):
        # Cleanup control
        self._cleanup_done = False
        self._cleanup_lock = threading.Lock()
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Set up Gemini API client
        genai.configure(api_key=self.config['api_key'])
        self.model = genai.GenerativeModel(self.config['model_name'])
        
        # Initialize socket server
        self.server_socket = None
        self.setup_socket()
        
        # Game state variables
        self.notepad_path = self.config['notepad_path']
        self.screenshot_path = self.config['screenshot_path']
        self.current_client = None
        self.running = True
        self.last_decision_time = 0
        self.decision_cooldown = self.config['decision_cooldown']
        self.client_threads = []
        self.debug_mode = self.config.get('debug_mode', False)
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.notepad_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.screenshot_path), exist_ok=True)
        
        # Initialize notepad if it doesn't exist
        self.initialize_notepad()
        
        print(f"Controller initialized with:")
        print(f"API Key: {self.config['api_key'][:5]}...{self.config['api_key'][-3:]}")
        print(f"Model: {self.config['model_name']}")
        print(f"Notepad path: {self.notepad_path}")
        print(f"Screenshot path: {self.screenshot_path}")
        print(f"Debug mode: {self.debug_mode}")
        
        # Set up signal handlers for proper shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Register cleanup function
        atexit.register(self.cleanup)

    def setup_socket(self):
        """Set up the socket server with proper error handling"""
        # Kill any process using our port
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.bind((self.config['host'], self.config['port']))
            test_socket.close()
        except socket.error:
            print(f"Port {self.config['port']} is already in use. Trying to release it...")
            os.system(f"lsof -ti:{self.config['port']} | xargs kill -9")
            time.sleep(1)  # Wait for port to be released
            
        try:
            # Initialize socket server
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config['host'], self.config['port']))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1)  # Non-blocking socket with timeout
        except socket.error as e:
            print(f"Socket setup error: {e}")
            sys.exit(1)

    def signal_handler(self, sig, frame):
        """Handle termination signals"""
        print(f"\nReceived signal {sig}. Shutting down server...")
        self.running = False
        self.cleanup()
        sys.exit(0)
        
    def cleanup(self):
        """Clean up resources properly - runs only once"""
        with self._cleanup_lock:
            if self._cleanup_done:
                return
            self._cleanup_done = True
            
            print("Cleaning up resources...")
            
            # Close client connections
            if self.current_client:
                try:
                    self.current_client.close()
                    self.current_client = None
                except:
                    pass
            
            # Close server socket
            if self.server_socket:
                try:
                    self.server_socket.close()
                    self.server_socket = None
                except:
                    pass
                
            print("Cleanup complete.")
            
            # Give GRPC time to shut down (fixes the timeout warning)
            time.sleep(0.5)

    def load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Always use absolute paths
            if 'notepad_path' in config and not os.path.isabs(config['notepad_path']):
                config['notepad_path'] = os.path.abspath(config['notepad_path'])
                
            if 'screenshot_path' in config and not os.path.isabs(config['screenshot_path']):
                config['screenshot_path'] = os.path.abspath(config['screenshot_path'])
                
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            # Return default configuration
            return {
                'api_key': 'YOUR_GEMINI_API_KEY',
                'model_name': 'gemini-2.0-flash',
                'host': '127.0.0.1',
                'port': 8888,
                'notepad_path': os.path.abspath('notepad.txt'),
                'screenshot_path': os.path.abspath('data/screenshots/screenshot.png'),
                'decision_cooldown': 3,  # 3 seconds between LLM decisions
                'debug_mode': True
            }

    def initialize_notepad(self):
        """Initialize the notepad file with a minimal structure"""
        if not os.path.exists(self.notepad_path):
            os.makedirs(os.path.dirname(self.notepad_path), exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(self.notepad_path, 'w') as f:
                f.write("# Pokémon Game AI Notepad\n\n")
                f.write(f"Game started: {timestamp}\n\n")
                f.write("## Game Status\n")
                f.write("- Just started the game\n\n")
                f.write("## Objectives\n")
                f.write("- Progress through the game\n")
                f.write("- Make strategic decisions\n\n")

    def read_notepad(self):
        """Read the current notepad content"""
        try:
            with open(self.notepad_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading notepad: {e}")
            return "Error reading notepad"

    def update_notepad(self, new_content):
        """Update the notepad with new content"""
        try:
            with open(self.notepad_path, 'w') as f:
                f.write(new_content)
            print("Notepad updated")
        except Exception as e:
            print(f"Error updating notepad: {e}")

    def summarize_notepad_if_needed(self):
        """Summarize notepad if it gets too long, keeping the structure intact"""
        notepad_content = self.read_notepad()
        
        # If notepad is over 10KB, ask LLM to summarize it
        if len(notepad_content) > 10000:
            print("Notepad is getting too long, summarizing...")
            
            try:
                summarize_prompt = """
                Please summarize the following game notes into a more concise format.
                
                Maintain these exact sections:
                - Long-term Goals
                - Current Objectives 
                - Team Status
                - Inventory
                - Game Progress
                
                Condense repetitive information but preserve all important game state details:
                - Current location and next destination
                - All Pokémon on the team with their levels, types and moves
                - Important items in the inventory
                - Badges collected and significant events
                - Current strategy and immediate plans
                
                Format the response as a well-structured markdown document with clear headings and bullet points.
                
                Here are the notes to summarize:
                
                """
                
                response = self.model.generate_content(
                    summarize_prompt + notepad_content
                )
                
                if response:
                    summarized_content = response.text
                    
                    # Add a note about summarization
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    summarized_content += f"\n\n## Note\nNotepad was summarized at {timestamp} to reduce size while preserving important information."
                    
                    self.update_notepad(summarized_content)
                    print("Notepad summarized successfully")
            except Exception as e:
                print(f"Error summarizing notepad: {e}")

    def process_screenshot(self, screenshot_path=None):
        """Process the latest screenshot with Gemini Vision"""
        current_time = time.time()
        
        # Check if we should make a new decision based on cooldown
        if current_time - self.last_decision_time < self.decision_cooldown:
            return None  # Skip decision making during cooldown
            
        try:
            # Read the notepad
            notepad_content = self.read_notepad()
            
            # Use provided path or default
            path_to_use = screenshot_path if screenshot_path else self.screenshot_path
            
            print(f"Loading screenshot from: {path_to_use}")
            if not os.path.exists(path_to_use):
                print(f"WARNING: Screenshot not found at {path_to_use}")
                return None
                
            # Load the screenshot
            image = PIL.Image.open(path_to_use)
            
            # Construct the prompt for Gemini with enhanced strategic thinking
            prompt = f"""
                You are Gemini, an AI playing Pokémon FireRed. Look at the screenshot and make decisions to progress in the game.
                
                ## Game Context
                - You are playing Pokémon and need to progress through the game
                - You're trying to make good strategic decisions based on what you see
                - Think carefully about what you see on screen and what action makes the most sense
                
                ## Your notepad (your memory):
                {notepad_content}
                
                ## Controls Available:
                - A: Confirm/Select/Interact
                - B: Cancel/Back
                - START: Open menu
                - SELECT: Cycle options
                - UP, DOWN, LEFT, RIGHT: Move/Navigate
                
                ## Your task:
                1. Look carefully at the screenshot
                2. Think about what's happening and what you should do
                3. Choose ONE button to press
                4. Update your notepad with important information
                
                First think step by step about what you see and what you should do. Consider ALL buttons, not just A.
                
                Respond in this exact format:
                THINK: [Your detailed analysis of the current situation and reasoning]
                BUTTON: [single button name]
                NOTEPAD: [one of: "no change" OR specific information to add]
                
                Buttons must be EXACTLY one of: A, B, START, SELECT, UP, DOWN, LEFT, RIGHT
                """
            
            print("Sending screenshot to Gemini...")
            
            # Generate response from Gemini
            response = self.model.generate_content([prompt, image])
            
            if response:
                print(f"Received response from Gemini: {response.text[:100]}...")
                
                # Parse response for button press and notepad update
                button_press, notepad_update, thinking = self.parse_llm_response(response.text)
                self.last_decision_time = current_time
                
                # Log the AI's thinking for debugging
                if thinking:
                    print(f"AI's thinking: {thinking[:150]}...")
                
                return {
                    'button': button_press,
                    'notepad_update': notepad_update
                }
            
        except Exception as e:
            print(f"Error processing screenshot: {e}")
            import traceback
            traceback.print_exc()
        
        return None

    def parse_llm_response(self, response_text):
        """Parse the LLM response to extract button press, notepad update and thinking"""
        button_press = None
        notepad_update = None
        thinking = None
        
        # Button mapping
        button_map = {
            "A": 0, "B": 1, "SELECT": 2, "START": 3,
            "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7,
            "R": 8, "L": 9
        }
        
        # Find each section
        think_match = re.search(r"THINK:\s*(.*?)(?=BUTTON:|$)", response_text, re.DOTALL)
        button_match = re.search(r"BUTTON:\s*(.*?)(?=NOTEPAD:|$)", response_text, re.DOTALL)
        notepad_match = re.search(r"NOTEPAD:\s*(.*?)$", response_text, re.DOTALL)
        
        # Extract thinking
        if think_match:
            thinking = think_match.group(1).strip()
            print(f"Extracted thinking: {thinking[:50]}...")
        
        # Extract button press
        if button_match:
            button_value = button_match.group(1).strip().upper()
            if button_value in button_map:
                button_press = button_map[button_value]
                print(f"Parsed button press: {button_value} -> {button_press}")
            else:
                # Default to A if invalid button
                button_press = 0
                print(f"Invalid button '{button_value}', defaulting to A (0)")
        
        # Extract notepad update
        if notepad_match:
            notepad_content = notepad_match.group(1).strip()
            if notepad_content.lower() != "no change":
                # Add timestamp to notepad entries
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                notepad_entry = f"\n## Update {timestamp}\n{notepad_content}\n"
                
                current_notepad = self.read_notepad()
                notepad_update = current_notepad + notepad_entry
                print(f"Adding to notepad: {notepad_content[:50]}...")
        
        return button_press, notepad_update, thinking

    def handle_client(self, client_socket, client_address):
        """Handle communication with the emulator client"""
        print(f"Connected to emulator at {client_address}")
        self.current_client = client_socket
        
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Parse the message from the emulator
                message = data.decode('utf-8').strip()
                print(f"Received message from emulator: {message[:50]}...")
                
                parts = message.split("||")
                
                if len(parts) >= 2:
                    message_type = parts[0]
                    content = parts[1]
                    
                    # Handle different message types
                    if message_type == "screenshot":
                        # Process the screenshot and get decision
                        print(f"Processing screenshot from: {content}")
                        
                        # Verify the file exists
                        if os.path.exists(content):
                            file_size = os.path.getsize(content)
                            print(f"Found screenshot at {content} (size: {file_size} bytes)")
                            
                            decision = self.process_screenshot(content)
                            
                            if decision:
                                # Send button press to emulator
                                if decision['button'] is not None and self.running:
                                    print(f"Sending button press: {decision['button']}")
                                    try:
                                        client_socket.send(str(decision['button']).encode('utf-8') + b'\n')
                                    except:
                                        print("Error sending button press")
                                        break
                                
                                # Update notepad if needed
                                if decision['notepad_update']:
                                    self.update_notepad(decision['notepad_update'])
                                    self.summarize_notepad_if_needed()
                        else:
                            print(f"WARNING: Screenshot file not found at {content}")
                    
                    # Handle other message types as needed
                    # (map data, party info, etc.)
                
            except socket.error as e:
                if e.args[0] != socket.EWOULDBLOCK and str(e) != 'Resource temporarily unavailable':
                    print(f"Socket error: {e}")
                    break
            except Exception as e:
                print(f"Error handling client: {e}")
                import traceback
                traceback.print_exc()
                if not self.running:
                    break
                continue
        
        print(f"Disconnected from {client_address}")
        self.current_client = None
        try:
            client_socket.close()
        except:
            pass

    def log_debug(self, message):
        """Log debug messages if debug mode is enabled"""
        if self.debug_mode:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[DEBUG {timestamp}] {message}")
    
    def extract_game_info(self, screenshot_path):
        """
        Extract useful game information from screenshots
        This could be expanded with OCR or more advanced CV techniques
        """
        try:
            # This is a placeholder for future OCR/CV improvements
            # We could use OCR to extract text from the game screen
            # For now, we'll just return the basic file info
            if os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                return {
                    "timestamp": timestamp,
                    "file_size": file_size,
                    "path": screenshot_path
                }
            return None
        except Exception as e:
            print(f"Error extracting game info: {e}")
            return None

    def start(self):
        """Start the controller server"""
        print(f"Starting Pokémon Game Controller on {self.config['host']}:{self.config['port']}")
        
        try:
            while self.running:
                try:
                    print("Waiting for emulator connection...")
                    client_socket, client_address = self.server_socket.accept()
                    client_socket.setblocking(0)
                    # Start client handler in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    self.client_threads.append(client_thread)
                
                except socket.timeout:
                    # Just a timeout, continue the loop
                    continue
                except KeyboardInterrupt:
                    print("\nKeyboard interrupt detected. Shutting down...")
                    break
                except Exception as e:
                    if self.running:  # Only log if we're still supposed to be running
                        print(f"Error in main loop: {e}")
                    break
        finally:
            # Ensure we clean up properly
            self.running = False
            print("Closing all client connections...")
            for t in self.client_threads:
                try:
                    t.join(timeout=1)
                except:
                    pass
            
            self.cleanup()
            print("Server shut down cleanly.")

if __name__ == "__main__":
    controller = PokemonGameController()
    try:
        controller.start()
    except KeyboardInterrupt:
        pass  # Already handled in signal_handler
    finally:
        controller.cleanup()