"""
Computer tool implementation.
"""
import base64
import io
import json
import os
import platform
from typing import Any, Dict, List, Optional, Tuple, Union

import PIL.Image
from PIL import Image, ImageGrab

from tools.base import Tool


class ComputerTool(Tool):
    """
    Tool for taking screenshots of the computer screen.
    """
    
    def __init__(self):
        """
        Initialize the computer tool.
        """
        super().__init__(
            name="computer",
            description="Take a screenshot of the computer screen",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["screenshot"],
                        "description": "Action to perform on the computer",
                    },
                },
                "required": ["action"],
            },
        )
            
    def _take_screenshot(self) -> Dict[str, Any]:
        """
        Take a screenshot of the current screen.
        
        Returns:
            Dictionary with the screenshot data
        """
        try:
            # Capture the screen
            screenshot = ImageGrab.grab()
            
            # Get original dimensions
            original_width, original_height = screenshot.size
            
            # Resize to a more reasonable size (50% of original)
            max_width = 800
            if original_width > max_width:
                scale_factor = max_width / original_width
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to base64 for transmission
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG", optimize=True, quality=85)
            img_bytes = buffered.getvalue()
            img_str = base64.b64encode(img_bytes).decode()
            
            # Get screen dimensions
            width, height = screenshot.size
            
            # Debug info
            img_size = len(img_bytes)
            b64_size = len(img_str)
            
            return {
                "success": True,
                "width": width,
                "height": height,
                "screenshot": f"data:image/png;base64,{img_str}",
                "message": f"Screenshot taken successfully. Image size: {img_size} bytes, Base64 size: {b64_size} bytes",
            }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return {
                "success": False,
                "message": f"Failed to take screenshot: {str(e)}\n{error_trace}",
            }
            
    def execute(self, action: str, x: Optional[int] = None, y: Optional[int] = None, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the computer tool with the given parameters.
        
        Args:
            action: Action to perform (only screenshot is allowed)
            x: X coordinate for mouse actions (not used)
            y: Y coordinate for mouse actions (not used)
            text: Text to type for the type action (not used)
            
        Returns:
            Result of the tool execution
        """
        if action == "screenshot":
            return self._take_screenshot()
        else:
            return {
                "success": False,
                "message": "Only screenshot action is supported for safety purposes",
            }