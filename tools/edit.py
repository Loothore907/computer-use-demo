"""
Edit tool for computer use demo.
"""
import json
import logging
import os
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional

from .base import Tool

logger = logging.getLogger("tools.edit")

class EditTool(Tool):
    """
    Tool for editing files on the system.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize the edit tool.
        
        Args:
            callback: Optional callback for handling edit results
        """
        super().__init__(
            name="edit",
            description="Tool for editing files on the system",
            callback=callback
        )
        logger.debug("EditTool initialized")
    
    def _run(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run an edit command.
        
        Args:
            command: The command to run (read, write, append, delete)
            **kwargs: Additional arguments for the command
        
        Returns:
            Result of the command
        """
        logger.info(f"Running edit command: {command}")
        
        if command == "read":
            return self._read_file(kwargs.get("path", ""))
        elif command == "write":
            return self._write_file(kwargs.get("path", ""), kwargs.get("content", ""))
        elif command == "append":
            return self._append_file(kwargs.get("path", ""), kwargs.get("content", ""))
        elif command == "delete":
            return self._delete_file(kwargs.get("path", ""))
        else:
            error_msg = f"Unknown edit command: {command}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a file.
        
        Args:
            path: Path to the file
        
        Returns:
            Dictionary with the file content
        """
        logger.info(f"Reading file: {path}")
        
        try:
            # Check if the file exists
            if not os.path.exists(path):
                logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"File not found: {path}")
            
            # Read the file
            with open(path, "r") as f:
                content = f.read()
            
            result = {
                "success": True,
                "path": path,
                "content": content,
                "size": len(content)
            }
            
            logger.info(f"Successfully read file: {path} ({len(content)} bytes)")
            return result
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise
    
    def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file, overwriting existing content.
        
        Args:
            path: Path to the file
            content: Content to write
        
        Returns:
            Dictionary with the result
        """
        logger.info(f"Writing to file: {path}")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Write to the file
            with open(path, "w") as f:
                f.write(content)
            
            result = {
                "success": True,
                "path": path,
                "size": len(content)
            }
            
            logger.info(f"Successfully wrote to file: {path} ({len(content)} bytes)")
            return result
        except Exception as e:
            logger.error(f"Error writing to file {path}: {e}")
            raise
    
    def _append_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Append content to a file.
        
        Args:
            path: Path to the file
            content: Content to append
        
        Returns:
            Dictionary with the result
        """
        logger.info(f"Appending to file: {path}")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Append to the file
            with open(path, "a") as f:
                f.write(content)
            
            # Get the total file size
            total_size = os.path.getsize(path)
            
            result = {
                "success": True,
                "path": path,
                "appended": len(content),
                "total_size": total_size
            }
            
            logger.info(f"Successfully appended to file: {path} ({len(content)} bytes)")
            return result
        except Exception as e:
            logger.error(f"Error appending to file {path}: {e}")
            raise
    
    def _delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            path: Path to the file
        
        Returns:
            Dictionary with the result
        """
        logger.info(f"Deleting file: {path}")
        
        try:
            # Check if the file exists
            if not os.path.exists(path):
                logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"File not found: {path}")
            
            # Get the file size before deleting
            size = os.path.getsize(path)
            
            # Delete the file
            os.remove(path)
            
            result = {
                "success": True,
                "path": path,
                "size": size
            }
            
            logger.info(f"Successfully deleted file: {path} ({size} bytes)")
            return result
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            raise
    
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
                        "enum": ["read", "write", "append", "delete"],
                        "description": "The edit command to run"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content for write and append commands"
                    }
                },
                "required": ["command", "path"]
            }
        } 