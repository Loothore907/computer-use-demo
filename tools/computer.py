"""
Computer tool implementation for direct OS control.

This module provides the ComputerTool class which allows Claude
to interact with the screen, keyboard, and mouse.
"""
import asyncio
import base64
import logging
import os
import shlex
import shutil
from enum import Enum
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple, TypedDict, Union, cast, get_args
from uuid import uuid4

from anthropic.types.beta import BetaToolComputerUse20241022Param, BetaToolUnionParam

from .base_anthropic import BaseAnthropicTool, ToolError, ToolResult

logger = logging.getLogger("tools.computer")

# StrEnum is not available in Python 3.10, so we implement it ourselves
class StrEnum(str, Enum):
    """String enumeration that behaves like both a string and an enum."""
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

# Define directories for outputs
OUTPUT_DIR = "/tmp/outputs"

# Typing delay for realistic human-like input
TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

# Action types supported by the 2024-10-22 API version
Action_20241022 = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]

# Additional action types in newer API version
Action_20250124 = (
    Action_20241022
    | Literal[
        "left_mouse_down",
        "left_mouse_up",
        "scroll",
        "hold_key",
        "wait",
        "triple_click",
    ]
)

# Scroll directions
ScrollDirection = Literal["up", "down", "left", "right"]


class Resolution(TypedDict):
    """Screen resolution type."""
    width: int
    height: int


# Target resolutions for scaling
MAX_SCALING_TARGETS: Dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}

# Button mappings for xdotool
CLICK_BUTTONS = {
    "left_click": 1,
    "right_click": 3,
    "middle_click": 2,
    "double_click": "--repeat 2 --delay 10 1",
    "triple_click": "--repeat 3 --delay 10 1",
}


class ScalingSource(StrEnum):
    """Source of coordinates for scaling."""
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    """Options for the computer tool."""
    display_height_px: int
    display_width_px: int
    display_number: Optional[int]


