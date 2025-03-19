"""
Tool for executing bash/shell commands.
"""
import os
import platform
import subprocess
from typing import Any, Dict, Optional

from tools.base import Tool


class BashTool(Tool):
    """
    Tool for executing shell commands on the system.
    """
    
    def __init__(self):
        """
        Initialize the bash tool.
        """
        super().__init__(
            name="bash",
            description="Execute a shell command on the system",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Working directory to execute the command in (defaults to current directory)",
                    },
                },
                "required": ["command"],
            },
        )
    
    def _execute_command(self, command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a shell command.
        
        Args:
            command: Command to execute
            working_directory: Working directory to execute the command in
            
        Returns:
            Dictionary with the command output
        """
        try:
            # Create shell command
            is_windows = platform.system() == "Windows"
            shell = is_windows
            
            # Run the command
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_directory
            )
            
            # Get output
            stdout, stderr = process.communicate()
            return_code = process.returncode
            
            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            
            return {
                "success": return_code == 0,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": return_code,
                "message": "Command executed successfully" if return_code == 0 else f"Command failed with return code {return_code}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to execute command: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
            }
    
    def execute(self, command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the bash tool with the given parameters.
        
        Args:
            command: Command to execute
            working_directory: Working directory to execute the command in
            
        Returns:
            Result of the tool execution
        """
        return self._execute_command(command, working_directory)