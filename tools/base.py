"""
Base tool implementation.
"""
from abc import ABC, abstractmethod
import json
from typing import Any, Dict, List, Optional


class Tool(ABC):
    """
    Base class for all tools.
    """

    def __init__(self, name: str, description: str, parameters: Dict[str, Any] = None):
        """
        Initialize a tool.

        Args:
            name: The name of the tool
            description: A description of what the tool does
            parameters: A dictionary describing the parameters the tool accepts
        """
        self.name = name
        self.description = description
        self.parameters = parameters or {}

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Parameters for the tool

        Returns:
            The result of the tool execution
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary for the Claude API.

        Returns:
            A dictionary representing the tool
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }