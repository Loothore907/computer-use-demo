#!/usr/bin/env python3
"""
Unified entry point for the Claude Computer Use Demo.
Handles Docker container startup and configuration.
"""
import os
import sys
import argparse
import subprocess
import logging
import dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("claude_demo.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("claude-demo")

def load_api_key():
    """
    Load API key from .env file or command line.
    Returns the API key or None if not found.
    """
    # Try to load from .env file
    if os.path.exists(".env"):
        logger.info("Loading environment variables from .env file...")
        dotenv.load_dotenv()
    
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Validate API key format
    if api_key and not api_key.startswith("sk-ant-"):
        logger.warning("API key doesn't follow the expected format (should start with 'sk-ant-')")
    
    return api_key

def ensure_directories():
    """
    Ensure required directories exist.
    """
    dirs = ["workspace", "data"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_name}")
    
    return {name: os.path.abspath(name) for name in dirs}

def check_docker():
    """
    Check if Docker is running and the image exists.
    Returns True if everything is ready, False otherwise.
    """
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("Docker is running properly")
        
        # Check if the image exists
        result = subprocess.run(
            ["docker", "image", "inspect", "claude-computer-use"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            logger.info("Docker image 'claude-computer-use' is available")
            return True
        else:
            logger.error("Docker image 'claude-computer-use' not found. Please build it first:")
            logger.error("docker build -t claude-computer-use .")
            return False
    except subprocess.CalledProcessError:
        logger.error("Docker doesn't seem to be running. Please start Docker and try again.")
        return False
    except FileNotFoundError:
        logger.error("Docker command not found. Please install Docker.")
        return False

def run_container(api_key, model="claude-3-5-sonnet-20241022", beta_flag="computer-use-2024-10-22", port=8501):
    """
    Run the Docker container with the given configuration.
    """
    if not api_key:
        logger.error("No API key provided. Please set ANTHROPIC_API_KEY in .env file or pass with --api-key.")
        return False
    
    dirs = ensure_directories()
    
    # Build the Docker command
    docker_cmd = [
        "docker", "run", "-it", "--rm",
        "-p", f"{port}:8501",
        "-v", f"{dirs['workspace'].replace('\\', '/')}:/app/workspace",
        "-v", f"{dirs['data'].replace('\\', '/')}:/app/data",
        "-e", f"ANTHROPIC_API_KEY={api_key}",
        "-e", f"MODEL={model}",
        "-e", f"BETA_FLAG={beta_flag}",
        "-e", "PYTHONUNBUFFERED=1",
        "claude-computer-use",
        "python", "/app/container_entry.py"
    ]
    
    # Add Docker socket for Docker-in-Docker functionality
    if sys.platform == "win32":
        docker_cmd.extend(["-v", "//./pipe/docker_engine://./pipe/docker_engine"])
    else:
        docker_cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock"])
    
    logger.info("Starting Claude Computer Use Demo container...")
    logger.info(f"Using model: {model}")
    logger.info(f"UI will be available at: http://localhost:{port}")
    
    try:
        # On Windows, use os.system for better interactive terminal support
        if sys.platform == "win32":
            command_str = " ".join(docker_cmd)
            os.system(command_str)
        else:
            # On Linux/Mac, use subprocess.run
            subprocess.run(docker_cmd)
        
        logger.info("Container exited successfully")
        return True
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        return True
    except Exception as e:
        logger.error(f"Error running Docker container: {e}")
        return False

def main():
    """
    Main entry point for the Claude Computer Use Demo.
    """
    parser = argparse.ArgumentParser(description="Claude Computer Use Demo")
    parser.add_argument("--api-key", help="Anthropic API key (if not set in .env file)")
    parser.add_argument("--model", default="claude-3-5-sonnet-20241022", 
                        help="Claude model to use (default: claude-3-5-sonnet-20241022)")
    parser.add_argument("--beta-flag", default="computer-use-2024-10-22",
                        help="Beta flag for computer use capabilities (default: computer-use-2024-10-22)")
    parser.add_argument("--port", type=int, default=8501,
                        help="Port to run Streamlit on (default: 8501)")
    parser.add_argument("--build", action="store_true",
                        help="Build the Docker image before running")
    parser.add_argument("--clean", action="store_true",
                        help="Clean Docker cache when building")
    
    args = parser.parse_args()
    
    # Load API key from .env or command line
    api_key = args.api_key or load_api_key()
    
    # Print API key information (first/last few chars only)
    if api_key:
        logger.info(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Build the image if requested
    if args.build:
        logger.info("Building Docker image...")
        build_cmd = ["docker", "build"]
        
        # Add no-cache flag if clean build requested
        if args.clean:
            logger.info("Building with clean cache...")
            build_cmd.append("--no-cache")
            
        build_cmd.extend(["-t", "claude-computer-use", "."])
        
        build_result = subprocess.run(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if build_result.returncode != 0:
            logger.error("Failed to build Docker image:")
            logger.error(build_result.stderr.decode("utf-8"))
            return 1
        
        logger.info("Docker image built successfully")
    
    # Check Docker is ready
    if not check_docker():
        return 1
    
    # Run the container
    success = run_container(
        api_key=api_key,
        model=args.model,
        beta_flag=args.beta_flag,
        port=args.port
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Operation canceled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)