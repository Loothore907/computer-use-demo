#!/usr/bin/env python3
"""
Script to run the agent loop with environment variables.
"""
import os
import sys
import subprocess
import logging
import traceback
import dotenv
import datetime
from typing import Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("claude-agent")

# Output directories
OUTPUT_ROOT = "output"
CHAT_DIR = os.path.join(OUTPUT_ROOT, "chats")
SCREENSHOT_DIR = os.path.join(OUTPUT_ROOT, "screenshots")
TOOL_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "tool_outputs")
LOG_DIR = os.path.join(OUTPUT_ROOT, "logs")

def setup_output_dirs() -> Dict[str, str]:
    """
    Create output directories for storing chats, screenshots, and tool outputs.
    
    Returns:
        Dict with paths to output directories
    """
    # Create timestamp-based session ID
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{timestamp}"
    
    # Create session directories
    session_dirs = {
        "session_id": session_id,
        "root": OUTPUT_ROOT,
        "chat": os.path.join(CHAT_DIR, session_id),
        "screenshot": os.path.join(SCREENSHOT_DIR, session_id),
        "tool_output": os.path.join(TOOL_OUTPUT_DIR, session_id),
        "log": os.path.join(LOG_DIR, session_id)
    }
    
    # Create directories
    for dir_path in session_dirs.values():
        if isinstance(dir_path, str) and not dir_path.endswith("_id"):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    return session_dirs

def load_env_vars() -> bool:
    """
    Load environment variables from .env file.
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Try to load .env file if it exists
    if os.path.exists(".env"):
        logger.info("Loading environment variables from .env file...")
        dotenv.load_dotenv()
        return True
    else:
        logger.warning("No .env file found. Using existing environment variables.")
        # Check if ANTHROPIC_API_KEY is already set in environment
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.error("ANTHROPIC_API_KEY not found in environment.")
            return False
    return True

def create_startup_script(session_dirs: Dict[str, str]):
    """Create a startup script to run in the container."""
    script = """#!/usr/bin/env python3
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
SESSION_DIRS = {session_dirs}

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
            user_input = input('\\nYou: ')
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
            
            print(f'\\nClaude: {result["assistant_message"]}')
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
    print('\\nAgent terminated.')
except Exception as e:
    logger.error(f"Container initialization error: {e}")
    logger.error(traceback.format_exc())
    print(f"Critical error: {e}")
    sys.exit(1)
""".replace("{session_dirs}", str(session_dirs))
    
    # Write the script to a file
    script_path = os.path.abspath("agent_startup.py")
    with open(script_path, "w") as f:
        f.write(script)
    
    logger.info(f"Created startup script: {script_path}")
    return script_path

def run_agent_container() -> None:
    """
    Run the agent in a Docker container with proper environment variables.
    """
    if not load_env_vars():
        logger.error("\nPlease create a .env file with your API key. See .env.example for reference.")
        logger.error("Or set the ANTHROPIC_API_KEY environment variable manually.")
        sys.exit(1)
    
    # Create output directories
    session_dirs = setup_output_dirs()
    logger.info(f"Created session: {session_dirs['session_id']}")
    
    # Get environment variables (with defaults for optional ones)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("MODEL", "claude-3-5-sonnet-20241022")
    beta_flag = os.environ.get("BETA_FLAG", "computer-use-2024-10-22")
    
    if not api_key or api_key.startswith("sk-ant-api01-..."):
        logger.error("Please set a valid ANTHROPIC_API_KEY in your .env file or environment.")
        sys.exit(1)
    
    # Validate API key format
    if not api_key.startswith("sk-ant-"):
        logger.warning("API key doesn't follow the expected format (should start with 'sk-ant-')")
    
    # Create workspace and data directories if they don't exist
    os.makedirs("workspace", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Get absolute paths
    workspace_path = os.path.abspath("workspace")
    data_path = os.path.abspath("data")
    output_path = os.path.abspath(OUTPUT_ROOT)
    
    # Check if Docker is running
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("Docker is running properly")
    except subprocess.CalledProcessError:
        logger.error("Docker doesn't seem to be running. Please start Docker and try again.")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("Docker command not found. Please make sure Docker is installed.")
        sys.exit(1)
    
    # Check if our image exists
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "claude-computer-use"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            logger.error("Docker image 'claude-computer-use' not found. Please build it first:")
            logger.error("docker build -t claude-computer-use .")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error checking Docker image: {e}")
        sys.exit(1)
    
    # Create startup script 
    startup_script = create_startup_script(session_dirs)
    
    # Construct the Docker command
    docker_cmd = f'docker run -it --rm ' \
                 f'-v //./pipe/docker_engine://./pipe/docker_engine ' \
                 f'-v {workspace_path.replace("\\", "/")}:/app/workspace ' \
                 f'-v {data_path.replace("\\", "/")}:/app/data ' \
                 f'-v {output_path.replace("\\", "/")}:/app/output ' \
                 f'-v {startup_script.replace("\\", "/")}:/app/startup.py ' \
                 f'-e PYTHONUNBUFFERED=1 ' \
                 f'-e ANTHROPIC_API_KEY={api_key} ' \
                 f'-e MODEL={model} ' \
                 f'-e BETA_FLAG={beta_flag} ' \
                 f'-e SESSION_ID={session_dirs["session_id"]} ' \
                 f'claude-computer-use ' \
                 f'python /app/startup.py'
    
    logger.info("\nStarting Claude agent container...")
    logger.info(f"Workspace directory: {workspace_path}")
    logger.info(f"Data directory: {data_path}")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Session ID: {session_dirs['session_id']}")
    logger.info(f"Model: {model}")
    logger.info(f"Beta flag: {beta_flag}")
    logger.info("="*50)
    
    # On Windows, use os.system for better terminal handling
    try:
        os.system(docker_cmd)
        logger.info("Docker container exited")
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
    except Exception as e:
        logger.error(f"Error running Docker container: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        logger.info("Starting Claude agent runner")
        run_agent_container()
    except KeyboardInterrupt:
        logger.info("Operation canceled by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        logger.error(traceback.format_exc()) 