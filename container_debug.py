
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
