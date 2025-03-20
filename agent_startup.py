#!/usr/bin/env python3
import os
import sys
import logging
import traceback
import json
import time
from pathlib import Path
from loop import AgentLoop

# Configure logging
os.makedirs('/app/output/logs', exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/output/logs/container.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("claude-agent")

# Output directories (mapped from host)
SESSION_DIRS = {'session_id': 'session_20250319_095610', 'root': 'output', 'chat': 'output\\chats\\session_20250319_095610', 'screenshot': 'output\\screenshots\\session_20250319_095610', 'tool_output': 'output\\tool_outputs\\session_20250319_095610', 'log': 'output\\logs\\session_20250319_095610'}

# Ensure output directories exist
for dir_path in SESSION_DIRS.values():
    if isinstance(dir_path, str) and not dir_path.endswith("_id"):
        os.makedirs(dir_path, exist_ok=True)
        logger.debug(f"Verified directory exists: {dir_path}")

try:
    # Get environment variables
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    model = os.environ.get('MODEL')
    beta_flag = os.environ.get('BETA_FLAG')
    
    if not api_key:
        logger.error("API key not found in environment variables")
        sys.exit(1)
    
    # Log startup info
    logger.info("Starting Claude agent")
    logger.info(f"Model: {model}")
    logger.info(f"Beta flag: {beta_flag}")
    logger.info(f"Session ID: {SESSION_DIRS['session_id']}")
    
    # Initialize agent with session dirs
    agent = AgentLoop(
        api_key=api_key, 
        model=model, 
        beta_flag=beta_flag,
        session_dirs=SESSION_DIRS
    )
    logger.info("Agent initialized successfully")
    logger.info("Type 'exit' to quit")
    
    # Create chat history JSON file
    chat_file = os.path.join(SESSION_DIRS['chat'], 'chat_history.json')
    with open(chat_file, 'w') as f:
        json.dump([], f)
    logger.info(f"Created chat history file: {chat_file}")
    
    # Run interaction loop
    while True:
        try:
            user_input = input('\nYou: ')
            if user_input.lower() in ['exit', 'quit']: 
                break
            
            logger.info("Sending request to Claude API...")
            start_time = time.time()
            result = agent.run(user_input)
            elapsed = time.time() - start_time
            logger.info(f"Received response from Claude API in {elapsed:.2f} seconds")
            
            # Save chat history
            with open(chat_file, 'w') as f:
                json.dump(agent.conversation_history, f, indent=2)
            logger.debug("Updated chat history file")
            
            print(f'\nClaude: {result["assistant_message"]}')
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            logger.error(traceback.format_exc())
            print(f'Error: {e}')
    
    # Final save of chat history
    with open(chat_file, 'w') as f:
        json.dump(agent.conversation_history, f, indent=2)
    logger.info("Saved final chat history")
    
    logger.info("Agent terminated")
    print('\nAgent terminated.')
except Exception as e:
    logger.error(f"Container initialization error: {e}")
    logger.error(traceback.format_exc())
    print(f"Critical error: {e}")
    sys.exit(1)
