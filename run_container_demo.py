#!/usr/bin/env python3
"""
Demo for running a Docker container with our tool.
"""
import json
import sys
import time
from simple_docker_demo import find_docker_path

sys.path.append('.')  # Add current directory to path
from tools.docker import DockerTool


def main():
    """
    Run a simple container demo.
    """
    # Try to find Docker path
    docker_path = find_docker_path()
    if not docker_path:
        print("Docker not found. Make sure Docker Desktop is running.")
        return
    
    print(f"Using Docker at: {docker_path}")
    docker_tool = DockerTool(docker_path=docker_path)
    
    # Pull the hello-world image
    print("\nPulling hello-world image...")
    result = docker_tool.execute(action="pull_image", image="hello-world")
    print(json.dumps(result, indent=2))
    
    if not result["success"]:
        print("Failed to pull hello-world image. Exiting.")
        return
    
    # Run the hello-world container
    print("\nRunning hello-world container...")
    result = docker_tool.execute(
        action="run_container",
        image="hello-world",
        detach=False
    )
    print(json.dumps(result, indent=2))
    
    # List containers (including stopped ones)
    print("\nListing all containers (including stopped ones)...")
    result = docker_tool.execute(action="list_containers")
    print(json.dumps(result, indent=2))
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    main() 