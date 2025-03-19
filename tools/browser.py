"""
Tool for capturing screenshots and browser information.
"""
import base64
import io
from typing import Any, Dict, Optional

from PIL import Image

from tools.base import Tool


class BrowserTool(Tool):
    """
    Tool for capturing screenshots and browser information.
    """
    
    def __init__(self, screenshot_function=None):
        """
        Initialize the browser tool.
        
        Args:
            screenshot_function: Function to capture screenshots
        """
        super().__init__(
            name="browser",
            description="Capture screenshots and browser information",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["screenshot"],
                        "description": "Action to perform (screenshot)",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "webp"],
                        "description": "Image format for screenshots",
                    },
                    "quality": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Image quality for lossy formats (jpg, webp)",
                    },
                },
                "required": ["action"],
            },
        )
        self.screenshot_function = screenshot_function
    
    def _capture_screenshot(self, format: str = "png", quality: int = 85) -> Dict[str, Any]:
        """
        Capture a screenshot of the current browser window.
        
        Args:
            format: Image format (png, jpg, webp)
            quality: Image quality for lossy formats
            
        Returns:
            Dictionary with the screenshot data
        """
        if self.screenshot_function is None:
            return {
                "success": False,
                "message": "Screenshot function not available",
            }
        
        try:
            # Capture screenshot using the provided function
            screenshot_data = self.screenshot_function()
            
            if not screenshot_data:
                return {
                    "success": False,
                    "message": "Failed to capture screenshot",
                }
            
            # Convert base64 data to PIL Image if it's base64 encoded
            if isinstance(screenshot_data, str) and screenshot_data.startswith("data:image"):
                # Extract the base64 data from the data URI
                base64_data = screenshot_data.split(",")[1]
                image_data = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_data))
            elif isinstance(screenshot_data, bytes):
                # If it's already bytes, open it directly
                image = Image.open(io.BytesIO(screenshot_data))
            else:
                # If it's already a PIL Image, use it directly
                image = screenshot_data
            
            # Convert to the desired format
            output = io.BytesIO()
            if format.lower() == "jpg":
                format = "jpeg"  # PIL uses "jpeg" not "jpg"
            
            image.save(output, format=format.upper(), quality=quality)
            output.seek(0)
            
            # Encode as base64 for return
            encoded = base64.b64encode(output.getvalue()).decode('ascii')
            mime_type = f"image/{format.lower()}"
            if format.lower() == "jpeg":
                mime_type = "image/jpeg"
            
            data_uri = f"data:{mime_type};base64,{encoded}"
            
            return {
                "success": True,
                "screenshot": data_uri,
                "format": format.lower(),
                "width": image.width,
                "height": image.height,
                "message": f"Screenshot captured ({image.width}x{image.height})",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to process screenshot: {str(e)}",
            }
    
    def execute(self, action: str, format: str = "png", quality: int = 85) -> Dict[str, Any]:
        """
        Execute the browser tool with the given parameters.
        
        Args:
            action: Action to perform (screenshot)
            format: Image format for screenshots
            quality: Image quality for lossy formats
            
        Returns:
            Result of the tool execution
        """
        if action == "screenshot":
            return self._capture_screenshot(format, quality)
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}",
            }