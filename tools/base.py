"""
Base tool class for computer use demo.
"""
import json
import logging
import time
import traceback
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger("tools")

class Tool:
    """
    Base class for tools.
    
    This class defines the interface that all tools must implement,
    and provides utilities for converting tools to the format expected
    by the Anthropic API.
    """
    
    def __init__(self, name: str, description: str, callback: Optional[Callable] = None):
        """
        Initialize the tool.
        
        Args:
            name: Tool name
            description: Tool description
            callback: Optional callback function to handle tool outputs
        """
        self.name = name
        self.description = description
        self.callback = callback
        logger.debug(f"Initialized tool: {name}")
        
        # Stats
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_duration = 0.0
    
    def run(self, *args, **kwargs) -> Any:
        """
        Run the tool. This should be implemented by subclasses.
        """
        start_time = time.time()
        self.total_calls += 1
        error = None
        
        try:
            logger.info(f"Running tool: {self.name}")
            logger.debug(f"Tool arguments: args={args}, kwargs={kwargs}")
            
            # Run the tool
            result = self._run(*args, **kwargs)
            
            # Record success
            duration = time.time() - start_time
            self.successful_calls += 1
            self.total_duration += duration
            logger.info(f"Tool {self.name} succeeded in {duration:.2f}s")
            
            # Call callback if available
            if self.callback:
                context = {"args": args, "kwargs": kwargs, "duration": duration}
                self.callback(result, self.name, context)
            
            return result
        except Exception as e:
            # Record failure
            duration = time.time() - start_time
            self.failed_calls += 1
            self.total_duration += duration
            error = str(e)
            logger.error(f"Tool {self.name} failed in {duration:.2f}s: {error}")
            logger.error(traceback.format_exc())
            
            # Call callback if available
            if self.callback:
                context = {
                    "args": args, 
                    "kwargs": kwargs, 
                    "duration": duration,
                    "error": error,
                    "traceback": traceback.format_exc()
                }
                self.callback(None, self.name, context)
            
            raise
    
    def _run(self, *args, **kwargs) -> Any:
        """
        Actual tool implementation. This should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary for the Anthropic API.
        
        This method should be implemented by subclasses based on their
        specific input and output types.
        
        Returns:
            Dictionary representation of the tool
        """
        raise NotImplementedError("Subclasses must implement this method") 