#!/usr/bin/env python3
"""
Script to update all tool classes to use the new pattern with callbacks.
"""
import os
import glob
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("update_tools")

def update_tool_class(file_path):
    """Update a tool class to use the new pattern with callbacks."""
    logger.info(f"Updating tool class in {file_path}")
    
    # Read the file
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if the file already uses the new pattern
    if "callback: Optional[Callable]" in content:
        logger.info(f"File {file_path} already uses the new pattern")
        return
    
    # Extract the class name
    class_name_match = re.search(r"class (\w+)\(Tool\):", content)
    if not class_name_match:
        logger.warning(f"Could not find tool class in {file_path}")
        return
    
    class_name = class_name_match.group(1)
    
    # Check if the tool handles screenshots
    is_screenshot_tool = "screenshot" in content.lower()
    callback_param = "screenshot_callback" if is_screenshot_tool else "callback"
    callback_type = f"{callback_param}: Optional[Callable] = None"
    
    # Update the imports
    if "from typing import Any, Callable, Dict, List, Optional" not in content:
        content = content.replace(
            "from typing import",
            "from typing import Any, Callable, Dict, List, Optional"
        )
    
    # Add logging import if not present
    if "import logging" not in content:
        content = content.replace(
            "import",
            "import logging\nimport"
        )
    
    # Add logger initialization if not present
    logger_line = f"logger = logging.getLogger(\"tools.{class_name.lower()}\")"
    if logger_line not in content:
        content = content.replace(
            f"class {class_name}(Tool):",
            f"{logger_line}\n\nclass {class_name}(Tool):"
        )
    
    # Update the __init__ method
    init_pattern = rf"def __init__\(self[^)]*\):"
    init_replacement = f"def __init__(self, {callback_type}):"
    content = re.sub(init_pattern, init_replacement, content)
    
    # Update the super().__init__ call
    super_pattern = r"super\(\).__init__\([^)]*\)"
    super_replacement = f"super().__init__(\n            name=\"{class_name.lower()[:-4]}\",\n            description=\"Tool for {class_name.lower()[:-4]} operations\",\n            callback={callback_param}\n        )"
    content = re.sub(super_pattern, super_replacement, content)
    
    # Add debug log after init
    if "logger.debug" not in content:
        content = content.replace(
            super_replacement + ")",
            super_replacement + ")\n        logger.debug(f\"{class_name} initialized\")"
        )
    
    # Update the execute method to _run
    if "def execute" in content:
        content = content.replace("def execute", "def _run")
    
    # Add to_dict method if not present
    if "def to_dict" not in content:
        to_dict_method = """
    def to_dict(self) -> Dict[str, Any]:
        \"\"\"
        Convert the tool to a dictionary for the Anthropic API.
        
        Returns:
            Dictionary representation of the tool
        \"\"\"
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["command1", "command2"],
                        "description": "The command to run"
                    },
                    "param1": {
                        "type": "string",
                        "description": "Parameter 1 description"
                    },
                    "param2": {
                        "type": "string",
                        "description": "Parameter 2 description"
                    }
                },
                "required": ["command"]
            }
        }"""
        
        content += to_dict_method
    
    # Write the updated content
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Updated {file_path}")

def main():
    """Main function to update all tool classes."""
    # Find all tool files
    tool_files = glob.glob("tools/*.py")
    
    # Exclude __init__.py and base.py
    tool_files = [f for f in tool_files if not f.endswith(("__init__.py", "base.py"))]
    
    logger.info(f"Found {len(tool_files)} tool files to update: {tool_files}")
    
    # Update each file
    for file_path in tool_files:
        update_tool_class(file_path)
    
    logger.info("Done updating tool classes")

if __name__ == "__main__":
    main() 