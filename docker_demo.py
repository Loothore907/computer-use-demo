#!/usr/bin/env python3
"""
Docker tool demo script.
"""
import json
import os
import argparse
from tools import DockerTool


def main():
    """
    Run a simple demo of the Docker tool.
    """
    parser = argparse.ArgumentParser(description="Docker tool demo")
    parser.add_argument("--action", type=str, required=True, 
                       choices=["list_containers", "list_images", "list_volumes", 
                               "run_container", "stop_container", "remove_container",
                               "pull_image", "inspect", "logs"],
                       help="Docker action to perform")
    parser.add_argument("--container-id", type=str, help="Container ID (for container operations)")
    parser.add_argument("--image", type=str, help="Image name (for image operations)")
    parser.add_argument("--command", type=str, help="Command to run in the container")
    parser.add_argument("--volume", type=str, action="append", help="Volume mapping (use multiple times for multiple volumes)")
    parser.add_argument("--port", type=str, action="append", help="Port mapping (use multiple times for multiple ports)")
    parser.add_argument("--env", type=str, action="append", help="Environment variable (format: KEY=VALUE)")
    parser.add_argument("--detach", action="store_true", help="Run container in detached mode")
    parser.add_argument("--network", type=str, help="Network to connect the container to")
    
    args = parser.parse_args()
    
    # Initialize the Docker tool
    docker_tool = DockerTool()
    
    # Process environment variables
    environment = {}
    if args.env:
        for env_var in args.env:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                environment[key] = value
    
    # Execute the appropriate action
    if args.action == "list_containers":
        result = docker_tool.execute(action="list_containers")
    elif args.action == "list_images":
        result = docker_tool.execute(action="list_images")
    elif args.action == "list_volumes":
        result = docker_tool.execute(action="list_volumes")
    elif args.action == "run_container":
        if not args.image:
            print("Error: --image is required for run_container action")
            return
        
        result = docker_tool.execute(
            action="run_container",
            image=args.image,
            command=args.command,
            volumes=args.volume,
            ports=args.port,
            environment=environment,
            detach=args.detach,
            network=args.network
        )
    elif args.action == "stop_container":
        if not args.container_id:
            print("Error: --container-id is required for stop_container action")
            return
            
        result = docker_tool.execute(
            action="stop_container",
            container_id=args.container_id
        )
    elif args.action == "remove_container":
        if not args.container_id:
            print("Error: --container-id is required for remove_container action")
            return
            
        result = docker_tool.execute(
            action="remove_container",
            container_id=args.container_id
        )
    elif args.action == "pull_image":
        if not args.image:
            print("Error: --image is required for pull_image action")
            return
            
        result = docker_tool.execute(
            action="pull_image",
            image=args.image
        )
    elif args.action == "inspect":
        if not args.container_id and not args.image:
            print("Error: either --container-id or --image is required for inspect action")
            return
            
        result = docker_tool.execute(
            action="inspect",
            container_id=args.container_id,
            image=args.image
        )
    elif args.action == "logs":
        if not args.container_id:
            print("Error: --container-id is required for logs action")
            return
            
        result = docker_tool.execute(
            action="logs",
            container_id=args.container_id
        )
    
    # Print the result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main() 