"""
Streamlit app for the computer use demo.
"""
import os
import time
from typing import List, Dict, Any, Optional

import streamlit as st
from PIL import Image
import io
import base64

from loop import AgentLoop


def init_session_state():
    """
    Initialize session state variables.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if "agent" not in st.session_state:
        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.session_state.agent = None
        else:
            st.session_state.agent = AgentLoop(api_key=api_key)
            
    if "screenshot" not in st.session_state:
        st.session_state.screenshot = None
        
    if "is_waiting" not in st.session_state:
        st.session_state.is_waiting = False


def display_messages():
    """
    Display all messages in the chat.
    """
    # Debug all message types for troubleshooting
    print("Current message history:")
    for i, message in enumerate(st.session_state.messages):
        print(f"Message {i}: role={message.get('role')}, keys={list(message.keys())}")
        if "tool_calls" in message:
            print(f"  Tool calls: {message['tool_calls']}")
        if "tool_call" in message:
            print(f"  Tool call: {message['tool_call']}")
            
    # Display messages in the UI
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.chat_message("user").write(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.write(content)
                # Check if this assistant message contains tool calls
                if "tool_calls" in message and message["tool_calls"]:
                    tool_calls = message["tool_calls"]
                    st.write(f"*Using tool: {tool_calls[0]['name']}*")
        elif role == "tool":
            with st.chat_message("system", avatar="🔧"):
                st.write(f"Tool response: {content}")
        elif role == "system":
            with st.chat_message("system", avatar="🔧"):
                st.write(content)
                
                # Display screenshot if available
                if "screenshot" in message:
                    try:
                        screenshot_data = message["screenshot"]
                        # Debug information about the screenshot
                        st.write(f"Screenshot data length: {len(screenshot_data)} chars")
                        
                        if screenshot_data.startswith("data:image/png;base64,"):
                            st.image(screenshot_data, caption="Screenshot", use_column_width=True)
                        else:
                            st.error("Invalid screenshot data format")
                    except Exception as e:
                        import traceback
                        st.error(f"Error displaying screenshot: {str(e)}")
                        st.code(traceback.format_exc())


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
    
    # Set waiting state for UI
    st.session_state.is_waiting = True
    
    try:
        # Run the agent
        response, tool_calls = st.session_state.agent.run(user_input)
        
        # Process tool calls
        for call in tool_calls:
            tool_name = call["name"]
            args = call["args"]
            result = call["result"]
            
            # Handle screenshots from computer tool
            if tool_name == "computer" and args.get("action") == "screenshot":
                # Debug information
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"Debug - Screenshot result: Success={result.get('success')}, Data length: {len(result.get('screenshot', ''))} chars"
                })
                
                if result.get("success"):
                    # Extract and save the screenshot
                    screenshot_data = result.get("screenshot", "")
                    if screenshot_data and isinstance(screenshot_data, str) and screenshot_data.startswith("data:image/png;base64,"):
                        # Add system message with screenshot
                        st.session_state.messages.append({
                            "role": "system",
                            "content": "Screenshot captured",
                            "screenshot": screenshot_data
                        })
                    else:
                        st.session_state.messages.append({
                            "role": "system",
                            "content": f"Screenshot data invalid: {screenshot_data[:100]}..."
                        })
                else:
                    st.session_state.messages.append({
                        "role": "system",
                        "content": f"Screenshot failed: {result.get('message', 'Unknown error')}"
                    })
            else:
                # Add system message for other tool calls
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"Tool: {tool_name}\nArgs: {args}\nResult: {result}"
                })
        
        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
    except Exception as e:
        # Handle errors
        import traceback
        st.session_state.messages.append({
            "role": "system",
            "content": f"Error: {str(e)}\n{traceback.format_exc()}"
        })
    finally:
        # Reset waiting state
        st.session_state.is_waiting = False


def main():
    """
    Main function for the Streamlit app.
    """
    # Set page config
    try:
        st.set_page_config(
            page_title="Computer Use Demo",
            page_icon="🖥️",
            layout="wide",
        )
    except Exception as e:
        st.write(f"Error setting page config: {e}")
        st.write("Continuing anyway...")
    
    # Initialize session state
    init_session_state()
    
    # Display header
    st.title("Claude Computer Use Demo")
    
    # API Key input
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Anthropic API Key", 
                               type="password", 
                               value=os.environ.get("ANTHROPIC_API_KEY", ""),
                               help="Enter your Anthropic API Key to enable Claude interaction")
        
        if st.button("Apply API Key"):
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
                st.session_state.agent = AgentLoop(api_key=api_key)
                st.success("API key applied!")
            else:
                st.error("Please enter an API key")
                
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.screenshot = None
            st.rerun()
    
    # Main chat interface
    display_messages()
    
    # Chat input
    if user_input := st.chat_input("Ask Claude to control your computer...", disabled=st.session_state.is_waiting):
        process_message(user_input)
        st.rerun()
        
    # Show waiting indicator
    if st.session_state.is_waiting:
        with st.chat_message("assistant"):
            st.write("Thinking...")
            

if __name__ == "__main__":
    main()