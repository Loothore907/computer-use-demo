"""
Streamlit app for the computer use demo.
"""
import os
import logging
from typing import List, Dict, Any

import streamlit as st

from loop import AgentLoop

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
            st.session_state.agent = AgentLoop(
                api_key=api_key,
                model=model,
                beta_flag=beta_flag
            )
            logger.info(f"Initialized agent with model={model}")
    
    # Initialize processing state flag
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False


def handle_tool_response(tool_calls):
    """
    Process tool calls and add relevant messages to the UI.
    
    Args:
        tool_calls: List of tool calls from the agent
    """
    for call in tool_calls:
        tool_name = call["name"]
        args = call["args"]
        result = call["result"]
        
        # Check if this tool call had an error
        if isinstance(result, dict) and (not result.get("success", True) or "error" in result):
            error_msg = result.get("message", "Unknown error")
            
            # Add error message to history for Claude to see
            st.session_state.messages.append({
                "role": "system",
                "content": f"❌ Error using tool {tool_name}: {error_msg}"
            })
            
        # Handle screenshots from computer or browser tool
        if (tool_name in ["computer", "browser"] and 
            ((args.get("command") == "screenshot") or (args.get("action") == "screenshot"))):
            if result.get("success") and "screenshot" in result:
                screenshot_data = result.get("screenshot", "")
                if screenshot_data and isinstance(screenshot_data, str) and screenshot_data.startswith("data:image/png;base64,"):
                    # Add system message with screenshot
                    st.session_state.messages.append({
                        "role": "system",
                        "content": "Screenshot captured",
                        "screenshot": screenshot_data
                    })
        else:
            # Add system message for other tool calls
            st.session_state.messages.append({
                "role": "system",
                "content": f"Tool: {tool_name}\nArgs: {args}\nResult: {result}"
            })


def process_message(user_input: str):
    """
    Process user input and get response from agent.
    
    Args:
        user_input: User input to process
    """
    if not st.session_state.agent:
        st.session_state.messages.append({
            "role": "system",
            "content": "Error: No API key found. Please set the ANTHROPIC_API_KEY environment variable."
        })
        return
    
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Set processing state
    st.session_state.is_processing = True
    
    try:
        # Run the agent
        response, tool_calls = st.session_state.agent.run(user_input)
        
        # Process tool calls
        handle_tool_response(tool_calls)
        
        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "tool_calls": tool_calls if tool_calls else None
        })
    except Exception as e:
        # Handle errors
        logger.error(f"Error processing message: {e}", exc_info=True)
        
        # Add error to message history
        st.session_state.messages.append({
            "role": "system",
            "content": f"An error occurred: {str(e)}"
        })
    finally:
        # Reset processing state
        st.session_state.is_processing = False


def display_messages():
    """
    Display all messages in the chat.
    """
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
                    tool_names = [call["name"] for call in message["tool_calls"]]
                    st.caption(f"Used tools: {', '.join(tool_names)}")
        elif role == "system":
            with st.chat_message("system", avatar="🔧"):
                st.write(content)
                
                # Display screenshot if available
                if "screenshot" in message:
                    try:
                        screenshot_data = message["screenshot"]
                        st.image(screenshot_data, caption="Screenshot", use_column_width=True)
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
        
        model = st.selectbox(
            "Claude Model",
            ["claude-3-5-sonnet-20241022", "claude-3-7-sonnet-20250219"],
            index=0,
            help="Select the Claude model to use"
        )
        
        if st.button("Apply Settings"):
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
                st.session_state.agent = AgentLoop(
                    api_key=api_key,
                    model=model,
                    beta_flag="computer-use-2024-10-22"
                )
                st.success("Settings applied!")
            else:
                st.error("Please enter an API key")
                
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
    
    # Main chat interface
    display_messages()
    
    # Chat input - disable while processing
    if user_input := st.chat_input(
        "Ask Claude to control your computer...", 
        disabled=st.session_state.is_processing
    ):
        process_message(user_input)
        st.rerun()
        
    # Show waiting indicator if processing a message
    if st.session_state.is_processing:
        with st.chat_message("assistant"):
            st.write("⏳ Processing your request...")


if __name__ == "__main__":
    main()