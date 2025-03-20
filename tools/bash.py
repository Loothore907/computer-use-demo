"""
Bash tool for computer use demo.
"""
import json
import logging
import subprocess
import tempfile
import os
import platform
from typing import Any, Callable, Dict, List, Optional

from .base import Tool

logger = logging.getLogger("tools.bash")

class BashTool(Tool):
    """
    Tool for running shell commands.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize the Bash tool.
        
        Args:
            callback: Optional callback for handling command outputs
        """
        super().__init__(
            name="bash",
            description="Tool for running shell commands",
            callback=callback
        )
        self.shell = "bash" if platform.system() != "Windows" else "cmd.exe"
        self.shell_args = ["-c"] if platform.system() != "Windows" else ["/c"]
        logger.debug(f"BashTool initialized with shell: {self.shell}")
    
    def _run(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run a shell command.
        
        Args:
            command: The shell command to run
            
        Returns:
            Dictionary with the command output
        """
        logger.info(f"Running shell command: {command}")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            
            # Run the command
            process = subprocess.Popen(
                [self.shell, *self.shell_args, command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            result = {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code
            }
            
            if exit_code == 0:
                logger.info(f"Command succeeded with exit code {exit_code}")
            else:
                logger.warning(f"Command failed with exit code {exit_code}")
                logger.warning(f"Command stderr: {stderr}")
            
            return result
        except Exception as e:
            logger.error(f"Error running command '{command}': {e}")
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
                        "description": "The shell command to run"
                    }
                },
                "required": ["command"]
            }
        } 