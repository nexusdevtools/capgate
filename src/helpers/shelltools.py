# This file is part of CapGate.
# CapGate is a modular network security framework designed for pentesting and network analysis.

import os
import shlex
import subprocess
from typing import Optional

from core.logger import logger # Assuming logger is accessible

def is_root() -> bool:
    """Checks if the current user is root."""
    return os.geteuid() == 0

def run_command(
    command: str,
    require_root: bool = False,
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = None  # Added timeout parameter
) -> str:
    """
    Runs a shell command and returns output (stdout).

    Args:
        command (str): The shell command to run.
        require_root (bool): Automatically prepends sudo if not root and not already sudo.
        capture_output (bool): Whether to capture stdout.
        check (bool): Whether to raise CalledProcessError on non-zero exit.
        timeout (Optional[int]): Timeout in seconds for the command.

    Returns:
        str: The stdout from the command, or "" on failure if check=False.
    """
    if require_root and not is_root():
        if not command.strip().startswith("sudo "):
            command = f"sudo {command}"

    logger.debug(f"Executing shell command: {command}")
    try:
        # Use shlex.split for better handling of command arguments
        cmd_parts = shlex.split(command)
        result = subprocess.run(
            cmd_parts,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout # Pass timeout here
        )
        stdout = result.stdout.strip() if result.stdout and capture_output else ""
        stderr = result.stderr.strip() if result.stderr and capture_output else ""

        if stdout:
            logger.debug(f"Command '{cmd_parts[0]}' STDOUT: {stdout}")
        if stderr: # Log stderr even on success, as some tools output info here
            logger.debug(f"Command '{cmd_parts[0]}' STDERR: {stderr}")
        
        return stdout

    except subprocess.CalledProcessError as e:
        stderr_info = e.stderr.strip() if e.stderr and capture_output else str(e)
        logger.error(f"Command '{shlex.join(e.cmd) if isinstance(e.cmd, list) else e.cmd}' failed with exit code {e.returncode}.")
        logger.error(f"Error: {stderr_info}")
        if check: # Re-raise if check is True, otherwise it's caught by the design
            raise 
        return "" # Return empty string if check is False and error occurred
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after {timeout} seconds.")
        if check:
            raise
        return ""
    except FileNotFoundError:
        logger.error(f"Command not found: {shlex.split(command)[0]}. Ensure it's installed and in PATH.")
        if check:
            raise
        return ""
    except Exception as e: # Catch other potential exceptions
        logger.exception(f"An unexpected error occurred while running command: {command}. Error: {e}")
        if check:
            raise
        return ""

def run_command_no_check(command: str, require_root: bool = False, capture_output: bool = True, timeout: Optional[int] = None) -> str:
    """
    Runs a shell command without checking the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=False, timeout=timeout)

# run_command_with_timeout and run_command_with_timeout_no_check can now directly use the timeout parameter in run_command/run_command_no_check
# For simplicity, they can be aliases or you can call run_command with the timeout directly where needed.
# If you want to keep them as distinct functions for clarity:

def run_command_with_timeout(command: str, timeout: int, require_root: bool = False, capture_output: bool = True) -> str:
    """
    Runs a shell command with a timeout and checks the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=True, timeout=timeout)

def run_command_with_timeout_no_check(command: str, timeout: int, require_root: bool = False, capture_output: bool = True) -> str:
    """
    Runs a shell command with a timeout without checking the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=False, timeout=timeout)


def run_command_with_sudo(command: str, capture_output: bool = True, check: bool = True, timeout: Optional[int] = None) -> str:
    """
    Runs a shell command with sudo.
    """
    return run_command(command, require_root=True, capture_output=capture_output, check=check, timeout=timeout)