"""
Tool for editing files on the system.
"""
import os
from typing import Any, Dict, Optional

from tools.base import Tool


class EditTool(Tool):
    """
    Tool for creating, editing, and reading files on the system.
    """
    
    def __init__(self):
        """
        Initialize the edit tool.
        """
        super().__init__(
            name="edit",
            description="Create, read, or edit a file on the system",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "append"],
                        "description": "Action to perform on the file (read, write, append)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file (for write and append actions)",
                    },
                },
                "required": ["action", "path"],
            },
        )
    
    def _read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a file from the system.
        
        Args:
            path: Path to the file
            
        Returns:
            Dictionary with the file content
        """
        try:
            # Validate path
            if not os.path.exists(path):
                return {
                    "success": False,
                    "message": f"File not found: {path}",
                }
                
            # Read the file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            return {
                "success": True,
                "content": content,
                "message": f"File read successfully: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to read file: {str(e)}",
            }
    
    def _write_file(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Write or append to a file on the system.
        
        Args:
            path: Path to the file
            content: Content to write
            append: Whether to append to the file instead of overwriting
            
        Returns:
            Dictionary with the result
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                
            # Write or append to the file
            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
                
            return {
                "success": True,
                "message": f"{'Appended to' if append else 'Wrote to'} file successfully: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to {'append to' if append else 'write to'} file: {str(e)}",
            }
    
    def execute(self, action: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the edit tool with the given parameters.
        
        Args:
            action: Action to perform (read, write, append)
            path: Path to the file
            content: Content to write (for write and append actions)
            
        Returns:
            Result of the tool execution
        """
        if action == "read":
            return self._read_file(path)
        elif action == "write":
            if content is None:
                return {
                    "success": False,
                    "message": "Content is required for write action",
                }
            return self._write_file(path, content, append=False)
        elif action == "append":
            if content is None:
                return {
                    "success": False,
                    "message": "Content is required for append action",
                }
            return self._write_file(path, content, append=True)
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}",
            }