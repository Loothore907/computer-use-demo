"""
Agent loop implementation for computer use demo.

This module implements an async agent loop that integrates with
Anthropic's API and the computer use tools.
"""
import asyncio
import json
import logging
import os
import time
import base64
import datetime
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import anthropic
from anthropic import Anthropic
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlockParam,
)

from tools import (
    ToolCollection,
    ToolError,
    ToolResult,
    ToolVersion,
    get_tool_group,
)

# Configure logging
logger = logging.getLogger("agent-loop")


class AgentLoop:
    """
    Agent loop for computer use demo.
    
    This class implements an async agent loop that:
    1. Takes user input
    2. Passes it to Claude with tools
    3. Gets the response and tool calls
    4. Executes the tool calls
    5. Returns the response to the user
    
    The loop maintains conversation history and available tools.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        beta_flag: str = "computer-use-2024-10-22",
        tool_version: ToolVersion = ToolVersion.V20241022,
        session_dirs: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the agent loop.
        
        Args:
            api_key: Anthropic API key
            model: Model to use for the agent
            beta_flag: Beta flag for computer use tools
            tool_version: Tool version to use
            session_dirs: Dictionary with paths to session directories
        """
        self.api_key = api_key
        self.model = model
        self.beta_flag = beta_flag
        self.tool_version = tool_version
        self.session_dirs = session_dirs or {}
        
        logger.info(f"Initializing AgentLoop with model={model}, beta_flag={beta_flag}, tool_version={tool_version}")
        if session_dirs:
            logger.info(f"Using session directories: session_id={session_dirs.get('session_id', 'unknown')}")
        
        # Initialize tools
        self.tool_collection = self._initialize_tools()
        
        # Initialize conversation history
        self.conversation_history = []
        self.processed_tool_ids = set()  # Track which tool IDs have been processed
        
        # API client settings
        self.max_retries = 3
        self.retry_delay = 1
        self.max_token_limit = 150000  # Maximum token count to preserve in conversation history
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_api_time": 0,
            "tool_usage": {},
            "errors": {
                "api": 0,
                "tool": 0,
                "other": 0
            }
        }
        
        logger.info("AgentLoop initialized successfully")
    
    def _initialize_tools(self) -> ToolCollection:
        """
        Initialize the tools for the agent.
        
        Returns:
            ToolCollection instance with the appropriate tools
        """
        logger.info(f"Initializing tools for version {self.tool_version}")
        
        # Get the tool group for the specified version
        tool_group = get_tool_group(self.tool_version)
        
        # Create tool instances
        tools = []
        for tool_class in tool_group.tools:
            try:
                tool = tool_class()
                tools.append(tool)
                logger.info(f"Initialized tool: {tool_class.__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize tool {tool_class.__name__}: {e}")
                logger.error(traceback.format_exc())
        
        # Create tool collection
        tool_collection = ToolCollection(*tools)
        logger.info(f"Initialized {len(tools)} tools")
        
        return tool_collection
    
    def _handle_screenshot(
        self, image_data: str, source: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Handle screenshot data by saving it to the screenshots directory.
        
        Args:
            image_data: Base64-encoded image data
            source: Source of the screenshot
            context: Additional context about the screenshot
        
        Returns:
            Path to the saved screenshot
        """
        if not self.session_dirs or "screenshot" not in self.session_dirs:
            logger.warning("No screenshot directory available, skipping screenshot storage")
            return ""
        
        try:
            # Create a timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"{source}_screenshot_{timestamp}.png"
            filepath = os.path.join(self.session_dirs["screenshot"], filename)
            
            # Save the image
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            logger.info(f"Saved screenshot: {filepath}")
            
            # Save context if available
            if context:
                context_path = filepath.replace(".png", "_context.json")
                with open(context_path, "w") as f:
                    json.dump(context, f, indent=2)
                logger.debug(f"Saved screenshot context: {context_path}")
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            logger.error(traceback.format_exc())
            return ""
    
    def _handle_tool_output(
        self, output: Any, tool_name: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle tool output by saving it to the tool outputs directory.
        
        Args:
            output: Tool output data
            tool_name: Name of the tool
            context: Additional context about the tool call
        """
        if not self.session_dirs or "tool_output" not in self.session_dirs:
            logger.warning("No tool output directory available, skipping tool output storage")
            return
        
        try:
            # Create a timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"{tool_name}_output_{timestamp}.json"
            filepath = os.path.join(self.session_dirs["tool_output"], filename)
            
            # Prepare data
            data = {
                "tool": tool_name,
                "timestamp": timestamp,
                "output": output
            }
            
            if context:
                data["context"] = context
            
            # Save the output
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved tool output: {filepath}")
        except Exception as e:
            logger.error(f"Error saving tool output: {e}")
            logger.error(traceback.format_exc())
    
    def clear_history(self) -> None:
        """
        Clear conversation history completely.
        This should be called when the user clicks the "Clear History" button.
        """
        logger.info("Clearing conversation history")
        
        # Reset processed tool IDs
        self.processed_tool_ids = set()
        
        # Clear all history
        self.conversation_history = []
        
        # Save the updated history
        self._save_chat_history()
        
        logger.info(f"History cleared, {len(self.conversation_history)} messages remain")
    
    def _prune_conversation_history(self) -> None:
        """
        Prune conversation history to prevent exceeding token limits.
        This method uses a more aggressive approach to ensure we don't exceed token limits.
        """
        # Calculate approximate token count
        total_chars = sum(len(str(msg)) for msg in self.conversation_history)
        approx_tokens = total_chars // 4  # Rough estimate: 4 chars per token
        
        # Log token estimate
        logger.debug(f"Estimated history size: ~{approx_tokens:,} tokens")
        
        # If we're approaching the limit, take action
        if approx_tokens > self.max_token_limit:
            logger.warning(f"Conversation history too large ({approx_tokens} tokens), pruning aggressively")
            
            # Remove screenshots and large content from history
            for message in self.conversation_history:
                content = message.get("content", [])
                
                # Handle list type content
                if isinstance(content, list):
                    new_content = []
                    for item in content:
                        # For tool results
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            # Get content
                            result_content = item.get("content", "")
                            
                            # Check if it's a screenshot (base64 image)
                            if isinstance(result_content, str) and "data:image/png;base64," in result_content:
                                # Replace with placeholder
                                item["content"] = "[Screenshot removed to reduce token count]"
                            # Check if it's large text content
                            elif isinstance(result_content, str) and len(result_content) > 1000:
                                # Truncate
                                item["content"] = result_content[:1000] + "... [content truncated]"
                            
                            new_content.append(item)
                        else:
                            new_content.append(item)
                    
                    # Update content
                    message["content"] = new_content
                
                # Handle string content (messages)
                elif isinstance(content, str) and len(content) > 5000:
                    message["content"] = content[:5000] + "... [content truncated]"
            
            # If still too large, start removing older messages
            if len(self.conversation_history) > 10:
                # Keep only last 10 messages
                self.conversation_history = self.conversation_history[-10:]
                logger.warning("Pruned to last 10 messages")
            
            # If still too large, keep only the most recent exchange
            total_chars = sum(len(str(msg)) for msg in self.conversation_history)
            approx_tokens = total_chars // 4
            if approx_tokens > self.max_token_limit and len(self.conversation_history) > 2:
                # Find the last user message
                last_user_idx = None
                for i in range(len(self.conversation_history) - 1, -1, -1):
                    if self.conversation_history[i].get("role") == "user":
                        last_user_idx = i
                        break
                
                # Keep only from the last user message
                if last_user_idx is not None:
                    self.conversation_history = self.conversation_history[last_user_idx:]
                    logger.warning(f"Pruned to last exchange (from message {last_user_idx})")
                else:
                    # Fallback to keeping just the last message
                    self.conversation_history = self.conversation_history[-1:]
                    logger.warning("Pruned to last message only")
        
        logger.debug(f"After pruning: {len(self.conversation_history)} messages")
    
    def add_message(self, role: str, content: Any) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message (user or assistant)
            content: Content of the message (string or list of content blocks)
        """
        # Before adding new message, prune history if needed
        self._prune_conversation_history()
        
        # For browser extracted content, limit size before adding to history
        if role == "user" and isinstance(content, list):
            new_content = []
            for item in content:
                # Handle tool results
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    result_content = item.get("content", "")
                    
                    # If it's a screenshot or large HTML content, limit it
                    if isinstance(result_content, str):
                        if "data:image/png;base64," in result_content:
                            # Replace with a placeholder
                            item = {
                                "type": "tool_result",
                                "tool_use_id": item.get("tool_use_id", ""),
                                "content": "[Screenshot data - not included in context to save tokens]"
                            }
                        elif len(result_content) > 5000:
                            # Truncate large content
                            item["content"] = result_content[:5000] + "... [content truncated to save tokens]"
                    
                    new_content.append(item)
                else:
                    new_content.append(item)
            
            # Update content
            content = new_content
        
        # Add message to history
        self.conversation_history.append({"role": role, "content": content})
        logger.debug(f"Added {role} message to conversation history")
        
        # Save to chat file if available
        self._save_chat_history()
    
    def _save_chat_history(self) -> None:
        """Save the conversation history to the chat file."""
        if not self.session_dirs or "chat" not in self.session_dirs:
            return
        
        try:
            chat_file = os.path.join(self.session_dirs["chat"], "chat_history.json")
            with open(chat_file, "w") as f:
                json.dump(self.conversation_history, f, indent=2)
            logger.debug("Saved chat history")
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            logger.error(traceback.format_exc())
    
    def _make_api_tool_result(
        self, result: ToolResult, tool_use_id: str
    ) -> BetaToolResultBlockParam:
        """
        Convert a ToolResult to an API-compatible tool result block.
        
        Args:
            result: Tool result
            tool_use_id: ID of the tool use
            
        Returns:
            Tool result block for the API
        """
        # Prepare tool result content
        tool_result_content: List[BetaContentBlockParam] | str = []
        is_error = False
        
        # Handle error result
        if result.error:
            is_error = True
            if result.system:
                tool_result_content = f"<system>{result.system}</system>\n{result.error}"
            else:
                tool_result_content = result.error
        else:
            # Handle successful result
            if result.output:
                # Add text content
                text_block = {
                    "type": "text",
                    "text": result.output if not result.system else f"<system>{result.system}</system>\n{result.output}",
                }
                tool_result_content.append(cast(BetaContentBlockParam, text_block))
            
            # Add image content if available
            if result.base64_image:
                image_block = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                }
                tool_result_content.append(cast(BetaContentBlockParam, image_block))
        
        # Create the tool result block
        return {
            "type": "tool_result",
            "content": tool_result_content,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
        }
    
    def _response_to_params(self, response: anthropic.beta.Message) -> List[BetaContentBlockParam]:
        """
        Convert an API response to content block parameters.
        
        Args:
            response: API response
            
        Returns:
            List of content block parameters
        """
        result: List[BetaContentBlockParam] = []
        
        # Process each content block in the response
        for block in response.content:
            if block.type == "text":
                # Text block
                if block.text:
                    result.append(BetaTextBlockParam(type="text", text=block.text))
            else:
                # Tool use block
                result.append(cast(BetaToolUseBlockParam, block.model_dump()))
        
        return result
    
    def get_sanitized_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get a sanitized version of the conversation history with properly paired
        tool_use and tool_result blocks.
        
        Returns:
            Sanitized conversation history suitable for API calls
        """
        # Ensure we have a clean slate
        sanitized = []
        
        # Extract all tool uses and results
        tool_uses = {}
        tool_results = {}
        
        # Find all tool uses and results
        for msg in self.conversation_history:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                for item in msg.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_id = item.get("id")
                        if tool_id:
                            tool_uses[tool_id] = item
            
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                for item in msg.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        tool_id = item.get("tool_use_id")
                        if tool_id:
                            tool_results[tool_id] = item
        
        # Find tool IDs that appear in both uses and results
        valid_tool_ids = set(tool_uses.keys()) & set(tool_results.keys())
        
        # Keep track of tool IDs we've already processed
        processed_tool_ids = set()
        
        # Process the conversation history
        for msg in self.conversation_history:
            # Handle assistant messages with potential tool_use blocks
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                new_content = []
                tool_use_ids_in_message = set()
                
                # First, filter content to only include text and valid tool_use blocks
                for item in msg.get("content", []):
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            # Keep text blocks
                            new_content.append(item)
                        elif item.get("type") == "tool_use":
                            # Only keep tool_use blocks with matching tool_results
                            tool_id = item.get("id")
                            if tool_id and tool_id in valid_tool_ids and tool_id not in processed_tool_ids:
                                new_content.append(item)
                                tool_use_ids_in_message.add(tool_id)
                    else:
                        # Keep other content
                        new_content.append(item)
                
                # Only add the message if it has content
                if new_content:
                    sanitized.append({
                        "role": msg.get("role"),
                        "content": new_content
                    })
                    
                    # For each tool_use in this message, add corresponding tool_result
                    for tool_id in tool_use_ids_in_message:
                        if tool_id in tool_results and tool_id not in processed_tool_ids:
                            # Mark this tool ID as processed
                            processed_tool_ids.add(tool_id)
                            
                            # Add user message with tool_result
                            sanitized.append({
                                "role": "user",
                                "content": [tool_results[tool_id]]
                            })
            
            # Handle user messages with potential tool_result blocks
            elif msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # For user messages with tool results, only include them if we haven't processed them already
                new_content = []
                has_tool_results = False
                
                for item in msg.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        # Skip already processed tool results
                        tool_id = item.get("tool_use_id")
                        if tool_id in processed_tool_ids:
                            continue
                        # Skip tool results without matching tool uses
                        if tool_id not in valid_tool_ids:
                            continue
                        # This is a valid tool result we haven't processed yet
                        new_content.append(item)
                        processed_tool_ids.add(tool_id)
                        has_tool_results = True
                    else:
                        # Non-tool content
                        new_content.append(item)
                
                # Only add user message if it has content that's not just tool results
                # or if it has unprocessed tool results
                if has_tool_results:
                    sanitized.append({
                        "role": msg.get("role"),
                        "content": new_content
                    })
                elif not any(isinstance(item, dict) and item.get("type") == "tool_result" for item in msg.get("content", [])):
                    # This is a regular user message without tool results
                    sanitized.append(msg)
            
            # Handle string content or other message types
            elif isinstance(msg.get("content"), str):
                sanitized.append(msg)
        
        # Calculate approximate token count
        total_chars = sum(len(str(msg)) for msg in sanitized)
        approx_tokens = total_chars // 4  # Rough estimate: 4 chars per token
        logger.debug(f"Sanitized history size: ~{approx_tokens:,} tokens")
        
        # If still too large, truncate aggressively
        if approx_tokens > self.max_token_limit and len(sanitized) > 2:
            # Find last user message that's not a tool result
            last_user_idx = None
            for i in range(len(sanitized) - 1, -1, -1):
                if sanitized[i].get("role") == "user" and (
                    isinstance(sanitized[i].get("content"), str) or
                    not any(isinstance(item, dict) and item.get("type") == "tool_result" 
                           for item in sanitized[i].get("content", []))
                ):
                    last_user_idx = i
                    break
            
            # Keep only the last exchange
            if last_user_idx is not None:
                sanitized = sanitized[last_user_idx:]
                logger.warning(f"History still too large, truncated to last exchange (from position {last_user_idx})")
            else:
                # Just keep the last message
                sanitized = sanitized[-1:]
                logger.warning("History still too large, truncated to last message only")
        
        return sanitized
    
    async def run_async(self, user_input: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Run the agent loop with the given user input.
        
        Args:
            user_input: User input
            
        Returns:
            Tuple of (assistant_message, tool_calls)
        """
        # Add user message to conversation history
        self.add_message("user", user_input)
        logger.info("Processing user input")
        
        # Initialize Anthropic client
        client = Anthropic(api_key=self.api_key)
        
        # Send the request with retry logic
        response = None
        request_start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"API call attempt {attempt+1}/{self.max_retries}")
                start_time = time.time()
                
                # Get a sanitized version of the conversation history
                sanitized_history = self.get_sanitized_conversation_history()
                
                # Get the tool group for the current version
                tool_group = get_tool_group(self.tool_version)
                
                # Make the API call
                betas = [tool_group.beta_flag] if tool_group.beta_flag else []
                response = await client.beta.messages.create(
                    model=self.model,
                    messages=sanitized_history,
                    max_tokens=4096,
                    tools=self.tool_collection.to_params(),
                    betas=betas
                )
                
                elapsed = time.time() - start_time
                self.stats["total_api_time"] += elapsed
                logger.info(f"Received response from Claude API in {elapsed:.2f} seconds")
                break
            except Exception as e:
                self.stats["errors"]["api"] += 1
                logger.error(f"API call failed (attempt {attempt+1}/{self.max_retries}): {e}")
                
                # Check if this is a token limit error
                if "prompt is too long" in str(e):
                    logger.warning("Token limit exceeded, clearing history and retrying")
                    # Aggressively clear history
                    self.clear_history()
                    # Add the user input again
                    self.add_message("user", user_input)
                # Check if this is a tool ID error
                elif "unexpected `tool_use_id` found in `tool_result` blocks" in str(e) or "Each `tool_result` block must have a corresponding `tool_use` block" in str(e):
                    logger.warning("Tool ID pairing error detected, clearing history and retrying")
                    # Clear history and retry
                    self.clear_history()
                    # Add the user input again
                    self.add_message("user", user_input)
                
                if attempt < self.max_retries - 1:
                    retry_time = self.retry_delay * (attempt + 1)
                    logger.info(f"Retrying in {retry_time} seconds...")
                    await asyncio.sleep(retry_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    logger.error(traceback.format_exc())
                    # Return a graceful error message rather than crashing
                    return f"I encountered an error communicating with the API after {self.max_retries} attempts: {str(e)}", []
        
        total_request_time = time.time() - request_start_time
        
        if not response:
            logger.error("No response received from API")
            # Return a graceful error message rather than crashing
            return "I did not receive a response from the API. Please try again.", []
        
        # Process the response
        try:
            # Extract assistant message from content blocks
            assistant_message = ""
            tool_calls = []
            
            # Convert the response to content block parameters
            response_params = self._response_to_params(response)
            
            # Process the response content blocks
            for content_block in response_params:
                if content_block["type"] == "text":
                    assistant_message = content_block["text"]
                elif content_block["type"] == "tool_use":
                    # Collect tool calls for later processing
                    tool_calls.append({
                        "name": content_block["name"],
                        "args": content_block["input"],
                        "id": content_block["id"]
                    })
            
            # First, add the assistant's response to conversation history WITH the tool_use blocks
            assistant_content = [{"type": "text", "text": assistant_message}]
            for content_block in response_params:
                if content_block["type"] == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": content_block["id"],
                        "name": content_block["name"],
                        "input": content_block["input"]
                    })

            # Add this complete message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # Process tool calls and collect results
            tool_results = []
            for content_block in response_params:
                if content_block["type"] == "tool_use":
                    tool_name = content_block["name"]
                    tool_input = content_block["input"]
                    tool_id = content_block["id"]
                    
                    # Avoid duplicate processing
                    if tool_id in self.processed_tool_ids:
                        logger.info(f"Tool ID {tool_id} already processed, skipping")
                        continue
                    
                    self.processed_tool_ids.add(tool_id)
                    
                    logger.info(f"Processing tool call: {tool_name} (ID: {tool_id})")
                    logger.debug(f"Tool arguments: {tool_input}")
                    
                    # Execute the tool
                    start_time = time.time()
                    try:
                        # Run the tool asynchronously
                        result = await self.tool_collection.run(tool_name, tool_input)
                        success = True
                        error_msg = None
                    except ToolError as e:
                        success = False
                        error_msg = str(e)
                        result = ToolResult(error=str(e))
                        logger.error(f"Tool error: {e}")
                    except Exception as e:
                        success = False
                        error_msg = str(e)
                        result = ToolResult(error=f"Unexpected error: {str(e)}")
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        logger.error(traceback.format_exc())
                    
                    duration = time.time() - start_time
                    
                    # Add to tool usage statistics
                    if tool_name not in self.stats["tool_usage"]:
                        self.stats["tool_usage"][tool_name] = {
                            "count": 0,
                            "success": 0,
                            "failures": 0,
                            "total_duration": 0
                        }
                    
                    self.stats["tool_usage"][tool_name]["count"] += 1
                    if success:
                        self.stats["tool_usage"][tool_name]["success"] += 1
                    else:
                        self.stats["tool_usage"][tool_name]["failures"] += 1
                        self.stats["errors"]["tool"] += 1
                    
                    self.stats["tool_usage"][tool_name]["total_duration"] += duration
                    
                    # Log the result
                    if success:
                        logger.info(f"Tool {tool_name} executed in {duration:.2f}s (success=True)")
                    else:
                        logger.error(f"Tool {tool_name} failed in {duration:.2f}s: {error_msg}")
                    
                    # Add to tool results
                    tool_results.append({
                        "name": tool_name,
                        "args": tool_input,
                        "result": result,
                        "tool_use_id": tool_id
                    })
                    
                    # Format the result for the API
                    tool_result_block = self._make_api_tool_result(result, tool_id)
                    
                    # Add to tool results collection
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": tool_result_block["content"],
                        "is_error": tool_result_block["is_error"]
                    })
            
            # Only if we have tool results, add them as a user message
            if tool_results:
                self.add_message("user", tool_results)
                
                # If we used any tools, add an instruction to provide feedback about the tool use
                if assistant_message:
                    assistant_message += "\n\n(I've just used the requested tool. Let me know if you need any further assistance.)"
            
            # Update token stats if available
            if hasattr(response, 'usage'):
                input_tokens = getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'output_tokens', 0)
                self.stats["total_tokens"] += input_tokens + output_tokens
                logger.debug(f"Total tokens: {input_tokens + output_tokens}")
            
            # Log response time
            logger.info(f"Total request+processing time: {total_request_time:.2f}s")
            
            # Return assistant message and tool calls
            return assistant_message, tool_calls
        except Exception as e:
            self.stats["errors"]["other"] += 1
            logger.error(f"Failed to process response: {e}")
            logger.error(traceback.format_exc())
            # Return a graceful error message rather than crashing
            return f"I encountered an error processing the response: {str(e)}", []
    
    def run(self, user_input: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Synchronous wrapper for the async run method.
        
        Args:
            user_input: User input
            
        Returns:
            Tuple of (assistant_message, tool_calls)
        """
        # Use asyncio to run the async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.run_async(user_input))
        finally:
            loop.close()