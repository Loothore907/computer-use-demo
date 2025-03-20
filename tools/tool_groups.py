"""
Tool versioning and grouping.

This module provides utilities for managing different versions of tools.
"""
from enum import Enum
from typing import Dict, List, Optional, Type

from .base_anthropic import BaseAnthropicTool


class ToolVersion(str, Enum):
    """Available tool versions."""
    V20241022 = "20241022"
    V20250124 = "20250124"


class ToolGroup:
    """Group of tools for a specific API version."""
    
    def __init__(
        self,
        version: ToolVersion,
        tools: List[Type[BaseAnthropicTool]],
        beta_flag: Optional[str] = None
    ):
        """
        Initialize a tool group.
        
        Args:
            version: Tool version
            tools: List of tool classes
            beta_flag: Beta flag for the API
        """
        self.version = version
        self.tools = tools
        self.beta_flag = beta_flag


# Import tool classes
from .computer import ComputerTool20241022, ComputerTool20250124


# Define tool groups for different API versions
TOOL_GROUPS_BY_VERSION: Dict[ToolVersion, ToolGroup] = {
    ToolVersion.V20241022: ToolGroup(
        version=ToolVersion.V20241022,
        tools=[ComputerTool20241022],
        beta_flag="computer-use-2024-10-22",
    ),
    ToolVersion.V20250124: ToolGroup(
        version=ToolVersion.V20250124,
        tools=[ComputerTool20250124],
        beta_flag="computer-use-2025-01-24",
    ),
}


def get_tool_group(version: ToolVersion) -> ToolGroup:
    """
    Get the tool group for the specified version.
    
    Args:
        version: Tool version
        
    Returns:
        Tool group
        
    Raises:
        ValueError: If the version is not found
    """
    if version not in TOOL_GROUPS_BY_VERSION:
        raise ValueError(f"Unsupported tool version: {version}")
    
    return TOOL_GROUPS_BY_VERSION[version]


def get_default_tool_group() -> ToolGroup:
    """
    Get the default tool group.
    
    Returns:
        Default tool group
    """
    return TOOL_GROUPS_BY_VERSION[ToolVersion.V20241022]