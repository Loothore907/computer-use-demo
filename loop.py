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
from typing import Any, Dict, List, Optional
import inspect

from tools import ComputerTool, BashTool, EditTool, BrowserTool, SearchTool, DockerTool

# Configure logging
logger = logging.getLogger("agent-loop")

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
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message (user or assistant)
            content: Content of the message
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
    
    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Run the agent loop with the given user input.
        
        Args:
            user_input: User input
            
        Returns:
            Tuple of (assistant_message, tool_calls)
        """
        # Custom Anthropic client wrapper to avoid proxy issues
        # We'll directly use the requests library to make API calls
        import requests
        import json
        
        class SimpleAnthropicClient:
            """
            Simple client for Anthropic API that avoids proxy issues
            """
            def __init__(self, api_key):
                self.api_key = api_key
                self.base_url = "https://api.anthropic.com"
                self.headers = {
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                    "x-api-key": api_key
                }
                # Create beta namespace
                self.beta = SimpleAnthropicBeta(self)
                
            def messages_create(self, **kwargs):
                """Call the messages API"""
                url = f"{self.base_url}/v1/messages"
                logger.info(f"Making API request to: {url}")
                response = requests.post(url, headers=self.headers, json=kwargs)
                
                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code} - {response.text}")
                
                # Convert to SimpleResponse object
                data = response.json()
                return SimpleResponse(data)
        
        class SimpleAnthropicBeta:
            """Beta namespace for SimpleAnthropicClient"""
            def __init__(self, client):
                self.client = client
                # Create messages namespace with create method
                self.messages = SimpleMessages(self.client)
                
            def messages_create(self, **kwargs):
                """Call the beta messages API - legacy method for backward compatibility"""
                # Add beta flags to headers
                if "betas" in kwargs:
                    self.client.headers["anthropic-beta"] = ",".join(kwargs.pop("betas"))
                
                return self.client.messages_create(**kwargs)
        
        class SimpleMessages:
            """Messages namespace for SimpleAnthropicClient"""
            def __init__(self, client):
                self.client = client
                
            def create(self, **kwargs):
                """Create a message - matches the structure of the official SDK"""
                # Add beta flags to headers if present
                if "betas" in kwargs:
                    self.client.headers["anthropic-beta"] = ",".join(kwargs.pop("betas"))
                    
                # Call the client's messages_create method
                return self.client.messages_create(**kwargs)
        
        class SimpleResponse:
            """Wrapper for API response to mimic Anthropic client response"""
            def __init__(self, data):
                self.id = data.get("id")
                self.model = data.get("model")
                self.usage = SimpleUsage(data.get("usage", {}))
                self.content = data.get("content", [])
                # Extract tool calls if present
                self.tool_calls = []
                for block in self.content:
                    if block.get("type") == "tool_use":
                        self.tool_calls.append(SimpleToolCall(block))
                        
        class SimpleUsage:
            """Usage information wrapper"""
            def __init__(self, data):
                self.input_tokens = data.get("input_tokens", 0)
                self.output_tokens = data.get("output_tokens", 0)
                
        class SimpleToolCall:
            """Tool call wrapper"""
            def __init__(self, data):
                self.id = data.get("id")
                self.name = data.get("name")
                self.input = data.get("input", {})
                self.type = data.get("type")
                
        # Add user message to conversation history
        self.add_message("user", user_input)
        logger.info("Processing user input")
        
        # Initialize our simplified Anthropic client
        logger.info("Initializing simple Anthropic client")
        try:
            client = SimpleAnthropicClient(api_key=self.api_key)
            logger.debug("Simple Anthropic client initialized successfully")
        except Exception as e:
            self.stats["errors"]["api"] += 1
            logger.error(f"Failed to initialize simple Anthropic client: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Create the request parameters
        request = {
            "model": self.model,
            "messages": self.conversation_history,
            "tools": self.get_api_tools(),
            "max_tokens": 4096,
            "betas": [self.beta_flag]
        }
        
        # Log the request for debugging
        logger.info(f"Sending request to Claude API with model={self.model}")
        logger.debug(f"Request contains {len(self.conversation_history)} messages and {len(self.get_api_tools())} tools")
        
        # Update request stats
        self.stats["total_requests"] += 1
        
        # Send the request
        response = None
        request_start_time = time.time()
        for attempt in range(self.max_retries):
            try:
                logger.info(f"API call attempt {attempt+1}/{self.max_retries}")
                start_time = time.time()
                
                # Use the .beta namespace for the latest API pattern
                response = client.beta.messages.create(**request)
                
                elapsed = time.time() - start_time
                self.stats["total_api_time"] += elapsed
                logger.info(f"Received response from Claude API in {elapsed:.2f} seconds")
                break
            except Exception as e:
                self.stats["errors"]["api"] += 1
                logger.error(f"API call failed (attempt {attempt+1}/{self.max_retries}): {e}")
                
                # Try alternative approach without beta namespace if that failed
                if "beta" in str(e) and attempt == 0:
                    logger.info("Trying alternative approach without beta namespace")
                    try:
                        alt_request = request.copy()
                        # Remove betas parameter for compatibility
                        if "betas" in alt_request:
                            del alt_request["betas"]
                        
                        response = client.messages.create(**alt_request)
                        elapsed = time.time() - start_time
                        self.stats["total_api_time"] += elapsed
                        logger.info(f"Alternative API call succeeded in {elapsed:.2f} seconds")
                        break
                    except Exception as alt_e:
                        logger.error(f"Alternative approach also failed: {alt_e}")
                
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
            # Extract message text - handle both newer and older response formats
            assistant_message = ""
            if hasattr(response, 'content') and isinstance(response.content, list):
                # Newer format with content blocks
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'text':
                        assistant_message = block.text
                        break
            elif hasattr(response, 'content') and isinstance(response.content, str):
                # Older format with content as string
                assistant_message = response.content
            else:
                # Fallback to content[0].text if available
                try:
                    assistant_message = response.content[0].text
                except (AttributeError, IndexError, TypeError):
                    logger.warning("Could not extract assistant message using standard methods")
                    assistant_message = str(response)
            
            logger.info("Successfully extracted assistant message from response")
            logger.debug(f"Assistant message length: {len(assistant_message)} characters")
            
            # Process tool calls - handle both newer and older formats
            tool_calls = []
            
            # Try newer format first (tool_use blocks)
            if hasattr(response, 'content') and isinstance(response.content, list):
                found_tool_uses = False
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'tool_use':
                        found_tool_uses = True
                        tool_name = block.name
                        tool_args = block.input
                        tool_id = block.id
                        
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
                            result = tool.run(tool_args)
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
                        
                        # Format in the new expected format
                        tool_calls.append({
                            "name": tool_name,
                            "args": tool_args,
                            "result": result,
                            "tool_use_id": tool_id
                        })
                        
                        logger.info(f"Tool {tool_name} executed in {duration:.2f}s (success={success})")
                
                # If we found and processed tool_use blocks, add them to the conversation
                if found_tool_uses and tool_calls:
                    # Format the tool results as expected by the API
                    tool_results = []
                    for call in tool_calls:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": call["tool_use_id"],
                            "content": call["result"]
                        })
                    
                    # Add tool results to conversation history
                    self.add_message("user", tool_results)
            
            # Fall back to older format if no tool_use blocks found
            elif hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"Using legacy format: Found {len(response.tool_calls)} tool calls in response")
                
                for call in response.tool_calls:
                    tool_name = call.name
                    tool_args = call.input
                    
                    logger.info(f"Processing tool call: {tool_name}")
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
                        result = tool.run(tool_args)
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
                        "result": result
                    })
                    
                    logger.info(f"Tool {tool_name} executed in {duration:.2f}s (success={success})")
            else:
                logger.info("No tool calls found in response")
            
            # Update token stats
            if hasattr(response, 'usage') and response.usage:
                if hasattr(response.usage, 'input_tokens'):
                    logger.debug(f"Input tokens: {response.usage.input_tokens}")
                    self.stats["total_tokens"] += response.usage.input_tokens
                if hasattr(response.usage, 'output_tokens'):
                    logger.debug(f"Output tokens: {response.usage.output_tokens}")
                    self.stats["total_tokens"] += response.usage.output_tokens
            
            # Log response time
            logger.info(f"Total request+processing time: {total_request_time:.2f}s")
        except Exception as e:
            self.stats["errors"]["other"] += 1
            logger.error(f"Failed to extract assistant message from response: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # Add assistant message to conversation history
        self.add_message("assistant", assistant_message)
        
        # Save stats
        self._save_stats()
        
        # Return assistant message and tool calls for Streamlit compatibility
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