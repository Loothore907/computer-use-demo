"""
Shell command execution utilities.

This module provides utilities for running shell commands in an async context.
"""
import asyncio
import logging
import shlex
from typing import Tuple

logger = logging.getLogger("tools.run")

async def run(command: str) -> Tuple[int, str, str]:
    """
    Run a shell command and return the exit code, stdout, and stderr.
    
    Args:
        command: Shell command to run
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    logger.debug(f"Running command: {command}")
    
    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        # Get return code
        return_code = process.returncode
        
        # Decode output
        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""
        
        # Log result
        if return_code == 0:
            logger.debug(f"Command completed successfully: {command}")
        else:
            logger.warning(f"Command failed with return code {return_code}: {command}")
            logger.warning(f"stderr: {stderr_str}")
        
        return return_code, stdout_str, stderr_str
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        return 1, "", str(e)


async def run_with_timeout(command: str, timeout: float) -> Tuple[int, str, str]:
    """
    Run a shell command with a timeout and return the exit code, stdout, and stderr.
    
    Args:
        command: Shell command to run
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        return await asyncio.wait_for(run(command), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Command timed out after {timeout} seconds: {command}")
        return 1, "", f"Command timed out after {timeout} seconds: {command}"


async def run_bash(command: str) -> Tuple[int, str, str]:
    """
    Run a command in a bash shell and return the exit code, stdout, and stderr.
    
    Args:
        command: Shell command to run
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    bash_command = f"bash -c {shlex.quote(command)}"
    return await run(bash_command)