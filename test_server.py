#!/usr/bin/env python3
"""
Simple test server to verify socket communication with mGBA
"""
import socket
import time
import os

def main():
    # Make sure screenshots directory exists
    os.makedirs("data/screenshots", exist_ok=True)
    
    # Set up server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    host = '127.0.0.1'
    port = 8888
    running = True  # Flag for server loop
    
    try:
        server.bind((host, port))
        server.listen(1)
        print(f"Server listening on {host}:{port}")
        
        print("Waiting for connection from mGBA...")
        client, address = server.accept()
        print(f"Connected to {address}")
        
        # Set non-blocking mode
        client.setblocking(0)
        
        counter = 0
        last_key_time = 0
        key_interval = 5  # seconds between key presses
        
        while running:
            try:
                # Check if there’s incoming data
                data = client.recv(1024)
                if data:
                    message = data.decode('utf-8').strip()
                    print(f"Received: {message}")
                    
                    # Handle screenshot messages
                    if message.startswith("screenshot||"):
                        screenshot_path = message.split("||")[1]
                        if os.path.exists(screenshot_path):
                            print(f"Screenshot exists at {screenshot_path}")
                            file_size = os.path.getsize(screenshot_path)
                            print(f"Screenshot size: {file_size} bytes")
                        else:
                            print(f"Screenshot does not exist at {screenshot_path}")
            except socket.error as e:
                # Handle non-blocking socket error
                if e.args[0] in {10035, 35} or str(e) == 'Resource temporarily unavailable':
                    pass  # Expected for non-blocking sockets
                else:
                    print(f"Socket error: {e}")

            # Send a key press every few seconds
            current_time = time.time()
            if current_time - last_key_time > key_interval:
                key_to_send = counter % 8  # Cycle through directions
                print(f"Sending key press: {key_to_send}")
                client.send(str(key_to_send).encode('utf-8'))
                last_key_time = current_time
                counter += 1

            time.sleep(0.1)  # Prevent CPU hogging
            
    except KeyboardInterrupt:
        print("\nReceived KeyboardInterrupt. Shutting down server...")
        running = False
    except Exception as e:
        print(f"Unexpected Error: {e}")
    finally:
        print("Closing client connection...")
        client.close()
        print("Closing server socket...")
        server.close()
        print("Server shut down successfully.")

if __name__ == "__main__":
    main()
