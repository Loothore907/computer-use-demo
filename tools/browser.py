"""
Browser tool for computer use demo.
"""
import json
import logging
import time
import base64
import os
import traceback
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from PIL import Image

from .base import Tool

logger = logging.getLogger("tools.browser")

class BrowserTool(Tool):
    """
    Tool for interacting with a web browser using Selenium.
    
    This tool provides:
    - Screenshot of the browser
    - Navigation to URLs
    - DOM interaction (click, type, etc.)
    - Extract information from the page
    """
    
    def __init__(self, screenshot_callback: Optional[Callable] = None):
        """
        Initialize the browser tool.
        
        Args:
            screenshot_callback: Optional callback for handling screenshots
        """
        super().__init__(
            name="browser",
            description="Tool for interacting with a web browser",
            callback=screenshot_callback
        )
        self.screenshot_callback = screenshot_callback
        self.driver = None
        self._initialize_browser()
        logger.debug("BrowserTool initialized")
    
    def _initialize_browser(self):
        """Initialize the Selenium WebDriver."""
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,1024")
            
            # Check for environment variables that might be set in Docker
            chrome_binary = os.environ.get("CHROME_BIN")
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")
            
            # Try to use system chromedriver if available, otherwise use webdriver-manager
            chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
            if chromedriver_path and os.path.exists(chromedriver_path):
                logger.info(f"Using system ChromeDriver at: {chromedriver_path}")
                service = Service(executable_path=chromedriver_path)
            else:
                logger.info("Using ChromeDriverManager to download driver")
                service = Service(ChromeDriverManager().install())
            
            # Create the WebDriver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self.driver is None:
            logger.info("Browser not initialized, initializing now")
            self._initialize_browser()
    
    def _run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Run a browser command.
        
        Args:
            *args: Positional arguments (first arg may be command name)
            **kwargs: Keyword arguments including command information
        
        Returns:
            Result of the command
        """
        logger.info(f"Running browser command with args: {args}, kwargs: {kwargs}")
        
        # Ensure we have a browser instance
        self._ensure_browser()
        
        # Extract command from inputs
        command = None
        url = None
        selector = None
        text = None
        timeout = 10  # Default timeout in seconds
        
        # Extract command from positional args
        if args and isinstance(args[0], str):
            command = args[0]
        
        # Extract parameters from kwargs
        if not command and "command" in kwargs:
            command = kwargs.get("command")
        
        # If command is in kwargs directly
        if isinstance(kwargs, dict):
            url = kwargs.get("url", "")
            selector = kwargs.get("selector", "")
            text = kwargs.get("text", "")
            timeout = kwargs.get("timeout", timeout)
        
        logger.info(f"Processed command: {command}, url: {url}, selector: {selector}")
        
        # Execute the appropriate command
        try:
            if command == "navigate":
                return self._navigate(url)
            elif command == "screenshot":
                return self._take_screenshot()
            elif command == "click":
                return self._click(selector, timeout)
            elif command == "type":
                return self._type(selector, text, timeout)
            elif command == "extract":
                return self._extract(selector, timeout)
            else:
                error_msg = f"Unknown browser command: {command}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Error executing browser command '{command}': {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def _navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            
        Returns:
            Dictionary with the navigation result
        """
        logger.info(f"Navigating to URL: {url}")
        
        if not url:
            return {"success": False, "message": "No URL provided"}
        
        try:
            # Navigate to the URL
            self.driver.get(url)
            
            # Get page info
            title = self.driver.title
            current_url = self.driver.current_url
            
            result = {
                "success": True,
                "url": current_url,
                "title": title
            }
            
            logger.info(f"Successfully navigated to {url}, title: {title}")
            return result
        except TimeoutException:
            error_msg = f"Timeout navigating to {url}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except WebDriverException as e:
            error_msg = f"Error navigating to {url}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error navigating to {url}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def _take_screenshot(self) -> Dict[str, Any]:
        """
        Take a screenshot of the current browser window.
        
        Returns:
            Dictionary with the screenshot data
        """
        logger.info("Taking browser screenshot")
        
        try:
            # Take screenshot
            screenshot = self.driver.get_screenshot_as_png()
            
            # Convert to base64 for display
            img = Image.open(BytesIO(screenshot))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            screenshot_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Format as data URL
            screenshot_data = f"data:image/png;base64,{screenshot_base64}"
            
            # Record timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # If we have a callback for screenshots, use it
            filepath = ""
            if self.screenshot_callback:
                context = {"timestamp": timestamp, "source": "browser"}
                filepath = self.screenshot_callback(screenshot_data, "browser", context)
            
            result = {
                "success": True,
                "screenshot": screenshot_data,
                "timestamp": timestamp,
                "filepath": filepath,
                "title": self.driver.title,
                "url": self.driver.current_url
            }
            
            logger.info("Browser screenshot taken successfully")
            return result
        except Exception as e:
            error_msg = f"Error taking browser screenshot: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def _click(self, selector: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Click on an element in the browser.
        
        Args:
            selector: The CSS selector of the element to click
            timeout: Seconds to wait for element to be clickable
            
        Returns:
            Dictionary with the click result
        """
        logger.info(f"Clicking on element: {selector}")
        
        if not selector:
            return {"success": False, "message": "No selector provided"}
        
        try:
            # Wait for element to be clickable
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            
            # Click the element
            element.click()
            
            result = {
                "success": True,
                "selector": selector
            }
            
            logger.info(f"Successfully clicked on {selector}")
            return result
        except TimeoutException:
            error_msg = f"Timeout waiting for element {selector} to be clickable"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except NoSuchElementException:
            error_msg = f"Element {selector} not found"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Error clicking on {selector}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def _type(self, selector: str, text: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Type text into an input element.
        
        Args:
            selector: The CSS selector of the input element
            text: The text to type
            timeout: Seconds to wait for element to be present
            
        Returns:
            Dictionary with the typing result
        """
        logger.info(f"Typing text into element: {selector}")
        
        if not selector:
            return {"success": False, "message": "No selector provided"}
        
        if not text:
            return {"success": False, "message": "No text provided"}
        
        try:
            # Wait for element to be present
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            # Clear existing text
            element.clear()
            
            # Type the text
            element.send_keys(text)
            
            result = {
                "success": True,
                "selector": selector,
                "text": text
            }
            
            logger.info(f"Successfully typed text into {selector}")
            return result
        except TimeoutException:
            error_msg = f"Timeout waiting for element {selector}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except NoSuchElementException:
            error_msg = f"Element {selector} not found"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Error typing into {selector}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def _extract(self, selector: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Extract information from an element.
        
        Args:
            selector: The CSS selector of the element to extract information from
            timeout: Seconds to wait for element to be present
            
        Returns:
            Dictionary with the extracted information
        """
        logger.info(f"Extracting information from element: {selector}")
        
        if not selector:
            return {"success": False, "message": "No selector provided"}
        
        try:
            # Wait for element to be present
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            # Extract information
            text = element.text
            html = element.get_attribute("outerHTML")
            
            result = {
                "success": True,
                "selector": selector,
                "text": text,
                "html": html,
                "attributes": {
                    "id": element.get_attribute("id"),
                    "class": element.get_attribute("class"),
                    "href": element.get_attribute("href")
                }
            }
            
            logger.info(f"Successfully extracted information from {selector}")
            return result
        except TimeoutException:
            error_msg = f"Timeout waiting for element {selector}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except NoSuchElementException:
            error_msg = f"Element {selector} not found"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Error extracting information from {selector}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "message": error_msg}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary for the Anthropic API.
        
        Returns:
            Dictionary representation of the tool
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["navigate", "screenshot", "click", "type", "extract"],
                        "description": "The browser command to run"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL for the navigate command"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the click, type, and extract commands"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text for the type command"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds for operations that wait for elements",
                        "default": 10
                    }
                },
                "required": ["command"]
            }
        }
    
    def __del__(self):
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except:
                pass 