"""
Agent loop implementation for computer use demo.
"""
import json
import os
import time
import logging
import traceback
import base64
import datetime
import requests
from typing import Any, Dict, List, Optional, Tuple

# We'll use requests directly instead of the SDK
# import anthropic  # Import the official Anthropic SDK

from tools import ComputerTool, BashTool, EditTool, BrowserTool, SearchTool, DockerTool

# Configure logging
logger = logging.getLogger("agent-loop")

class SimpleAnthropicClient:
    """
    A very simple Anthropic API client that doesn't rely on the SDK.
    This avoids version compatibility issues.
    """
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def create_message(self, model, messages, tools=None, max_tokens=4096, beta=None):
        """Send a request to the Anthropic API."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
        
        # Add beta flags if provided
        if beta:
            self.headers["anthropic-beta"] = beta if isinstance(beta, str) else ",".join(beta)
        
        logger.debug(f"Sending API request to {self.base_url}")
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                raise Exception(error_msg)
            
            # Parse the response
            data = response.json()
            logger.debug("API request successful")
            
            # Return a simple response object
            return SimpleResponse(data)
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"API request failed: {e}")

class SimpleResponse:
    """A simple response object that mimics the Anthropic SDK response."""
    
    def __init__(self, data):
        self.id = data.get("id")
        self.model = data.get("model")
        self.content = []
        self.tool_calls = []
        
        # Parse response content
        content_data = data.get("content", [])
        for block in content_data:
            block_type = block.get("type")
            
            if block_type == "text":
                self.content.append(SimpleTextBlock(block))
            elif block_type == "tool_use":
                tool_call = SimpleToolCall(block)
                self.content.append(tool_call)
                self.tool_calls.append(tool_call)
        
        # Extract usage information
        usage_data = data.get("usage", {})
        self.usage = SimpleUsage(usage_data)

class SimpleTextBlock:
    """A simple text block object."""
    
    def __init__(self, data):
        self.type = "text"
        self.text = data.get("text", "")

class SimpleToolCall:
    """A simple tool call object."""
    
    def __init__(self, data):
        self.type = "tool_use"
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.input = data.get("input", {})

class SimpleUsage:
    """A simple usage information object."""
    
    def __init__(self, data):
        self.input_tokens = data.get("input_tokens", 0)
        self.output_tokens = data.get("output_tokens", 0)

class AgentLoop:
    """
    Agent loop for computer use demo.
    
    This class implements a simple agent loop that:
    1. Takes user input
    2. Passes it to Claude with tools
    3. Gets the response and tool calls
    4. Executes the tool calls
    5. Returns the response to the user
    
    The loop maintains conversation history and available tools.
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", 
                 beta_flag: str = "computer-use-2024-10-22", session_dirs: Optional[Dict[str, str]] = None):
        """
        Initialize the agent loop.
        
        Args:
            api_key: Anthropic API key
            model: Model to use for the agent (default: claude-3-5-sonnet-20241022)
            beta_flag: Beta flag for computer use tools (default: computer-use-2024-10-22)
            session_dirs: Dictionary with paths to session directories
        """
        self.api_key = api_key
        self.model = model
        self.beta_flag = beta_flag
        self.session_dirs = session_dirs or {}
        
        logger.info(f"Initializing AgentLoop with model={model}, beta_flag={beta_flag}")
        if session_dirs:
            logger.info(f"Using session directories: session_id={session_dirs.get('session_id', 'unknown')}")
        
        self.tools = self._get_tools()
        self.conversation_history = []
        self.tool_usage_history = []
        self.max_retries = 3
        self.retry_delay = 1
        
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
    
    def _get_tools(self) -> Dict[str, Any]:
        """
        Get the available tools for the agent.
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        logger.info("Initializing tools")
        tools = {
            "computer": ComputerTool(self._handle_screenshot),
            "bash": BashTool(self._handle_tool_output),
            "edit": EditTool(self._handle_tool_output),
            "browser": BrowserTool(self._handle_screenshot),
            "search": SearchTool(self._handle_tool_output),
            "docker": DockerTool(self._handle_tool_output),
        }
        
        # Format tools for Claude API
        api_tools = []
        for name, tool in tools.items():
            api_tools.append(tool.to_dict())
            logger.debug(f"Added tool: {name}")
        
        logger.info(f"Initialized {len(tools)} tools")
        return {
            "instances": tools,
            "api_tools": api_tools,
        }
    
    def _handle_screenshot(self, image_data: str, source: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle screenshot data by saving it to the screenshots directory.
        
        Args:
            image_data: Base64-encoded image data
            source: Source of the screenshot (e.g., "browser", "computer")
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
    
    def _handle_tool_output(self, output: Any, tool_name: str, context: Optional[Dict[str, Any]] = None) -> None:
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
    
    def add_message(self, role: str, content: Any) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message (user or assistant)
            content: Content of the message (string or list of content blocks)
        """
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
    
    def log_tool_usage(self, tool_name: str, args: Dict[str, Any], result: Any, 
                      duration: float, success: bool, error: Optional[str] = None) -> None:
        """
        Log tool usage for analysis.
        
        Args:
            tool_name: Name of the tool
            args: Arguments passed to the tool
            result: Result of the tool call
            duration: Duration of the tool call in seconds
            success: Whether the tool call was successful
            error: Error message if the tool call failed
        """
        usage_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "tool": tool_name,
            "args": args,
            "success": success,
            "duration": duration
        }
        
        if error:
            usage_data["error"] = error
            self.stats["errors"]["tool"] += 1
        
        # Add to tool usage history
        self.tool_usage_history.append(usage_data)
        
        # Update statistics
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
        
        self.stats["tool_usage"][tool_name]["total_duration"] += duration
        
        # Log the event
        if success:
            logger.info(f"Tool {tool_name} succeeded in {duration:.2f}s")
        else:
            logger.warning(f"Tool {tool_name} failed in {duration:.2f}s: {error}")
        
        # Save tool usage to file
        if self.session_dirs and "tool_output" in self.session_dirs:
            try:
                usage_file = os.path.join(self.session_dirs["tool_output"], "tool_usage.json")
                with open(usage_file, "w") as f:
                    json.dump(self.tool_usage_history, f, indent=2)
                logger.debug("Saved tool usage history")
            except Exception as e:
                logger.error(f"Error saving tool usage history: {e}")
    
    def get_api_tools(self) -> List[Dict[str, Any]]:
        """
        Get the tools in the format expected by the Anthropic API.
        
        Returns:
            List of tool definitions
        """
        return self.tools["api_tools"]
    
    def run(self, user_input: str) -> Tuple[str, List[Dict[str, Any]]]:
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
        
        # Initialize our custom Anthropic client
        try:
            client = SimpleAnthropicClient(api_key=self.api_key)
            logger.debug("Initialized custom Anthropic client")
        except Exception as e:
            self.stats["errors"]["api"] += 1
            logger.error(f"Failed to initialize custom Anthropic client: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Send the request with retry logic
        response = None
        request_start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"API call attempt {attempt+1}/{self.max_retries}")
                start_time = time.time()
                
                # Make the API call
                response = client.create_message(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=self.get_api_tools(),
                    max_tokens=4096,
                    beta=self.beta_flag
                )
                
                elapsed = time.time() - start_time
                self.stats["total_api_time"] += elapsed
                logger.info(f"Received response from Claude API in {elapsed:.2f} seconds")
                break
            except Exception as e:
                self.stats["errors"]["api"] += 1
                logger.error(f"API call failed (attempt {attempt+1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    retry_time = self.retry_delay * (attempt + 1)
                    logger.info(f"Retrying in {retry_time} seconds...")
                    time.sleep(retry_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    logger.error(traceback.format_exc())
                    raise
        
        total_request_time = time.time() - request_start_time
        
        if not response:
            logger.error("No response received from API")
            raise Exception("Failed to get response from Claude API")
        
        # Process the response
        try:
            # Extract assistant message from content blocks
            assistant_message = ""
            tool_calls = []
            
            # Process the response content blocks
            for content_block in response.content:
                if content_block.type == "text":
                    assistant_message = content_block.text
                elif content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_args = content_block.input
                    tool_id = content_block.id
                    
                    logger.info(f"Processing tool call: {tool_name} (ID: {tool_id})")
                    logger.debug(f"Tool arguments: {tool_args}")
                    
                    # Find the tool
                    tool = self.tools["instances"].get(tool_name)
                    if not tool:
                        logger.warning(f"Unknown tool: {tool_name}")
                        continue
                    
                    # Execute the tool
                    start_time = time.time()
                    success = True
                    error_msg = None
                    
                    try:
                        result = tool.run(**tool_args)
                    except Exception as e:
                        success = False
                        error_msg = str(e)
                        result = {"success": False, "message": str(e)}
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        logger.error(traceback.format_exc())
                    
                    duration = time.time() - start_time
                    
                    # Log tool usage
                    self.log_tool_usage(
                        tool_name=tool_name,
                        args=tool_args,
                        result=result,
                        duration=duration,
                        success=success,
                        error=error_msg
                    )
                    
                    # Add to tool calls
                    tool_calls.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                        "tool_use_id": tool_id
                    })
                    
                    logger.info(f"Tool {tool_name} executed in {duration:.2f}s (success={success})")
                    
                    # Add tool result to conversation for Claude to see
                    tool_results = [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    }]
                    
                    self.add_message("user", tool_results)
            
            # Update token stats if available
            if hasattr(response, 'usage'):
                input_tokens = getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'output_tokens', 0)
                self.stats["total_tokens"] += input_tokens + output_tokens
                logger.debug(f"Total tokens: {input_tokens + output_tokens}")
            
            # Log response time
            logger.info(f"Total request+processing time: {total_request_time:.2f}s")
        except Exception as e:
            self.stats["errors"]["other"] += 1
            logger.error(f"Failed to process response: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Add assistant message to conversation history
        self.add_message("assistant", assistant_message)
        
        # Save stats
        self._save_stats()
        
        # Return assistant message and tool calls
        return assistant_message, tool_calls
    
    def _save_stats(self) -> None:
        """Save the agent stats to a file."""
        if not self.session_dirs or "log" not in self.session_dirs:
            return
        
        try:
            stats_file = os.path.join(self.session_dirs["log"], "agent_stats.json")
            with open(stats_file, "w") as f:
                json.dump(self.stats, f, indent=2)
            logger.debug("Saved agent stats")
        except Exception as e:
            logger.error(f"Error saving agent stats: {e}")
            logger.error(traceback.format_exc())