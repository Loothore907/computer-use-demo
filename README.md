# Computer Use Demo

A demo application that allows Claude to take screenshots of your computer.

## Overview

This application provides a simple chat interface for interacting with Claude with the ability to take screenshots of your screen. It demonstrates how Claude can use tools to interact with your computer in a safe and controlled way.

## Features

- Chat interface for interacting with Claude
- Screenshot capability (Claude can take screenshots of your screen)
- API key management through the UI

## Setup

1. Clone this repository
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

1. Enter your Anthropic API key in the sidebar
2. Click "Apply API Key" to set it
3. Start chatting with Claude
4. Ask Claude to take a screenshot (e.g., "Please take a screenshot of my screen")
5. Claude will capture a screenshot and display it in the chat

## Safety

This demo has been restricted to only allow screenshots. It does not include capabilities for:
- Controlling your mouse or keyboard
- Executing commands on your system
- Editing files on your system

## License

MIT