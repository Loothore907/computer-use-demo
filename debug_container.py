#!/usr/bin/env python3
"""
Debug script to identify issues with the Docker container.
"""
import os
import sys
import subprocess
import logging
import dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug")

def load_env_vars():
    """Load environment variables from .env file."""
    if os.path.exists(".env"):
        logger.info("Loading environment variables from .env file...")
        dotenv.load_dotenv()
        return True
    else:
        logger.error("No .env file found.")
        return False

def main():
    """Main debug function."""
    if not load_env_vars():
        logger.error("Environment variables could not be loaded. Exiting.")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("MODEL", "claude-3-5-sonnet-20241022")
    beta_flag = os.environ.get("BETA_FLAG", "computer-use-2024-10-22")

    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables.")
        sys.exit(1)

    logger.info(f"API Key: {api_key[:10]}...{api_key[-5:]}")
    logger.info(f"Model: {model}")
    logger.info(f"Beta Flag: {beta_flag}")

    workspace_path = os.path.abspath("workspace")
    data_path = os.path.abspath("data")
    os.makedirs(workspace_path, exist_ok=True)
    os.makedirs(data_path, exist_ok=True)

    # Write debug script to a file
    debug_script = '''
import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("debug-container")

try:
    # Print Python version
    logger.info(f"Python version: {sys.version}")
    
    # Print environment variables
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if key == "ANTHROPIC_API_KEY":
            logger.info(f"  {key}: {value[:10]}...{value[-5:]}")
        else:
            logger.info(f"  {key}: {value}")
    
    # Try to import required modules
    logger.info("Importing modules...")
    
    try:
        import anthropic
        logger.info("Successfully imported anthropic")
        logger.info(f"Anthropic version: {anthropic.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import anthropic: {e}")
    
    # Check for tools module
    try:
        sys.path.append("/app")
        from tools import ComputerTool
        logger.info("Successfully imported tools.ComputerTool")
        
        # Try to initialize a tool
        tool = ComputerTool()
        logger.info("Successfully initialized ComputerTool")
        logger.info(f"Tool schema: {tool.to_dict()}")
    except Exception as e:
        logger.error(f"Error with tools module: {e}")
        logger.error(traceback.format_exc())
    
    # Check for loop module
    try:
        from loop import AgentLoop
        logger.info("Successfully imported AgentLoop")
    except Exception as e:
        logger.error(f"Error importing AgentLoop: {e}")
        logger.error(traceback.format_exc())
        
    logger.info("Debug complete")
    
except Exception as e:
    logger.error(f"Unhandled exception: {e}")
    logger.error(traceback.format_exc())
'''

    with open("container_debug.py", "w") as f:
        f.write(debug_script)
    
    logger.info("Created debug script file: container_debug.py")

    # Run with direct command instead of capture_output
    docker_cmd = (
        f'docker run --rm '
        f'-v //./pipe/docker_engine://./pipe/docker_engine '
        f'-v {workspace_path.replace("\\", "/")}:/app/workspace '
        f'-v {data_path.replace("\\", "/")}:/app/data '
        f'-v {os.path.abspath("container_debug.py").replace("\\", "/")}:/app/debug.py '
        f'-e ANTHROPIC_API_KEY={api_key} '
        f'-e MODEL={model} '
        f'-e BETA_FLAG={beta_flag} '
        f'claude-computer-use '
        f'python /app/debug.py'
    )

    logger.info("Running debug container...")
    logger.info(f"Command: {docker_cmd}")
    
    # On Windows, we need to use os.system directly to see output
    os.system(docker_cmd)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc()) 