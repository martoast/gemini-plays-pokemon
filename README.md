# Pokémon Red AI Player

An AI system that plays Pokémon Red using Google's Gemini Vision model for decision making.

## How It Works

This project uses a combination of components to allow an AI to play Pokémon Red:

1. **Emulator with Lua Script**: The mGBA emulator runs Pokémon Red and uses a Lua script to:
   - Capture screenshots of the game
   - Send those screenshots to the Python controller
   - Receive button press commands
   - Execute those commands in the game

2. **Python Controller**: The controller acts as a bridge between the emulator and Gemini:
   - Receives screenshots from the emulator
   - Manages the notepad (game memory)
   - Sends the screenshots and notepad to Gemini
   - Gets decisions from Gemini (button presses and notepad updates)
   - Sends commands back to the emulator

3. **Gemini AI**: The "brain" of the system that:
   - Analyzes screenshots to understand the game state
   - Makes decisions about what to do next
   - Keeps track of its progress and goals in the notepad

## Setup Instructions

### Prerequisites

- Python 3.8+ installed
- mGBA emulator installed (or another emulator that supports Lua scripting)
- A Google Gemini API key
- A legal copy of Pokémon Red ROM

### Installation

1. **Clone this repository**:
   ```
   git clone https://github.com/yourusername/pokemon-red-ai-player.git
   cd pokemon-red-ai-player
   ```

2. **Install Python dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Configure the API key**:
   - Open `config.json`
   - Replace `YOUR_GEMINI_API_KEY` with your actual Gemini API key

4. **Create necessary directories**:
   ```
   mkdir -p data/screenshots
   ```

### Running the AI

1. **Start the system using the main script**:
   ```
   python main.py --rom path/to/pokemon_red.gb --emulator mgba
   ```

   This will:
   - Start the Python controller in the background
   - Launch the emulator with the game and Lua script
   - Begin the AI gameplay session

2. **Watch the AI play**:
   - The emulator window will show the game
   - The AI will make decisions every 3 seconds
   - The notepad.txt file will be updated with the AI's observations and plans

## Project Structure

- `controller.py`: The Python controller that communicates with the emulator and Gemini
- `config.json`: Configuration file for API keys and other settings
- `emulator/`: Directory containing Lua scripts for the emulator
  - `script.lua`: Main Lua script that runs in the emulator
  - `luafinding.lua`: Pathfinding implementation for navigation
  - `vector.lua`: Vector utilities for the pathfinding system
- `data/screenshots/`: Directory where game screenshots are saved
- `notepad.txt`: The AI's memory file where it records observations and plans

## Customization

- **Decision Frequency**: Change the `decision_cooldown` in `config.json` to adjust how often the AI makes decisions
- **Screenshot Interval**: Modify the `screenshotInterval` variable in `script.lua` to change how often screenshots are taken
- **AI Prompting**: Edit the prompt in `controller.py` to change how the AI interprets the game and makes decisions

## Troubleshooting

- **Emulator Connection Issues**: Make sure the emulator is able to connect to the Python controller on the correct port (default: 8888)
- **API Key Errors**: Verify your Gemini API key is correct and has access to the vision capabilities
- **Missing Screenshots**: Check that the `data/screenshots` directory exists and is writable