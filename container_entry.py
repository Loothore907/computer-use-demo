#!/usr/bin/env python3
"""
Container entry point script that configures and launches the Streamlit app.
"""
import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("container.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("container-entry")

def setup_streamlit_config():
    """
    Set up Streamlit configuration to bypass welcome screen and telemetry.
    """
    # Force disable of Streamlit welcome screen and telemetry
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = "false"
    os.environ['STREAMLIT_SERVER_HEADLESS'] = "true"

    # Create Streamlit config directory
    streamlit_config_path = os.path.expanduser("~/.streamlit")
    os.makedirs(streamlit_config_path, exist_ok=True)
    logger.info(f"Created Streamlit config directory: {streamlit_config_path}")

    # Create credentials.toml - bypasses email prompt
    credentials_file = os.path.join(streamlit_config_path, "credentials.toml")
    with open(credentials_file, "w") as f:
        f.write("""
[general]
email = ""
showWelcomeOnStartup = false
        """)
    logger.info(f"Created Streamlit credentials file: {credentials_file}")

    # Create config.toml - disables telemetry and header
    config_file = os.path.join(streamlit_config_path, "config.toml")
    with open(config_file, "w") as f:
        f.write("""
[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"

[server]
headless = true
runOnSave = false
enableCORS = true
enableXsrfProtection = false
fileWatcherType = "none"
        """)
    logger.info(f"Created Streamlit config file: {config_file}")

    # Create first-run marker to skip welcome
    with open(os.path.join(streamlit_config_path, ".first_run_complete"), "w") as f:
        f.write("1")
    logger.info("Created Streamlit first-run marker")

def verify_environment():
    """
    Verify that required environment variables are set.
    
    Returns:
        bool: True if environment is valid, False otherwise
    """
    required_vars = ["ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Log API key (first/last few chars only)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        logger.info(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Log other configuration
    logger.info(f"Using model: {os.environ.get('MODEL', 'claude-3-5-sonnet-20241022')}")
    logger.info(f"Using beta flag: {os.environ.get('BETA_FLAG', 'computer-use-2024-10-22')}")
    
    return True

def main():
    """
    Main entry point that configures and launches Streamlit.
    """
    logger.info("Starting container entry script")
    
    # Set up Streamlit configuration
    setup_streamlit_config()
    
    # Verify environment
    if not verify_environment():
        logger.error("Environment verification failed. Exiting.")
        sys.exit(1)
    
    logger.info("Environment verification passed")
    
    # Launch Streamlit app
    logger.info("Launching Streamlit app...")
    try:
        subprocess.run(["streamlit", "run", "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlit process failed with return code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error launching Streamlit: {e}")
        sys.exit(1)
    
    logger.info("Streamlit process completed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)