"""
Docker tool implementation for managing Docker containers.
"""
import json
import logging
import os
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional, Union

from tools.base import Tool

logger = logging.getLogger("tools.dockertool")

class DockerTool(Tool):
    """
    Tool for interacting with Docker containers, images, and volumes.
    Provides a safer interface to Docker operations with validation.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize the Docker tool.
        
        Args:
            docker_path: Path to the Docker executable (default: "docker")
        """
        super().__init__(
            name="docker",
            description="Tool for docker operations",
            callback=callback
        )
        self.docker_path = "docker"  # Set default docker path
        
        # Define the input schema
        self.input_schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Docker action to perform (list, run, stop, remove, build, pull, etc.)",
                },
                "container_id": {
                    "type": "string",
                    "description": "Container ID or name (for container operations)",
                },
                "image": {
                    "type": "string",
                    "description": "Image name (for image operations)",
                },
                "command": {
                    "type": "string",
                    "description": "Command to run in the container (for run or exec)",
                },
                "volume_name": {
                    "type": "string",
                    "description": "Volume name (for volume operations)",
                },
                "volumes": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of volume mappings (e.g., ['host_path:container_path'])",
                },
                "ports": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of port mappings (e.g., ['8080:80'])",
                },
                "environment": {
                    "type": "object",
                    "description": "Environment variables to set in the container",
                },
                "detach": {
                    "type": "boolean",
                    "description": "Run container in background",
                },
                "dockerfile_path": {
                    "type": "string",
                    "description": "Path to Dockerfile (for build operations)",
                },
                "tag": {
                    "type": "string",
                    "description": "Tag for the image (for build operations)",
                },
                "build_context": {
                    "type": "string",
                    "description": "Build context directory (for build operations)",
                },
                "network": {
                    "type": "string",
                    "description": "Network to connect the container to",
                }
            },
            "required": ["action"],
        }
    
    def _run_docker_command(self, args: List[str]) -> Dict[str, Any]:
        """
        Run a Docker command with the given arguments.
        
        Args:
            args: List of Docker command arguments
            
        Returns:
            Dictionary with the command output
        """
        try:
            # Prepend docker to the command
            cmd = [self.docker_path] + args
            
            # Run the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Get output
            stdout, stderr = process.communicate(timeout=60)
            return_code = process.returncode
            
            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            
            # Try to parse JSON output if applicable
            if stdout_str and (stdout_str.strip().startswith("{") or stdout_str.strip().startswith("[")):
                try:
                    json_output = json.loads(stdout_str)
                    return {
                        "success": return_code == 0,
                        "output": json_output,
                        "stderr": stderr_str if stderr_str else None,
                        "return_code": return_code,
                        "message": "Command executed successfully" if return_code == 0 else f"Command failed with return code {return_code}",
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "success": return_code == 0,
                "output": stdout_str,
                "stderr": stderr_str if stderr_str else None,
                "return_code": return_code,
                "message": "Command executed successfully" if return_code == 0 else f"Command failed with return code {return_code}",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Command timed out after 60 seconds",
                "output": "",
                "stderr": "Timeout exceeded",
                "return_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to execute command: {str(e)}",
                "output": "",
                "stderr": str(e),
                "return_code": -1,
            }
    
    def _validate_container_id(self, container_id: str) -> bool:
        """
        Validate a container ID or name.
        
        Args:
            container_id: Container ID or name to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check if it's a valid container ID or name
        if not container_id:
            return False
        
        # Container IDs are alphanumeric
        if re.match(r'^[a-zA-Z0-9_.-]+$', container_id):
            return True
        
        return False
    
    def _validate_image_name(self, image: str) -> bool:
        """
        Validate an image name.
        
        Args:
            image: Image name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not image:
            return False
        
        # Image names follow a specific format
        if re.match(r'^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*:[a-zA-Z0-9_.-]+$', image) or \
           re.match(r'^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$', image):
            return True
        
        return False
    
    def _list_containers(self, all: bool = False) -> Dict[str, Any]:
        """
        List Docker containers.
        
        Args:
            all: Whether to list all containers (including stopped ones)
            
        Returns:
            Dictionary with the list of containers
        """
        args = ["container", "ls", "--format", "json"]
        if all:
            args.append("--all")
        
        return self._run_docker_command(args)
    
    def _list_images(self) -> Dict[str, Any]:
        """
        List Docker images.
        
        Returns:
            Dictionary with the list of images
        """
        return self._run_docker_command(["image", "ls", "--format", "json"])
    
    def _list_volumes(self) -> Dict[str, Any]:
        """
        List Docker volumes.
        
        Returns:
            Dictionary with the list of volumes
        """
        return self._run_docker_command(["volume", "ls", "--format", "json"])
    
    def _run_container(
        self,
        image: str,
        command: Optional[str] = None,
        volumes: Optional[List[str]] = None,
        ports: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
        network: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run a Docker container.
        
        Args:
            image: Image to run
            command: Command to run in the container
            volumes: Volume mappings
            ports: Port mappings
            environment: Environment variables
            detach: Whether to run in detached mode
            network: Network to connect to
            
        Returns:
            Dictionary with the container information
        """
        # Validate image name
        if not self._validate_image_name(image):
            return {
                "success": False,
                "message": f"Invalid image name: {image}",
            }
        
        # Build the command
        args = ["run"]
        
        # Container configuration
        if detach:
            args.append("--detach")
        
        # Network
        if network:
            args.extend(["--network", network])
        
        # Volumes
        if volumes:
            for volume in volumes:
                args.extend(["-v", volume])
        
        # Ports
        if ports:
            for port in ports:
                args.extend(["-p", port])
        
        # Environment variables
        if environment:
            for key, value in environment.items():
                args.extend(["-e", f"{key}={value}"])
        
        # Image and command
        args.append(image)
        
        if command:
            args.extend(command.split())
        
        return self._run_docker_command(args)
    
    def _stop_container(self, container_id: str) -> Dict[str, Any]:
        """
        Stop a Docker container.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Dictionary with the result
        """
        # Validate container ID
        if not self._validate_container_id(container_id):
            return {
                "success": False,
                "message": f"Invalid container ID: {container_id}",
            }
        
        return self._run_docker_command(["stop", container_id])
    
    def _remove_container(self, container_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a Docker container.
        
        Args:
            container_id: Container ID or name
            force: Whether to force removal
            
        Returns:
            Dictionary with the result
        """
        # Validate container ID
        if not self._validate_container_id(container_id):
            return {
                "success": False,
                "message": f"Invalid container ID: {container_id}",
            }
        
        args = ["rm"]
        if force:
            args.append("--force")
        args.append(container_id)
        
        return self._run_docker_command(args)
    
    def _build_image(
        self,
        tag: str,
        dockerfile_path: str = "Dockerfile",
        build_context: str = "."
    ) -> Dict[str, Any]:
        """
        Build a Docker image.
        
        Args:
            tag: Tag for the image
            dockerfile_path: Path to Dockerfile
            build_context: Build context directory
            
        Returns:
            Dictionary with the result
        """
        # Build the command
        args = ["build", "-f", dockerfile_path, "-t", tag, build_context]
        
        return self._run_docker_command(args)
    
    def _pull_image(self, image: str) -> Dict[str, Any]:
        """
        Pull a Docker image.
        
        Args:
            image: Image to pull
            
        Returns:
            Dictionary with the result
        """
        # Validate image name
        if not self._validate_image_name(image):
            return {
                "success": False,
                "message": f"Invalid image name: {image}",
            }
        
        return self._run_docker_command(["pull", image])
    
    def _remove_image(self, image: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a Docker image.
        
        Args:
            image: Image to remove
            force: Whether to force removal
            
        Returns:
            Dictionary with the result
        """
        # Validate image name
        if not self._validate_image_name(image):
            return {
                "success": False,
                "message": f"Invalid image name: {image}",
            }
        
        args = ["rmi"]
        if force:
            args.append("--force")
        args.append(image)
        
        return self._run_docker_command(args)
    
    def _inspect(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """
        Inspect a Docker resource.
        
        Args:
            resource_type: Type of resource (container, image, network, volume)
            resource_id: Resource ID or name
            
        Returns:
            Dictionary with the resource information
        """
        return self._run_docker_command(["inspect", resource_id])
    
    def _logs(self, container_id: str, tail: Optional[int] = None) -> Dict[str, Any]:
        """
        Get logs from a Docker container.
        
        Args:
            container_id: Container ID or name
            tail: Number of lines to show from the end
            
        Returns:
            Dictionary with the logs
        """
        # Validate container ID
        if not self._validate_container_id(container_id):
            return {
                "success": False,
                "message": f"Invalid container ID: {container_id}",
            }
        
        args = ["logs"]
        if tail is not None:
            args.extend(["--tail", str(tail)])
        args.append(container_id)
        
        return self._run_docker_command(args)
    
    def _exec(self, container_id: str, command: str) -> Dict[str, Any]:
        """
        Execute a command in a Docker container.
        
        Args:
            container_id: Container ID or name
            command: Command to execute
            
        Returns:
            Dictionary with the command output
        """
        # Validate container ID
        if not self._validate_container_id(container_id):
            return {
                "success": False,
                "message": f"Invalid container ID: {container_id}",
            }
        
        args = ["exec", container_id]
        args.extend(command.split())
        
        return self._run_docker_command(args)
    
    def _run(
        self,
        action: str,
        container_id: Optional[str] = None,
        image: Optional[str] = None,
        command: Optional[str] = None,
        volume_name: Optional[str] = None,
        volumes: Optional[List[str]] = None,
        ports: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
        dockerfile_path: Optional[str] = None,
        tag: Optional[str] = None,
        build_context: Optional[str] = None,
        network: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the Docker tool with the given parameters.
        
        Args:
            action: Docker action to perform
            container_id: Container ID or name
            image: Image name
            command: Command to run
            volume_name: Volume name
            volumes: Volume mappings
            ports: Port mappings
            environment: Environment variables
            detach: Whether to run in detached mode
            dockerfile_path: Path to Dockerfile
            tag: Tag for the image
            build_context: Build context directory
            network: Network to connect to
            
        Returns:
            Result of the tool execution
        """
        if action == "list_containers":
            return self._list_containers(all=True)
        elif action == "list_images":
            return self._list_images()
        elif action == "list_volumes":
            return self._list_volumes()
        elif action == "run_container":
            if not image:
                return {
                    "success": False,
                    "message": "Image is required for run_container action",
                }
            return self._run_container(
                image,
                command,
                volumes,
                ports,
                environment,
                detach,
                network
            )
        elif action == "stop_container":
            if not container_id:
                return {
                    "success": False,
                    "message": "Container ID is required for stop_container action",
                }
            return self._stop_container(container_id)
        elif action == "remove_container":
            if not container_id:
                return {
                    "success": False,
                    "message": "Container ID is required for remove_container action",
                }
            return self._remove_container(container_id)
        elif action == "build_image":
            if not tag:
                return {
                    "success": False,
                    "message": "Tag is required for build_image action",
                }
            return self._build_image(tag, dockerfile_path, build_context)
        elif action == "pull_image":
            if not image:
                return {
                    "success": False,
                    "message": "Image is required for pull_image action",
                }
            return self._pull_image(image)
        elif action == "remove_image":
            if not image:
                return {
                    "success": False,
                    "message": "Image is required for remove_image action",
                }
            return self._remove_image(image)
        elif action == "inspect":
            if container_id:
                return self._inspect("container", container_id)
            elif image:
                return self._inspect("image", image)
            elif volume_name:
                return self._inspect("volume", volume_name)
            elif network:
                return self._inspect("network", network)
            else:
                return {
                    "success": False,
                    "message": "Resource ID is required for inspect action",
                }
        elif action == "logs":
            if not container_id:
                return {
                    "success": False,
                    "message": "Container ID is required for logs action",
                }
            return self._logs(container_id)
        elif action == "exec":
            if not container_id:
                return {
                    "success": False,
                    "message": "Container ID is required for exec action",
                }
            if not command:
                return {
                    "success": False,
                    "message": "Command is required for exec action",
                }
            return self._exec(container_id, command)
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}",
            } 
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary for the Anthropic API.
        
        Returns:
            Dictionary representation of the tool
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["command1", "command2"],
                        "description": "The command to run"
                    },
                    "param1": {
                        "type": "string",
                        "description": "Parameter 1 description"
                    },
                    "param2": {
                        "type": "string",
                        "description": "Parameter 2 description"
                    }
                },
                "required": ["command"]
            }
        }