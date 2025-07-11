# capgate/src/agent/tools.py

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
import subprocess
import os
from base.logger import logger
from pathlib import Path # Required for Path objects in type hints and comparisons

# Import directly from the single source of truth for paths
from paths import PROJECT_ROOT, NEXUSDEVTOOLS_ROOT_DIR, AGENT_KNOWLEDGE_BASE_DIR
# Import CapGate's core logger for consistent logging
from base.logger import logger as capgate_core_logger # Assuming core.logger provides a configured logger

logger = logging.getLogger(__name__) # Logger for this specific module


# --- Helper for path validation ---
def _is_path_within_allowed_dirs(abs_path: str, allowed_base_dirs: Tuple[Path, ...]) -> bool:
    """Checks if an absolute path is within any of the allowed base directories."""
    abs_path_obj = Path(abs_path).resolve() # Convert to Path object for robust comparison
    for base_dir_obj in allowed_base_dirs:
        # Check if the absolute path starts with the base directory's absolute path
        try:
            # Check if abs_path_obj is a subpath of base_dir_obj
            # This is a more robust check than commonpath or str.startswith
            abs_path_obj.relative_to(base_dir_obj)
            return True
        except ValueError: # Path is not a subpath
            continue
    return False


# --- CapGate Internal Function Example (Agent can call this) ---
class CapGateLogToolSchema(BaseModel):
    message: str = Field(..., description="The message to log.")
    level: str = Field("INFO", description="The logging level (e.g., INFO, WARNING, ERROR).")

def internal_capgate_log_event(message: str, level: str = "INFO") -> str:
    """Logs an event within the CapGate system using CapGate's core logger."""
    level_map = {
        "INFO": capgate_core_logger.info,
        "WARNING": capgate_core_logger.warning,
        "ERROR": capgate_core_logger.error,
        "DEBUG": capgate_core_logger.debug
    }
    log_func = level_map.get(level.upper(), capgate_core_logger.info)
    log_func(f"[Agent Log] {message}")
    return f"Logged event: {message} with level {level}"

capgate_log_tool = FunctionTool.from_defaults(
    fn=internal_capgate_log_event,
    description="Logs an informational, warning, or error message within the CapGate system. Useful for noting observations or actions directly into CapGate's logs."
)


# --- File Reading Tool ---
class FileReadToolSchema(BaseModel):
    file_path: str = Field(..., description="The path to the file to read, relative to the CapGate root.")

def read_capgate_file_content(file_path: str) -> str:
    """Reads the content of a specified file within the CapGate project or nexusdevtools.
    Paths are relative to the CapGate root directory."""
    if PROJECT_ROOT is None: # Safeguard, though main.py should ensure this is set.
        return "Error: PROJECT_ROOT is not set. Internal configuration error."

    abs_file_path = str(PROJECT_ROOT / file_path) # Convert Path object to string for os.path.join compatibility

    # Strict validation: Only allow reading within CapGate's main directories, nexusdevtools, or agent's knowledge base
    allowed_read_prefixes = (PROJECT_ROOT, NEXUSDEVTOOLS_ROOT_DIR, AGENT_KNOWLEDGE_BASE_DIR)
    if not _is_path_within_allowed_dirs(abs_file_path, allowed_read_prefixes):
        logger.warning("Agent attempted to read file outside allowed directories: %s", file_path)
        return f"Error: Access denied. Cannot read files outside CapGate/nexusdevtools/agent knowledge base: {file_path}"

    try:
        with open(abs_file_path, 'r') as f:
            content = f.read()
        return f"File content of {file_path}:\n```\n{content}\n```"
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

capgate_file_read_tool = FunctionTool.from_defaults(
    fn=read_capgate_file_content,
    description="Reads the content of a file within the CapGate project or nexusdevtools. Provide paths relative to the CapGate root."
)


# --- File Writing Tool (with critical human approval) ---
class FileWriteToolSchema(BaseModel):
    file_path: str = Field(..., description="The path to the file to write to, relative to the CapGate root.")
    content: str = Field(..., description="The content to write to the file.")

