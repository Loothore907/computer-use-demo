"""
Computer tool for computer use demo.
"""
import base64
import json
import logging
import os
import platform
import time
from typing import Any, Callable, Dict, Optional

from .base import Tool

logger = logging.getLogger("tools.computer")

class ComputerTool(Tool):
    """
    Tool for getting information about the computer.
    
    This tool provides:
    - Screenshot of the desktop
    - System information (OS, CPU, memory, etc.)
    - File system information
    - Process information
    """
    
    def __init__(self, screenshot_callback: Optional[Callable] = None):
        """
        Initialize the computer tool.
        
        Args:
            screenshot_callback: Optional callback for handling screenshots
        """
        super().__init__(
            name="computer",
            description="Tool for interacting with the computer",
            callback=screenshot_callback
        )
        self.screenshot_callback = screenshot_callback
        logger.debug("ComputerTool initialized")
    
    def _run(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run a computer command.
        
        Args:
            command: The command to run (screenshot, sysinfo, etc.)
            **kwargs: Additional arguments for the command
        
        Returns:
            Result of the command
        """
        logger.info(f"Running computer command: {command}")
        
        if command == "screenshot":
            return self._take_screenshot(**kwargs)
        elif command == "sysinfo":
            return self._get_system_info(**kwargs)
        elif command == "fsinfo":
            return self._get_filesystem_info(**kwargs)
        elif command == "procinfo":
            return self._get_process_info(**kwargs)
        else:
            error_msg = f"Unknown computer command: {command}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _take_screenshot(self, **kwargs) -> Dict[str, Any]:
        """
        Take a screenshot of the desktop.
        
        Returns:
            Dictionary with screenshot data
        """
        logger.info("Taking screenshot")
        try:
            # This would be implemented with platform-specific code
            # For demo purposes, we'll just create a dummy screenshot
            dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            
            # Record timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # If we have a callback for screenshots, use it
            filepath = ""
            if self.screenshot_callback:
                context = {"timestamp": timestamp, "source": "computer"}
                filepath = self.screenshot_callback(dummy_image, "computer", context)
            
            result = {
                "success": True,
                "image": dummy_image,
                "timestamp": timestamp,
                "filepath": filepath
            }
            logger.info("Screenshot taken successfully")
            return result
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            raise
    
    def _get_system_info(self, **kwargs) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dictionary with system information
        """
        logger.info("Getting system information")
        try:
            sysinfo = {
                "platform": platform.system(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "node": platform.node(),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            logger.info("System information retrieved successfully")
            return {"success": True, "info": sysinfo}
        except Exception as e:
            logger.error(f"Error getting system information: {e}")
            raise
    
    def _get_filesystem_info(self, path: str = None, **kwargs) -> Dict[str, Any]:
        """
        Get filesystem information.
        
        Args:
            path: The path to get information about (default: current directory)
        
        Returns:
            Dictionary with filesystem information
        """
        path = path or os.getcwd()
        logger.info(f"Getting filesystem information for path: {path}")
        
        try:
            # Get directory contents
            entries = []
            for entry in os.scandir(path):
                entry_info = {
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "is_file": entry.is_file(),
                    "size": entry.stat().st_size if entry.is_file() else None,
                    "modified": time.ctime(entry.stat().st_mtime)
                }
                entries.append(entry_info)
            
            fsinfo = {
                "path": path,
                "entries": entries,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            logger.info(f"Filesystem information retrieved successfully for path: {path}")
            return {"success": True, "info": fsinfo}
        except Exception as e:
            logger.error(f"Error getting filesystem information for path {path}: {e}")
            raise
    
    def _get_process_info(self, **kwargs) -> Dict[str, Any]:
        """
        Get process information.
        
        Returns:
            Dictionary with process information
        """
        logger.info("Getting process information")
        
        try:
            # This would be implemented with platform-specific code
            # For demo purposes, we'll just return a dummy process list
            processes = [
                {"pid": 1, "name": "system", "cpu": 0.1, "memory": 1024},
                {"pid": 2, "name": "user_process", "cpu": 5.2, "memory": 4096}
            ]
            
            procinfo = {
                "processes": processes,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            logger.info("Process information retrieved successfully")
            return {"success": True, "info": procinfo}
        except Exception as e:
            logger.error(f"Error getting process information: {e}")
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
                        "enum": ["screenshot", "sysinfo", "fsinfo", "procinfo"],
                        "description": "The computer command to run"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path for the fsinfo command (optional)"
                    }
                },
                "required": ["command"]
            }
        } 