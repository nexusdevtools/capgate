# src/helpers/shelltools.py
# This file is part of CapGate.
# CapGate is a modular network security framework designed for pentesting and network analysis.

import os
import shlex
import subprocess
from typing import Optional, Union, List # Import Union and List

from base.logger import logger # Assuming logger is accessible

def is_root() -> bool:
    """Checks if the current user is root."""
    return os.geteuid() == 0

def run_command(
    command: Union[str, List[str]], # <--- CRITICAL CHANGE: Accept both string or list of strings
    require_root: bool = False,
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = None
) -> str:
    """
    Runs a shell command and returns output (stdout).

    Args:
        command (Union[str, List[str]]): The shell command to run, either as a single string
                                          or as a list of strings (arguments).
        require_root (bool): Automatically prepends sudo if not root and not already sudo.
        capture_output (bool): Whether to capture stdout.
        check (bool): Whether to raise CalledProcessError on non-zero exit.
        timeout (Optional[int]): Timeout in seconds for the command.

    Returns:
        str: The stdout from the command, or "" on failure if check=False.
    """
    cmd_parts: List[str] # Declare type for cmd_parts

    if isinstance(command, str):
        # Use shlex.split for robust parsing of string commands
        cmd_parts = shlex.split(command)
    else:
        # If command is already a list, use it directly
        cmd_parts = command

    # Apply sudo if required and not already root
    if require_root and not is_root():
        if cmd_parts[0] != "sudo": # Avoid double-sudo
            cmd_parts.insert(0, "sudo")

    logger.debug(f"Executing shell command: {shlex.join(cmd_parts)}") # Use shlex.join for logging

    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout
        )
        stdout = result.stdout.strip() if result.stdout and capture_output else ""
        stderr = result.stderr.strip() if result.stderr and capture_output else ""

        if stdout:
            logger.debug(f"Command '{cmd_parts[0]}' STDOUT: {stdout}")
        if stderr:
            logger.debug(f"Command '{cmd_parts[0]}' STDERR: {stderr}")
        
        return stdout

    except subprocess.CalledProcessError as e:
        stderr_info = e.stderr.strip() if e.stderr and capture_output else str(e)
        logger.error(f"Command '{shlex.join(e.cmd)}' failed with exit code {e.returncode}.")
        logger.error(f"Error: {stderr_info}")
        if check:
            raise 
        return ""
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{shlex.join(cmd_parts)}' timed out after {timeout} seconds.")
        if check:
            raise
        return ""
    except FileNotFoundError:
        logger.error(f"Command not found: '{cmd_parts[0]}'. Ensure it's installed and in PATH.")
        if check:
            raise
        return ""
    except Exception as e:
        logger.exception(f"An unexpected error occurred while running command: '{shlex.join(cmd_parts)}'. Error: {e}")
        if check:
            raise
        return ""

def run_command_no_check(command: Union[str, List[str]], require_root: bool = False, capture_output: bool = True, timeout: Optional[int] = None) -> str:
    """
    Runs a shell command without checking the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=False, timeout=timeout)

def run_command_with_timeout(command: Union[str, List[str]], timeout: int, require_root: bool = False, capture_output: bool = True) -> str:
    """
    Runs a shell command with a timeout and checks the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=True, timeout=timeout)

def run_command_with_timeout_no_check(command: Union[str, List[str]], timeout: int, require_root: bool = False, capture_output: bool = True) -> str:
    """
    Runs a shell command with a timeout without checking the exit code.
    """
    return run_command(command, require_root=require_root, capture_output=capture_output, check=False, timeout=timeout)

def run_command_with_sudo(command: Union[str, List[str]], capture_output: bool = True, check: bool = True, timeout: Optional[int] = None) -> str:
    """
    Runs a shell command with sudo.
    """
    return run_command(command, require_root=True, capture_output=capture_output, check=check, timeout=timeout)