def write_capgate_file_content_with_approval(file_path: str, content: str) -> str:
    """Writes content to a specified file within the CapGate project.
    Requires explicit human approval for execution.
    The agent should clearly state its intent and ask the human for approval before calling this tool.
    """
    if PROJECT_ROOT is None: # Safeguard
        return "Error: PROJECT_ROOT is not set. Internal configuration error."

    abs_file_path = str(PROJECT_ROOT / file_path)

    # STRICT validation: Only allow writing within CapGate's main source directories
    # Adjust this tuple based on where your agent should be allowed to modify code.
    allowed_write_prefixes = (PROJECT_ROOT / 'src',) # Using Path objects directly for joining
    if not _is_path_within_allowed_dirs(abs_file_path, allowed_write_prefixes):
        logger.warning(f"Agent attempted to write file outside allowed directories: {file_path}")
        return f"Error: Write access denied. Cannot write to files outside CapGate's designated source directories: {file_path}"

    print(f"\n--- MCP AGENT PROPOSED FILE WRITE ---")
    print(f"Path: {file_path} (Absolute: {abs_file_path})")
    print(f"Content:\n```\n{content}\n```")
    user_approval = input("Approve this file write? (y/N): ").lower()
    if user_approval == 'y':
        try:
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
            with open(abs_file_path, 'w') as f:
                f.write(content)
            logger.info(f"Successfully wrote to {file_path} after human approval.")
            return f"Successfully wrote to {file_path} after human approval."
        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            return f"Error writing to file {file_path}: {e}"
    else:
        logger.info(f"File write to {file_path} rejected by human.")
        return f"File write to {file_path} rejected by human."

capgate_file_write_tool = FunctionTool.from_defaults(
    fn=write_capgate_file_content_with_approval,
    description="Writes content to a file within the CapGate project. Requires explicit human approval. Provide paths relative to the CapGate root."
)


# --- Git Command Tool ---
class GitCommandToolSchema(BaseModel):
    command: str = Field(..., description="The git command to execute (e.g., 'status', 'diff', 'add file.py', 'commit -m \"message\"').")
    args: Optional[List[str]] = Field(default_factory=list, description="Additional arguments for the git command.")

def execute_capgate_git_command(command: str, args: Optional[List[str]] = None) -> str:
    """Executes a git command within the CapGate repository."""
    if PROJECT_ROOT is None: # Safeguard
        return "Error: PROJECT_ROOT is not set. Internal configuration error."

    if not os.path.exists(str(PROJECT_ROOT / '.git')): # Convert Path to string
        return f"Error: '{PROJECT_ROOT}' is not a Git repository."

    full_command = ["git", command] + (args if args else [])
    print(f"\n--- MCP AGENT PROPOSED GIT COMMAND ---")
    print(f"Executing: {' '.join(full_command)} (in {PROJECT_ROOT})")

    # STRICTLY control allowed commands
    allowed_read_commands = ["status", "diff", "log", "show", "branch", "ls-files"]
    allowed_write_commands = ["add", "commit"] # These will still require user approval for changes

    if command not in allowed_read_commands + allowed_write_commands:
        logger.warning(f"Agent attempted to execute disallowed git command: {command}")
        return f"Error: Git command '{command}' is not allowed for direct execution by the agent for safety reasons. Allowed: {', '.join(allowed_read_commands + allowed_write_commands)}"

    # For 'commit', add an extra approval layer
    if command == "commit":
        commit_message = " ".join(args) if args else "Automated commit by MCP Agent"
        print(f"Proposed Git Commit Message: '{commit_message}'")
        user_approval = input("Approve this git commit? (y/N): ").lower()
        if user_approval != 'y':
            logger.info("Git commit rejected by human.")
            return "Git commit rejected by human."

    try:
        result = subprocess.run(
            full_command,
            cwd=str(PROJECT_ROOT), # Execute in the project root (convert Path to string)
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Git command '{command}' executed successfully.")
        return f"Git command output:\n```\n{result.stdout}\n```"
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing git command '{command}': {e.stderr}")
        return f"Error executing git command: {e.stderr}"
    except FileNotFoundError:
        logger.error("'git' command not found. Ensure Git is installed and in your PATH.")
        return "Error: 'git' command not found. Ensure Git is installed and in your PATH."
    except Exception as e:
        logger.error(f"An unexpected error occurred during git command '{command}': {e}")
        return f"An unexpected error occurred during git command: {e}"

capgate_git_tool = FunctionTool.from_defaults(
    fn=execute_capgate_git_command,
    description="Executes specific git commands within the CapGate repository (e.g., 'status', 'diff', 'add file.py', 'commit -m \"message\"'). Requires human approval for 'commit'."
)


# --- Define all tools available to the agent ---
ALL_CAPGATE_AGENT_TOOLS = [
    capgate_log_tool,
    capgate_file_read_tool,
    capgate_file_write_tool,
    capgate_git_tool,
    # Add more tools here as CapGate functionality is exposed
]