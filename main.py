#!/usr/bin/env python3
"""
Main launcher for Pokémon Red AI Player
This script handles starting up all necessary components
"""

import os
import sys
import time
import subprocess
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Launch Pokémon Red AI Player")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--rom", default="pokemon_red.gb", help="Path to Pokémon ROM file")
    parser.add_argument("--emulator", default="/Applications/mGBA.app/Contents/MacOS/mGBA", help="Path to emulator executable")
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs("data/screenshots", exist_ok=True)
    
    # Check if config exists
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
    
    # Start the emulator without the Lua script (we'll need to load it manually from the UI)
    print("Starting emulator...")
    print("IMPORTANT: Once mGBA opens, go to Tools > Scripting... and load the script from 'emulator/script.lua'")
    emulator_command = [
        args.emulator,
        args.rom
    ]
    
    try:
        emulator_process = subprocess.Popen(emulator_command)
        
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