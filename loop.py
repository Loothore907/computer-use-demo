"""
Agent loop implementation.
"""
import json
import os
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Literal

import anthropic
from anthropic.types import Message, MessageParam

from tools import Tool as BaseTool
from tools.computer import ComputerTool

# Define our own Tool class since it's not in the latest SDK
class ToolParameter(TypedDict):
    type: str
    description: Optional[str]
    enum: Optional[List[str]]
    
class ToolParameterProperties(TypedDict):
    type: str
    properties: Dict[str, ToolParameter]
    required: Optional[List[str]]

class Tool(TypedDict):
    name: str
    description: str
    input_schema: ToolParameterProperties

class AgentLoop:
    """
    Agent loop for the computer use demo.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        """
        Initialize the agent loop.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)
            model: Model to use for the agent
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("No API key provided")

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Initialize tools - only using screenshot capability
        self.computer_tool = ComputerTool()
        
        self.tools = [
            self.computer_tool,
        ]
        
        self.messages: List[Dict[str, Any]] = []
        self.system_prompt = (
            "You are Claude, an AI assistant that can take screenshots of the computer. "
            "You have access to a 'computer' tool that has a 'screenshot' action. "
            "When a user asks you to take a screenshot, you MUST use this tool by calling the computer tool with the screenshot action. "
            "Do not pretend to take screenshots - you must actually use the tool. "
            "After taking a screenshot, the image will be displayed to the user automatically. "
            "Here's an example: When a user says 'take a screenshot', call the computer tool with action='screenshot'."
        )

    def add_message(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the conversation history.

        Args:
            message: Message to add
        """
        self.messages.append(message)

    def get_api_tools(self) -> List[Dict[str, Any]]:
        """
        Get the tools in the format expected by the Anthropic API.

        Returns:
            List of tools in API format
        """
        api_tools = []
        for tool in self.tools:
            tool_dict = tool.to_dict()
            api_tools.append({
                "name": tool_dict["name"],
                "description": tool_dict["description"],
                "input_schema": {
                    "type": "object",
                    "properties": tool_dict["parameters"]["properties"],
                    "required": tool_dict["parameters"].get("required", [])
                }
            })
        return api_tools

    def run(self, user_input: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Run the agent loop with the given user input.

        Args:
            user_input: User input to process

        Returns:
            Tuple of (agent response, tool calls made)
        """
        # Add user message to history
        self.add_message({"role": "user", "content": user_input})
        
        # Prepare messages for the API
        api_messages = []
        for msg in self.messages:
            if "tool_calls" in msg and msg["tool_calls"]:
                # Handle tool calls in assistant messages
                api_messages.append({
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                    "tool_calls": msg["tool_calls"]
                })
            elif "tool_call" in msg and msg["tool_call"]:
                # Handle tool responses
                api_messages.append({
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                    "tool_call_id": msg["tool_call"]["id"],
                })
            else:
                # Handle regular messages
                api_messages.append({
                    "role": msg["role"],
                    "content": msg.get("content", "")
                })

        # Get tools for debugging
        tools = self.get_api_tools()
        print(f"Using model: {self.model}")
        print(f"Available tools: {json.dumps(tools, indent=2)}")
        
        # Call the API
        response = self.client.messages.create(
            model=self.model,
            system=self.system_prompt,
            messages=api_messages,
            tools=tools,
            max_tokens=4096,
        )
        
        # Log response for debugging
        print(f"Raw response: {response}")
        
        # Process the response
        tool_calls = []
        user_facing_content = ""
        
        # The new API returns tool use blocks in the content
        if hasattr(response, 'content') and isinstance(response.content, list):
            for block in response.content:
                if block.type == 'text':
                    # Remove thinking tags if present
                    text = block.text
                    if "<thinking>" in text and "</thinking>" in text:
                        parts = text.split("</thinking>")
                        if len(parts) > 1:
                            text = parts[1].strip()
                        else:
                            text = ""
                    user_facing_content += text
                elif block.type == 'tool_use':
                    print(f"Tool use block found: {block}")
                    tool_name = block.name
                    tool_args = block.input
                    tool_id = block.id
                    
                    print(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Find the matching tool
                    for tool in self.tools:
                        if tool.name == tool_name:
                            # Execute the tool
                            result = tool.execute(**tool_args)
                            
                            print(f"Tool result: {result}")
                            
                            # Record the tool call
                            tool_call = {
                                "id": tool_id,
                                "name": tool_name,
                                "args": tool_args,
                                "result": result
                            }
                            tool_calls.append(tool_call)
                            
                            # Add tool call to messages
                            self.add_message({
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [{
                                    "id": tool_id,
                                    "name": tool_name,
                                    "args": tool_args
                                }]
                            })
                            
                            # Add tool response to messages
                            self.add_message({
                                "role": "tool",
                                "content": str(result),
                                "tool_call": {
                                    "id": tool_id,
                                    "name": tool_name
                                }
                            })
                            
                            break
        else:
            # Fall back to old approach if content is not structured as expected
            user_facing_content = response.content[0].text if hasattr(response.content, '__iter__') else response.content
            print("No tool use blocks found in response")
        
        # Add assistant response to messages
        self.add_message({
            "role": "assistant",
            "content": user_facing_content
        })
        
        return user_facing_content, tool_calls