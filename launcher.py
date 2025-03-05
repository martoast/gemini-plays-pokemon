#!/usr/bin/env python3
"""
All-in-One Launcher for Pokémon Red AI Player
"""

import os
import sys
import time
import subprocess
import json
import argparse

def setup_directories():
    """Set up required directories"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create the screenshots directory
    screenshots_dir = os.path.join(project_root, "data", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Create an empty notepad.txt if it doesn't exist
    notepad_path = os.path.join(project_root, "notepad.txt")
    if not os.path.exists(notepad_path):
        with open(notepad_path, "w") as f:
            f.write("# Pokémon Red Game AI Notepad\n")
            f.write("I am playing Pokémon Red. I need to record important information here.\n\n")
    
    print(f"Created directory: {screenshots_dir}")
    print(f"Screenshot path: {os.path.join(screenshots_dir, 'screenshot.png')}")
    print(f"Notepad path: {notepad_path}")
    print("Directory setup complete!")

def main():
    """Main function to launch all components"""
    parser = argparse.ArgumentParser(description="Launch Pokémon Red AI Player")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--rom", default="pokemon-red.gba", help="Path to Pokémon ROM file")
    parser.add_argument("--emulator", default="/Applications/mGBA.app/Contents/MacOS/mGBA", help="Path to emulator executable")
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Check if config exists and has API key
    if not os.path.exists(args.config):
        print(f"Error: Config file {args.config} not found.")
        print("Please create a config.json file with your Gemini API key.")
        return 1
    
    # Load config to check API key
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    if config['api_key'] == "YOUR_GEMINI_API_KEY":
        print("Error: You need to set your Gemini API key in config.json")
        return 1
    
    # Check if ROM file exists
    if not os.path.exists(args.rom):
        print(f"Error: ROM file {args.rom} not found.")
        print("Please provide a valid path to the Pokémon Red ROM file.")
        return 1
    
    # Start the controller in background
    print("Starting Python controller...")
    controller_process = subprocess.Popen(
        [sys.executable, "controller.py"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Give the controller a moment to start
    time.sleep(2)
    
    # Start the emulator with the ROM
    print("Starting emulator...")
    print("IMPORTANT: Once mGBA opens, go to Tools > Scripting... and load the script from 'emulator/script.lua'")
    emulator_command = [
        args.emulator,
        args.rom
    ]
    
    try:
        emulator_process = subprocess.Popen(emulator_command)
        
        # Print controller output in real-time
        def print_output(stream, prefix):
            for line in iter(stream.readline, b''):
                print(f"{prefix}: {line.decode().strip()}")
                
        from threading import Thread
        Thread(target=print_output, args=(controller_process.stdout, "Controller")).daemon = True
        Thread(target=print_output, args=(controller_process.stderr, "Controller Error")).daemon = True
        
        # Wait for the emulator to finish
        emulator_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up processes
        print("Terminating controller...")
        controller_process.terminate()
        
        try:
            controller_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            controller_process.kill()
        
        print("All processes terminated.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())