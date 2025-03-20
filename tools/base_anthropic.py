"""
Base tool framework for Anthropic's computer use tools.

This module provides the base classes and utilities for implementing
tools compatible with Anthropic's computer use API.
"""
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, fields, replace
from typing import Any, Optional, TypedDict, cast, Dict

class BaseAnthropicTool(metaclass=ABCMeta):
    """
    Abstract base class for Anthropic-defined tools.
    
    This class defines the interface that all tools must implement
    to be compatible with Anthropic's computer use API.
    """
    
    @abstractmethod
    async def __call__(self, **kwargs) -> Any:
        """
        Executes the tool with the given arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Result of the tool execution
        """
        ...

    @abstractmethod
    def to_params(self) -> Dict[str, Any]:
        """
        Convert the tool to parameters expected by the Anthropic API.
        
        Returns:
            Dictionary representation of the tool parameters
        """
        raise NotImplementedError


@dataclass(frozen=True)
class ToolResult:
    """
    Represents the result of a tool execution.
    
    This class provides a standardized way to represent tool results,
    including output, error messages, screenshots, and system messages.
    """
    output: Optional[str] = None
    error: Optional[str] = None
    base64_image: Optional[str] = None
    system: Optional[str] = None
    
    def __bool__(self):
        """Return True if any field has a value."""
        return any(getattr(self, field.name) for field in fields(self))
    
    def __add__(self, other: "ToolResult") -> "ToolResult":
        """Combine two tool results."""
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ) -> Optional[str]:
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine non-concatenable fields")
            return field or other_field
        
        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )
    
    def replace(self, **kwargs) -> "ToolResult":
        """Returns a new ToolResult with the given fields replaced."""
        return replace(self, **kwargs)


class ToolError(Exception):
    """
    Exception raised when a tool encounters an error.
    
    This exception is used to signal that a tool operation failed,
    allowing the error to be properly reported to Claude.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ToolOptions(TypedDict, total=False):
    """Base type for tool options."""
    pass


class ToolCollection:
    """
    Collection of tools available to the agent.
    
    This class manages a set of tools and provides methods to
    retrieve tool parameters and execute tool calls.
    """
    
    def __init__(self, *tools: BaseAnthropicTool):
        """
        Initialize the tool collection.
        
        Args:
            *tools: Tools to include in the collection
        """
        self.tools = {tool.__class__.__name__: tool for tool in tools}
    
    def to_params(self) -> list[Dict[str, Any]]:
        """
        Get parameters for all tools in the collection.
        
        Returns:
            List of tool parameters for the Anthropic API
        """
        return [tool.to_params() for tool in self.tools.values()]
    
    async def run(self, name: str, tool_input: Dict[str, Any]) -> ToolResult:
        """
        Run a tool with the given input.
        
        Args:
            name: Name of the tool to run
            tool_input: Input parameters for the tool
            
        Returns:
            Result of the tool execution
            
        Raises:
            ToolError: If the tool is not found or execution fails
        """
        tool = self.tools.get(name)
        if not tool:
            raise ToolError(f"Tool not found: {name}")
        
        try:
            return await tool(**tool_input)
        except ToolError as e:
            # Pass through ToolError
            raise
        except Exception as e:
            # Wrap other exceptions in ToolError
            raise ToolError(f"Tool execution failed: {str(e)}")