"""
Streamlit app for the computer use demo.
"""
import asyncio
import os
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st

from loop import AgentLoop
from tools import ToolVersion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("streamlit_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("streamlit-app")

def init_session_state():
    """
    Initialize session state variables.
    """
    # Initialize messages history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Initialize session directories
    if "session_dirs" not in st.session_state:
        # Create session directories for storing screenshots, tool outputs, and chat history
        temp_dir = tempfile.mkdtemp(prefix="claude_demo_")
        
        screenshot_dir = os.path.join(temp_dir, "screenshots")
        tool_output_dir = os.path.join(temp_dir, "tool_outputs")
        chat_dir = os.path.join(temp_dir, "chat")
        log_dir = os.path.join(temp_dir, "logs")
        
        # Create the directories
        os.makedirs(screenshot_dir, exist_ok=True)
        os.makedirs(tool_output_dir, exist_ok=True)
        os.makedirs(chat_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        
        st.session_state.session_dirs = {
            "session_id": Path(temp_dir).name,
            "root": temp_dir,
            "screenshot": screenshot_dir,
            "tool_output": tool_output_dir,
            "chat": chat_dir,
            "log": log_dir
        }
        
        logger.info(f"Created session directories: {st.session_state.session_dirs}")
        
    # Initialize agent
    if "agent" not in st.session_state:
        # Get configuration from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("MODEL", "claude-3-5-sonnet-20241022")
        beta_flag = os.environ.get("BETA_FLAG", "computer-use-2024-10-22")
        
        if not api_key:
            st.session_state.agent = None
            logger.error("No API key found in environment variables")
        else:
            # Determine tool version from beta flag
            tool_version = ToolVersion.V20241022
            if "2025-01-24" in beta_flag:
                tool_version = ToolVersion.V20250124
            
            st.session_state.agent = AgentLoop(
                api_key=api_key,
                model=model,
                beta_flag=beta_flag,
                tool_version=tool_version,
                session_dirs=st.session_state.session_dirs
            )
            logger.info(f"Initialized agent with model={model}, tool_version={tool_version}")
    
    # Initialize processing state flag
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
        
    # Initialize pending message flag
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None
        
    # Initialize total tokens sent/received
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0


def handle_tool_response(tool_calls):
    """
    Process tool calls and add relevant messages to the UI.
    
    Args:
        tool_calls: List of tool calls from the agent
    """
    for call in tool_calls:
        tool_name = call.get("name")
        args = call.get("args")
        result = call.get("result")
        
        # Skip if this is just a tool call definition without a result
        if result is None:
            continue
            
        # Check if this is a ToolResult object
        if hasattr(result, "error") and result.error:
            error_msg = result.error
            
            # Add error message to UI history
            st.session_state.messages.append({
                "role": "system",
                "content": f"❌ Error using tool {tool_name}: {error_msg}",
                "for_ui_only": True
            })
        elif hasattr(result, "base64_image") and result.base64_image:
            # Add system message with screenshot for display only in UI
            st.session_state.messages.append({
                "role": "system",
                "content": "Screenshot captured:",
                "screenshot": f"data:image/png;base64,{result.base64_image}",
                "for_ui_only": True
            })
        elif hasattr(result, "output") and result.output:
            # Add system message for tool output
            st.session_state.messages.append({
                "role": "system",
                "content": f"✅ Tool: {tool_name}\nArgs: {args}\nResult: {result.output}",
                "for_ui_only": True
            })
        else:
            # Add system message for other tool calls (UI only)
            st.session_state.messages.append({
                "role": "system",
                "content": f"ℹ️ Tool: {tool_name}\nArgs: {args}\nResult: {result}",
                "for_ui_only": True
            })


def process_message(user_input: str):
    """
    Process user input and get response from agent.
    
    Args:
        user_input: User input to process
    """
    # Clear the pending message
    st.session_state.pending_message = None
    
    if not user_input:
        return
        
    if not st.session_state.agent:
        st.session_state.messages.append({
            "role": "system",
            "content": "Error: No API key found. Please set the ANTHROPIC_API_KEY environment variable.",
            "for_ui_only": True
        })
        return
    
    # Set processing state
    st.session_state.is_processing = True
    
    try:
        # Run the agent
        response, tool_calls = st.session_state.agent.run(user_input)
        
        # Process tool calls for UI display
        handle_tool_response(tool_calls)
        
        # Add assistant response to UI history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "tool_calls": [call.get("name") for call in tool_calls if call.get("name")] if tool_calls else None
        })
        
        # Update token stats
        if st.session_state.agent and hasattr(st.session_state.agent, "stats"):
            if "total_tokens" in st.session_state.agent.stats:
                st.session_state.total_tokens = st.session_state.agent.stats["total_tokens"]
        
    except Exception as e:
        # Handle errors
        logger.error(f"Error processing message: {e}", exc_info=True)
        
        # Add error to message history (UI only)
        st.session_state.messages.append({
            "role": "system",
            "content": f"An error occurred: {str(e)}",
            "for_ui_only": True
        })
    finally:
        # Reset processing state
        st.session_state.is_processing = False