def chunks(s: str, chunk_size: int) -> list[str]:
    """Split a string into chunks of the given size."""
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class BaseComputerTool:
    """
    Base implementation of the computer tool.
    
    This class provides the core functionality for interacting with the
    screen, keyboard, and mouse. It is extended by version-specific
    implementations that expose the appropriate API.
    """
    
    name: Literal["computer"] = "computer"
    width: int
    height: int
    display_num: Optional[int]
    _screenshot_delay = 2.0
    _scaling_enabled = True
    
    @property
    def options(self) -> ComputerToolOptions:
        """Get the computer tool options."""
        width, height = self.scale_coordinates(
            ScalingSource.COMPUTER, self.width, self.height
        )
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }
    
    def __init__(self):
        """Initialize the computer tool."""
        # Get screen dimensions from environment
        self.width = int(os.getenv("WIDTH") or 0)
        self.height = int(os.getenv("HEIGHT") or 0)
        assert self.width and self.height, "WIDTH, HEIGHT must be set"
        
        # Configure display
        if (display_num := os.getenv("DISPLAY_NUM")) is not None:
            self.display_num = int(display_num)
            self._display_prefix = f"DISPLAY=:{self.display_num} "
        else:
            self.display_num = None
            self._display_prefix = ""
        
        # Set up xdotool command prefix
        self.xdotool = f"{self._display_prefix}xdotool"
        
        logger.info(f"Initialized {self.__class__.__name__} with display {self.display_num or 'default'}")
        logger.info(f"Screen dimensions: {self.width}x{self.height}")
    
    async def __call__(
        self,
        *,
        action: Action_20241022,
        text: Optional[str] = None,
        coordinate: Optional[Tuple[int, int]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the computer tool with the given parameters.
        
        Args:
            action: Action to perform
            text: Text to type or key to press
            coordinate: Screen coordinates for mouse actions
            **kwargs: Additional action-specific parameters
            
        Returns:
            Result of the tool execution
            
        Raises:
            ToolError: If the action fails or parameters are invalid
        """
        logger.info(f"Computer tool action: {action}")
        
        # Mouse move and drag require coordinates
        if action in ("mouse_move", "left_click_drag"):
            if coordinate is None:
                raise ToolError(f"coordinate is required for {action}")
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            
            x, y = self.validate_and_get_coordinates(coordinate)
            if action == "mouse_move":
                command_parts = [self.xdotool, f"mousemove --sync {x} {y}"]
                return await self.shell(" ".join(command_parts))
            elif action == "left_click_drag":
                command_parts = [
                    self.xdotool,
                    f"mousedown 1 mousemove --sync {x} {y} mouseup 1",
                ]
                return await self.shell(" ".join(command_parts))
        
        # Keyboard actions require text
        if action in ("key", "type"):
            if text is None:
                raise ToolError(f"text is required for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")
            if not isinstance(text, str):
                raise ToolError(f"{text} must be a string")
            
            if action == "key":
                command_parts = [self.xdotool, f"key -- {text}"]
                return await self.shell(" ".join(command_parts))
            elif action == "type":
                results: list[ToolResult] = []
                for chunk in chunks(text, TYPING_GROUP_SIZE):
                    command_parts = [
                        self.xdotool,
                        f"type --delay {TYPING_DELAY_MS} -- {shlex.quote(chunk)}",
                    ]
                    results.append(
                        await self.shell(" ".join(command_parts), take_screenshot=False)
                    )
                
                # Take a screenshot after typing is complete
                screenshot_result = await self.screenshot()
                
                # Combine all results
                combined_result = ToolResult(
                    output="".join(result.output or "" for result in results),
                    error="".join(result.error or "" for result in results),
                    base64_image=screenshot_result.base64_image,
                )
                
                return combined_result
        
        # Simple actions
        if action in (
            "left_click",
            "right_click",
            "double_click",
            "middle_click",
            "screenshot",
            "cursor_position",
        ):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            
            if action == "screenshot":
                return await self.screenshot()
            elif action == "cursor_position":
                command_parts = [self.xdotool, "getmouselocation --shell"]
                result = await self.shell(
                    " ".join(command_parts),
                    take_screenshot=False,
                )
                
                # Parse the output to get X and Y coordinates
                output = result.output or ""
                try:
                    x = int(output.split("X=")[1].split("\n")[0])
                    y = int(output.split("Y=")[1].split("\n")[0])
                    
                    # Scale the coordinates
                    x, y = self.scale_coordinates(ScalingSource.COMPUTER, x, y)
                    
                    return result.replace(output=f"X={x},Y={y}")
                except (IndexError, ValueError):
                    raise ToolError(f"Failed to parse cursor position: {output}")
            else:
                # Click actions
                command_parts = [self.xdotool, f"click {CLICK_BUTTONS[action]}"]
                return await self.shell(" ".join(command_parts))
        
        # If we get here, the action is not supported
        raise ToolError(f"Invalid action: {action}")
    
    def validate_and_get_coordinates(
        self, coordinate: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        """
        Validate coordinates and scale them if needed.
        
        Args:
            coordinate: Coordinates to validate
            
        Returns:
            Validated and scaled coordinates
            
        Raises:
            ToolError: If coordinates are invalid
        """
        if not isinstance(coordinate, tuple) or len(coordinate) != 2:
            raise ToolError(f"{coordinate} must be a tuple of length 2")
        
        if not all(isinstance(i, int) and i >= 0 for i in coordinate):
            raise ToolError(f"{coordinate} must be a tuple of non-negative ints")
        
        return self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])
    
    async def screenshot(self) -> ToolResult:
        """
        Take a screenshot of the current screen.
        
        Returns:
            ToolResult with the screenshot as a base64-encoded image
            
        Raises:
            ToolError: If the screenshot fails
        """
        logger.info("Taking screenshot")
        
        # Create output directory
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename for screenshot
        path = output_dir / f"screenshot_{uuid4().hex}.png"
        
        # Try gnome-screenshot first, fall back to scrot
        if shutil.which("gnome-screenshot"):
            screenshot_cmd = f"{self._display_prefix}gnome-screenshot -f {path} -p"
        else:
            # Fall back to scrot if gnome-screenshot isn't available
            screenshot_cmd = f"{self._display_prefix}scrot -p {path}"
        
        # Take the screenshot
        result = await self.shell(screenshot_cmd, take_screenshot=False)
        
        # Scale the screenshot if enabled
        if self._scaling_enabled:
            x, y = self.scale_coordinates(ScalingSource.COMPUTER, self.width, self.height)
            await self.shell(f"convert {path} -resize {x}x{y}! {path}", take_screenshot=False)
        
        # Check if the screenshot was taken successfully
        if path.exists():
            # Read the screenshot and convert to base64
            with open(path, "rb") as f:
                image_data = f.read()
            
            # Return the result with the base64-encoded image
            return result.replace(base64_image=base64.b64encode(image_data).decode())
        
        # If we get here, the screenshot failed
        raise ToolError(f"Failed to take screenshot: {result.error}")
    
    async def shell(self, command: str, take_screenshot: bool = True) -> ToolResult:
        """
        Run a shell command.
        
        Args:
            command: Command to run
            take_screenshot: Whether to take a screenshot after the command
            
        Returns:
            Result of the command execution
        """
        logger.info(f"Running shell command: {command}")
        
        # Create process
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        # Decode output
        stdout_str = stdout.decode() if stdout else None
        stderr_str = stderr.decode() if stderr else None
        
        # Take screenshot if requested
        base64_image = None
        if take_screenshot:
            # Delay to let things settle
            await asyncio.sleep(self._screenshot_delay)
            try:
                base64_image = (await self.screenshot()).base64_image
            except ToolError:
                # Ignore screenshot errors
                pass
        
        return ToolResult(
            output=stdout_str,
            error=stderr_str,
            base64_image=base64_image,
        )
    
    def scale_coordinates(
        self, source: ScalingSource, x: int, y: int
    ) -> Tuple[int, int]:
        """
        Scale coordinates to or from the target resolution.
        
        Args:
            source: Source of the coordinates
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Scaled coordinates
        """
        if not self._scaling_enabled:
            return x, y
        
        # Calculate aspect ratio
        ratio = self.width / self.height
        target_dimension = None
        
        # Find the closest target resolution with the same aspect ratio
        for dimension in MAX_SCALING_TARGETS.values():
            # Allow some error in the aspect ratio
            if abs(dimension["width"] / dimension["height"] - ratio) < 0.02:
                if dimension["width"] < self.width:
                    target_dimension = dimension
                break
        
        # If no suitable target resolution was found, return the original coordinates
        if target_dimension is None:
            return x, y
        
        # Calculate scaling factors
        x_scaling_factor = target_dimension["width"] / self.width
        y_scaling_factor = target_dimension["height"] / self.height
        
        if source == ScalingSource.API:
            # Validate coordinates
            if x > self.width or y > self.height:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")
            
            # Scale up from API to computer
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        
        # Scale down from computer to API
        return round(x * x_scaling_factor), round(y * y_scaling_factor)


class ComputerTool20241022(BaseComputerTool, BaseAnthropicTool):
    """
    Computer tool implementation for the 2024-10-22 API version.
    
    This class implements the computer tool compatible with the
    'computer-use-2024-10-22' beta flag.
    """
    
    api_type: Literal["computer_20241022"] = "computer_20241022"
    
    def to_params(self) -> BetaToolComputerUse20241022Param:
        """
        Convert the tool to parameters expected by the Anthropic API.
        
        Returns:
            Tool parameters dictionary
        """
        return {"name": self.name, "type": self.api_type, **self.options}


class ComputerTool20250124(BaseComputerTool, BaseAnthropicTool):
    """
    Computer tool implementation for the 2025-01-24 API version.
    
    This class implements the computer tool compatible with the
    newer API version, adding support for additional actions.
    """
    
    api_type: Literal["computer_20250124"] = "computer_20250124"
    
    def to_params(self) -> BetaToolUnionParam:
        """
        Convert the tool to parameters expected by the Anthropic API.
        
        Returns:
            Tool parameters dictionary
        """
        return cast(
            BetaToolUnionParam,
            {"name": self.name, "type": self.api_type, **self.options},
        )
    
    async def __call__(
        self,
        *,
        action: Action_20250124,
        text: Optional[str] = None,
        coordinate: Optional[Tuple[int, int]] = None,
        scroll_direction: Optional[ScrollDirection] = None,
        scroll_amount: Optional[int] = None,
        duration: Optional[Union[int, float]] = None,
        key: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the computer tool with the given parameters.
        
        This method extends the base implementation with additional actions
        supported by the newer API version.
        
        Args:
            action: Action to perform
            text: Text to type or key to press
            coordinate: Screen coordinates for mouse actions
            scroll_direction: Direction to scroll
            scroll_amount: Amount to scroll
            duration: Duration for hold or wait actions
            key: Key to hold
            **kwargs: Additional action-specific parameters
            
        Returns:
            Result of the tool execution
            
        Raises:
            ToolError: If the action fails or parameters are invalid
        """
        # Handle new actions
        if action in ("left_mouse_down", "left_mouse_up"):
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action=}.")
            
            command_parts = [
                self.xdotool,
                f"{'mousedown' if action == 'left_mouse_down' else 'mouseup'} 1",
            ]
            return await self.shell(" ".join(command_parts))
        
        if action == "scroll":
            if scroll_direction is None or scroll_direction not in get_args(ScrollDirection):
                raise ToolError(f"{scroll_direction=} must be 'up', 'down', 'left', or 'right'")
            
            if not isinstance(scroll_amount, int) or scroll_amount < 0:
                raise ToolError(f"{scroll_amount=} must be a non-negative int")
            
            # Move mouse to target position if coordinates are provided
            mouse_move_part = ""
            if coordinate is not None:
                x, y = self.validate_and_get_coordinates(coordinate)
                mouse_move_part = f"mousemove --sync {x} {y}"
            
            # Map scroll direction to button
            scroll_button = {
                "up": 4,
                "down": 5,
                "left": 6,
                "right": 7,
            }[scroll_direction]
            
            # Build command
            command_parts = [self.xdotool, mouse_move_part]
            
            # Add modifier key if provided
            if text:
                command_parts.append(f"keydown {text}")
            
            # Add scroll command
            command_parts.append(f"click --repeat {scroll_amount} {scroll_button}")
            
            # Release modifier key if provided
            if text:
                command_parts.append(f"keyup {text}")
            
            return await self.shell(" ".join(command_parts))
        
        if action in ("hold_key", "wait"):
            if duration is None or not isinstance(duration, (int, float)):
                raise ToolError(f"{duration=} must be a number")
            
            if duration < 0:
                raise ToolError(f"{duration=} must be non-negative")
            
            if duration > 100:
                raise ToolError(f"{duration=} is too long.")
            
            if action == "hold_key":
                if text is None:
                    raise ToolError(f"text is required for {action}")
                
                # Escape keys for shell
                escaped_keys = shlex.quote(text)
                
                # Build command
                command_parts = [
                    self.xdotool,
                    f"keydown {escaped_keys}",
                    f"sleep {duration}",
                    f"keyup {escaped_keys}",
                ]
                
                return await self.shell(" ".join(command_parts))
            
            if action == "wait":
                # Sleep for the specified duration
                await asyncio.sleep(duration)
                
                # Take a screenshot
                return await self.screenshot()
        
        if action in (
            "left_click",
            "right_click",
            "double_click",
            "triple_click",
            "middle_click",
        ):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            
            # Move mouse to target position if coordinates are provided
            mouse_move_part = ""
            if coordinate is not None:
                x, y = self.validate_and_get_coordinates(coordinate)
                mouse_move_part = f"mousemove --sync {x} {y}"
            
            # Build command
            command_parts = [self.xdotool, mouse_move_part]
            
            # Add modifier key if provided
            if key:
                command_parts.append(f"keydown {key}")
            
            # Add click command
            command_parts.append(f"click {CLICK_BUTTONS[action]}")
            
            # Release modifier key if provided
            if key:
                command_parts.append(f"keyup {key}")
            
            return await self.shell(" ".join(command_parts))
        
        # Fall back to base implementation for other actions
        return await super().__call__(
            action=action, text=text, coordinate=coordinate, key=key, **kwargs
        )