#!/usr/bin/env python3
"""
Simple Docker tool demo script.
"""
import json
import os
import sys
import subprocess
from pathlib import Path

sys.path.append('.')  # Add current directory to path

from tools.docker import DockerTool


def find_docker_path():
    """
    Try to find the Docker executable on Windows.
    
    Returns:
        Path to the Docker executable or None if not found
    """
    # Common Docker installation paths on Windows
    paths_to_check = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        r"C:\Program Files\Docker Desktop\Docker\resources\bin\docker.exe",
        r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
        # Add additional common paths as needed
    ]
    
    # Check if docker.exe exists in any of these paths
    for path in paths_to_check:
        if os.path.exists(path):
            return path
    
    # Check if docker is in PATH
    try:
        result = subprocess.run(["where", "docker"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    
    # If using WSL, try the WSL docker path
    try:
        result = subprocess.run(["wsl", "which", "docker"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return f"wsl docker"  # Use docker through WSL
    except Exception:
        pass
    
    return None


def main():
    """
    Run a simple demo of the Docker tool.
    """
    # Try to find Docker path
    docker_path = find_docker_path()
    if docker_path:
        print(f"Found Docker at: {docker_path}")
    else:
        print("Docker not found. Make sure Docker Desktop is running and docker.exe is in your PATH.")
        print("Proceeding with default 'docker' command, but it may fail.")
        docker_path = "docker"
    
    # Initialize the Docker tool with the found path
    docker_tool = DockerTool(docker_path=docker_path)
    
    # List Docker images
    print("Listing Docker images...")
    result = docker_tool.execute(action="list_images")
    print(json.dumps(result, indent=2))
    
    # List Docker containers
    print("\nListing Docker containers...")
    result = docker_tool.execute(action="list_containers")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main() 