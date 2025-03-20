"""
Main entry point for the computer use demo.
"""
import os
import sys
import argparse

def main():
    """
    Parse arguments and run the appropriate module.
    """
    parser = argparse.ArgumentParser(description="Computer Use Demo")
    parser.add_argument(
        "--api-key", 
        help="Anthropic API key (alternatively, set ANTHROPIC_API_KEY environment variable)",
        default=os.environ.get("ANTHROPIC_API_KEY")
    )
    parser.add_argument(
        "--model",
        help="Model to use for the agent",
        default="claude-3-5-sonnet-20240620",
        choices=["claude-3-5-sonnet-20240620", "claude-3-7-sonnet-20240229"]
    )
    
    args = parser.parse_args()
    
    # Set API key in environment
    if args.api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key
    
    # Fix the import to use direct import instead of package import
    from app import main as app_main
    app_main()
    
if __name__ == "__main__":
    main() 