def display_messages():
    """
    Display all messages in the chat.
    """
    # Display all existing messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.chat_message("user").write(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.write(content)
                # If this message has tool calls, indicate this
                if "tool_calls" in message and message["tool_calls"]:
                    used_tools = set(message["tool_calls"])  # Use a set to deduplicate
                    st.caption(f"Used tools: {', '.join(used_tools)}")
        elif role == "system":
            with st.chat_message("system", avatar="🔧"):
                st.write(content)
                
                # Display screenshot if available
                if "screenshot" in message:
                    try:
                        screenshot_data = message["screenshot"]
                        # Set width to control screenshot size (max 600px)
                        st.image(screenshot_data, caption="Screenshot", width=600)
                    except Exception as e:
                        st.error(f"Error displaying screenshot: {str(e)}")


def main():
    """
    Main function for the Streamlit app.
    """
    # Set page config
    st.set_page_config(
        page_title="Claude Computer Use Demo",
        page_icon="🖥️",
        layout="wide",
    )
    
    # Initialize session state
    init_session_state()
    
    # Display header
    st.title("Claude Computer Use Demo")
    
    # Configuration sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input(
            "Anthropic API Key", 
            type="password", 
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            help="Enter your Anthropic API Key to enable Claude interaction"
        )
        
        # Model selection
        model_options = [
            "claude-3-5-sonnet-20241022", 
            "claude-3-7-sonnet-20250219"
        ]
        model = st.selectbox(
            "Claude Model",
            model_options,
            index=0,
            help="Select the Claude model to use"
        )
        
        # Tool version selection
        tool_version_options = {
            "October 2022 (Initial)": ToolVersion.V20241022,
            "January 2024 (Enhanced)": ToolVersion.V20250124
        }
        tool_version_display = st.selectbox(
            "Tool Version",
            options=list(tool_version_options.keys()),
            index=0,
            help="Select the tool version to use"
        )
        tool_version = tool_version_options[tool_version_display]
        
        # Beta flag selection (based on tool version)
        beta_flag = "computer-use-2024-10-22"
        if tool_version == ToolVersion.V20250124:
            beta_flag = "computer-use-2025-01-24"
        
        # Apply settings button
        if st.button("Apply Settings"):
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
                st.session_state.agent = AgentLoop(
                    api_key=api_key,
                    model=model,
                    beta_flag=beta_flag,
                    tool_version=tool_version,
                    session_dirs=st.session_state.session_dirs
                )
                st.success("Settings applied!")
            else:
                st.error("Please enter an API key")
        
        st.markdown("---")
        
        # Clear chat/history buttons
        col1, col2 = st.columns(2)
        with col1:        
            if st.button("Clear Chat"):
                # Clear UI messages
                st.session_state.messages = []
                st.rerun()
        
        with col2:
            if st.button("Clear History"):
                if st.session_state.agent:
                    # Clear conversation history and processed tool IDs
                    st.session_state.agent.clear_history()
                    st.success("Conversation history cleared!")
                    
                    # Update token count display
                    history_size = len(str(st.session_state.agent.conversation_history))
                    token_estimate = history_size // 4  # Rough estimate: 4 chars per token
                    st.info(f"New history size: ~{token_estimate:,} tokens")
                else:
                    st.error("No agent initialized")
        
        st.markdown("---")
        
        # Display token estimate
        if st.session_state.agent:
            history_size = len(str(st.session_state.agent.conversation_history))
            token_estimate = history_size // 4  # Rough estimate: 4 chars per token
            st.info(f"Estimated history size: ~{token_estimate:,} tokens")
            st.info(f"Total API tokens: ~{st.session_state.total_tokens:,}")
        
        # Display session info
        st.markdown("---")
        if "session_dirs" in st.session_state:
            st.info(f"Session ID: {st.session_state.session_dirs['session_id']}")
            
            # Show session directories (collapsible)
            with st.expander("Session Directories"):
                for key, path in st.session_state.session_dirs.items():
                    if key != "session_id":
                        st.text(f"{key}: {path}")
    
    # Main chat interface
    display_messages()
    
    # Process pending message if one exists
    if st.session_state.pending_message is not None:
        process_message(st.session_state.pending_message)
        st.rerun()
    
    # Chat input - disable while processing
    user_input = st.chat_input(
        "Ask Claude to control your computer...",
        disabled=st.session_state.is_processing
    )
    
    # If user has submitted a message
    if user_input:
        # Add user message to UI history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Set as pending message to be processed after rerun
        st.session_state.pending_message = user_input
        st.rerun()
    
    # Show waiting indicator if processing a message
    if st.session_state.is_processing:
        with st.chat_message("assistant"):
            st.write("⏳ Processing your request...")


if __name__ == "__main__":
    main()