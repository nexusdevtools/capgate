# capgate/main.py

import os
import sys
# --- Ensure running as root (as per your requirement) ---
if os.geteuid() != 0:
    print("This application must be run as root. Please use sudo or run as root user.")
    sys.exit(1)

# --- Load environment variables as early as possible ---
from pathlib import Path
from dotenv import load_dotenv # pip install python-dotenv

# Determine CAPGATE_ROOT_DIR early for .env loading
CAPGATE_ROOT_DIR = Path(__file__).parent.resolve()
load_dotenv(dotenv_path=CAPGATE_ROOT_DIR / '.env')


import logging
import subprocess
import signal
import time
import atexit
import psutil # For robust process management (pip install psutil)
import socket # For port checking

import typer

# --- Set up basic logging for the entire application ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CapGateRoot") # Specific logger for the root
logger.setLevel(logging.INFO) # Set default level for the root logger

# --- Ensure CapGate's src directory is in the Python Path ---
# This allows importing modules like 'cli.capgate_cli' and 'agent.mod_coor'
# directly by their module name, without needing 'src.' prefix.
SRC_DIR = CAPGATE_ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
    logger.info(f"Added '{SRC_DIR}' to Python path.")


# --- Import CapGate Core Components ---
# These imports now rely on `src/` being in sys.path
from cli.capgate_cli import app as capgate_cli_app, set_global_runner
from runner import CapGateRunner

# Import agent specific components and sub-apps
# NOTE: ask_capgate_agent and start_capgate_agent_interactive_session are used in the 'dev' command below.
from agent.mod_coor import initialize_capgate_agent, index_capgate_knowledge, ask_capgate_agent, start_capgate_agent_interactive_session
# Import nested Typer apps from cli.capgate_cli for direct merging
from cli.commands.graph import app as graph_app
from cli.commands.debug_commands import debug_cli
from cli.capgate_cli import docs_app # Import docs_app directly


# --- Global Runner Instance ---
_runner_instance: CapGateRunner = None

# --- Global Ollama Process Management ---
# Configuration for Ollama, can be set in .env
OLLAMA_SERVER_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_SERVER_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_SERVER_URL = f"http://{OLLAMA_SERVER_HOST}:{OLLAMA_SERVER_PORT}"
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "mistral") # Default model

_ollama_process = None # To store subprocess.Popen object for ollama serve

def _is_port_in_use(port, host=OLLAMA_SERVER_HOST):
    """Checks if a given port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, int(port)))
            return False # Port is free
        except socket.error:
            return True # Port is in use

def _find_and_kill_process_on_port(port, host=OLLAMA_SERVER_HOST):
    """Attempts to find and kill a process listening on the specified port.
    This is OS-specific and might require elevated privileges itself.
    """
    logger.warning(f"Attempting to kill process on {host}:{port} if it's an orphaned Ollama instance.")
    try:
        if sys.platform.startswith('linux') or sys.platform == 'darwin': # Linux / macOS
            # Find PID using lsof (requires lsof installed and often sudo)
            cmd = f"lsof -ti TCP:{port}"
            # Check for specific host if not 127.0.0.1
            if host != "127.0.0.1":
                cmd += f" | grep '{host}'"
            
            # Use subprocess.run to avoid shell=True if possible, but lsof chaining might need it
            pids = subprocess.check_output(cmd, shell=True, text=True).strip().split('\n')
            pids = [p for p in pids if p] # Filter empty strings
            if pids:
                logger.warning(f"Found processes listening on {host}:{port}: {pids}. Attempting to kill...")
                for pid_str in pids:
                    try:
                        pid = int(pid_str)
                        process = psutil.Process(pid)
                        # More robust check: look for 'ollama' in process name or command line
                        if "ollama" in process.name().lower() or any("ollama" in arg.lower() for arg in process.cmdline()):
                            logger.info(f"Killing identified Ollama process PID {pid}...")
                            process.terminate()
                            process.wait(timeout=5)
                            if psutil.pid_exists(pid):
                                process.kill()
                                logger.warning(f"Force killed Ollama process PID {pid}.")
                        else:
                            logger.info(f"PID {pid} found on port {port} but not identified as Ollama. Skipping kill.")
                    except (psutil.NoSuchProcess, ProcessLookupError):
                        logger.debug(f"PID {pid_str} already gone.")
                    except Exception as e:
                        logger.error(f"Error killing PID {pid_str}: {e}")
                return True
            else:
                logger.debug(f"No process found listening on {host}:{port}.")
                return False
        elif sys.platform == 'win32': # Windows
            logger.warning("Automated process killing on Windows is complex and not fully implemented. Please manually check and kill any orphaned Ollama processes.")
            return False # Manual cleanup for Windows
        else:
            logger.warning("Automated process killing not supported for this OS. Please manually check and kill any orphaned Ollama processes.")
            return False
    except subprocess.CalledProcessError as e:
        logger.debug(f"lsof/netstat command failed or found nothing: {e.stderr.strip()}")
        return False
    except Exception as e:
        logger.error(f"Error finding/killing process on port {port}: {e}")
        return False

def start_ollama_server():
    """Starts the Ollama server if it's not already running. Manages its lifecycle."""
    global _ollama_process
    
    # Check if a managed Ollama process is already running
    if _ollama_process is not None and _ollama_process.poll() is None:
        logger.info("Ollama server process already running (managed by CapGate).")
        return
    
    # Check if port is in use by an *external* or orphaned process
    if _is_port_in_use(OLLAMA_SERVER_PORT, OLLAMA_SERVER_HOST):
        logger.warning(f"Port {OLLAMA_SERVER_PORT} is in use. Attempting to ensure it's not an orphaned Ollama.")
        if _find_and_kill_process_on_port(OLLAMA_SERVER_PORT, OLLAMA_SERVER_HOST):
            logger.info("Orphaned Ollama process found and terminated. Retrying server start.")
            time.sleep(1) # Give port time to release
            if _is_port_in_use(OLLAMA_SERVER_PORT, OLLAMA_SERVER_HOST):
                logger.error(f"Port {OLLAMA_SERVER_PORT} is still in use after attempted cleanup. Cannot start Ollama server.")
                raise RuntimeError(f"Ollama server port {OLLAMA_SERVER_PORT} is busy and cannot be freed.")
        else:
            logger.info(f"Port {OLLAMA_SERVER_PORT} is in use but not by an identifiable Ollama process. Assuming external/managed.")
            return # Assume external Ollama is running, don't try to start it.


    logger.info("Starting Ollama server in background...")
    try:
        # FIX: Call the 'ollama' executable directly, not via 'python -m ollama'
        # The 'ollama' executable must be in your system's PATH.
        _ollama_process = subprocess.Popen(
            ["ollama", "serve"], # CORRECTED COMMAND
            stdout=subprocess.PIPE, # Capture stdout for debugging
            stderr=subprocess.PIPE, # Capture stderr for debugging
            preexec_fn=os.setsid if sys.platform.startswith('linux') or sys.platform == 'darwin' else None, # Detach from controlling tty
            env={**os.environ, 'OLLAMA_HOST': OLLAMA_SERVER_HOST, 'OLLAMA_PORT': OLLAMA_SERVER_PORT} # Ensure env vars are passed
        )
        logger.info(f"Ollama server started with PID {_ollama_process.pid}.")
        time.sleep(2) # Give server a moment to start up

        # Check if process terminated immediately
        if _ollama_process.poll() is not None:
            stdout, stderr = _ollama_process.communicate() # Get captured output
            logger.error(f"Ollama server terminated unexpectedly on startup (Exit Code: {_ollama_process.returncode}).")
            logger.error(f"Ollama stdout:\n{stdout.decode().strip()}")
            logger.error(f"Ollama stderr:\n{stderr.decode().strip()}")
            raise RuntimeError("Ollama server failed to start.")

        # Register atexit to ensure cleanup
        atexit.register(stop_ollama_server)
        # Register signal handlers for graceful shutdown on Ctrl+C or kill signals
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    except FileNotFoundError:
        logger.error("Ollama command not found. Ensure Ollama is installed and in your PATH/venv.")
        logger.error("Try running 'ollama' directly in your terminal to confirm it's executable.")
        raise RuntimeError("Ollama command not found.")
    except Exception as e:
        logger.error(f"Error starting Ollama server: {e}")
        raise RuntimeError(f"Failed to start Ollama server: {e}")

def stop_ollama_server():
    """Stops the Ollama server process managed by CapGate."""
    global _ollama_process
    if _ollama_process is not None and _ollama_process.poll() is None:
        logger.info(f"Stopping Ollama server (PID: {_ollama_process.pid})...")
        try:
            # Use os.killpg for processes started with setsid to kill the whole process group
            if _ollama_process.pid and (sys.platform.startswith('linux') or sys.platform == 'darwin'):
                os.killpg(_ollama_process.pid, signal.SIGTERM)
            else:
                _ollama_process.terminate() # Standard terminate
            _ollama_process.wait(timeout=10) # Wait for termination
            logger.info("Ollama server terminated.")
        except psutil.NoSuchProcess:
            logger.info("Ollama server process already terminated.")
        except subprocess.TimeoutExpired:
            logger.warning("Ollama server did not terminate gracefully. Killing process.")
            if _ollama_process.pid and (sys.platform.startswith('linux') or sys.platform == 'darwin'):
                os.killpg(_ollama_process.pid, signal.SIGKILL) # Force kill
            else:
                _ollama_process.kill() # Force kill
            logger.info("Ollama server force-killed.")
        except Exception as e:
            logger.error(f"Error stopping Ollama server: {e}")
        _ollama_process = None
    else:
        logger.info("Ollama server not running or not managed by CapGate.")

def _signal_handler(signum, frame):
    """Custom signal handler for graceful shutdown."""
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    stop_ollama_server()
    sys.exit(signum)

def warm_up_ollama_model(model_name=OLLAMA_MODEL_NAME):
    """Pulls and warms up the specified Ollama model."""
    try:
        logger.info(f"Attempting to pull and warm up Ollama model '{model_name}'...")
        # FIX: Call the 'ollama' executable directly
        pull_result = subprocess.run(
            ["ollama", "pull", model_name], # CORRECTED COMMAND
            capture_output=True, text=True, check=True,
            env={**os.environ, 'OLLAMA_HOST': OLLAMA_SERVER_HOST, 'OLLAMA_PORT': OLLAMA_SERVER_PORT}
        )
        logger.info(f"Ollama pull output for {model_name}:\n{pull_result.stdout.strip()}")
        if pull_result.stderr:
            logger.warning(f"Ollama pull stderr for {model_name}:\n{pull_result.stderr.strip()}")

        # FIX: Call the 'ollama' executable directly for warmup
        logger.info(f"Triggering Ollama model '{model_name}' to load into memory...")
        warmup_proc = subprocess.Popen(
            ["ollama", "run", model_name], # CORRECTED COMMAND
            stdin=subprocess.PIPE, # To send 'Hello' and then /bye
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, 'OLLAMA_HOST': OLLAMA_SERVER_HOST, 'OLLAMA_PORT': OLLAMA_SERVER_PORT}
        )
        try:
            warmup_proc.stdin.write(b"Hello\n/bye\n")
            warmup_proc.stdin.flush()
            warmup_proc.wait(timeout=30) # Give it 30 seconds to load and process 'Hello' and /bye
            if warmup_proc.poll() is None:
                logger.warning(f"Ollama run for '{model_name}' did not exit after warmup. Terminating.")
                warmup_proc.terminate()
                warmup_proc.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error during interactive warmup of '{model_name}': {e}")
        finally:
            if warmup_proc.poll() is None: # Still running?
                warmup_proc.kill() # Force kill if necessary

        logger.info(f"Model '{model_name}' pull confirmed and warmup attempt completed.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error during Ollama pull/warmup for '{model_name}': {e.stderr}")
        logger.error(f"Try running 'ollama pull {model_name}' manually to debug.")
        raise RuntimeError(f"Failed to pull/warmup Ollama model {model_name}.")
    except subprocess.TimeoutExpired:
        logger.error(f"Ollama run warmup for '{model_name}' timed out. Model might be very large or system slow.")
        raise RuntimeError(f"Ollama model warmup for {model_name} timed out.")
    except FileNotFoundError:
        logger.error("Ollama command not found during warmup. Ensure Ollama is installed and in your PATH.")
        raise RuntimeError("Ollama command not found.")
    except Exception as e:
        logger.error(f"Unexpected error during Ollama warmup: {e}")
        raise RuntimeError(f"Unexpected error during Ollama warmup for {model_name}.")


# --- Main CapGate Application Initialization and Orchestration ---
def initialize_capgate_application(cli_mock_mode: bool = False, cli_auto_select: bool = False):
    """
    Initializes the core CapGate application components, including the runner.
    """
    global _runner_instance
    
    logger.info("CapGate Root: Initializing core application components...")
    
    # CapGateRunner's __init__ method will call ensure_directories_for_capgate_startup() from src.paths
    _runner_instance = CapGateRunner(cli_state={
        "mock_mode": cli_mock_mode,
        "auto_select": cli_auto_select
    })
    
    # Inject the runner instance into the CLI module
    set_global_runner(_runner_instance)
    logger.info("CapGate Root: CapGateRunner initialized and injected into CLI.")


def initialize_mcp_agent(force_index: bool = False):
    """
    Initializes the MCP AI Agent.
    """
    logger.info("CapGate Root: Attempting to initialize MCP Agent...")
    
    # The paths in agent.tools and agent.mod_coor are now directly imported from src.paths,
    # which uses the globally defined PROJECT_ROOT based on main.py's location.

    # Start and warm up Ollama before initializing the agent
    try:
        start_ollama_server()
        warm_up_ollama_model() # This pulls and attempts to load the model into memory
        # The agent's own initialize_capgate_agent will perform the API test connection
        # which effectively warms it further if not fully loaded.
    except RuntimeError as e:
        logger.error(f"CapGate Root: Failed to setup Ollama server or model: {e}. AI assistance will be unavailable.")
        # It's critical here: if Ollama isn't working, the agent won't work.
        return # Do not proceed with agent initialization

    try:
        initialize_capgate_agent() # This initializes LLM, embedding, and loads KB
        if force_index:
            logger.info("CapGate Root: Agent initialization complete. Forcing knowledge re-indexing as requested.")
            index_capgate_knowledge() # Call the index function from agent.mod_coor
        logger.info("CapGate Root: MCP Agent ready to assist.")
    except Exception as e:
        logger.error(f"CapGate Root: Failed to initialize MCP Agent: {e}. AI assistance will be unavailable.")


# --- Main Typer CLI App for Root ---
root_app = typer.Typer(
    help="""CapGate - The Wireless Network Intelligence Toolkit (Root Orchestrator)
This is the main entry point for CapGate, managing core application, CLI, and AI Agent.
""",
    invoke_without_command=True
)

# Merge the top-level commands from capgate_cli_app into root_app.
for command_info in capgate_cli_app.registered_commands: # Iterate over CommandInfo objects
    root_app.command(name=command_info.name, help=command_info.help)(command_info.callback)

# Explicitly add the sub-Typer apps from capgate_cli to root_app
# These are the apps that were added via `app.add_typer()` in capgate_cli.py
root_app.add_typer(graph_app, name="graph")
root_app.add_typer(debug_cli, name="debug")
root_app.add_typer(docs_app, name="docs") # Correctly adding the docs_app now!

@root_app.callback(invoke_without_command=True)
def root_main_callback(ctx: typer.Context): # Removed all Options from here
    """
    Main callback for the root CapGate application.
    Initializes core components if no subcommand is given.
    """
    logger.info("CapGate Root: Root callback initiated.")
    
    # Initialize core CapGateRunner based on root CLI options
    # These values will now be set by the actual commands if they use them
    initialize_capgate_application(cli_mock_mode=False, cli_auto_select=False) # Default to False if not explicit

    # The agent initialization logic is now exclusively part of the 'dev' command or other specific commands.
    # It is NOT part of the root callback unless a specific flag dictates it.
    # Since we moved --dev/--no-agent/--index-agent into *commands*,
    # the root callback simply initializes the core app.
    
    if ctx.invoked_subcommand is None:
        logger.info("CapGate Root: No subcommand invoked. Showing help for main commands.")
        typer.echo(root_app.info.help)


# --- NEW: `dev` command for interactive development mode ---
@root_app.command("dev", help="Run CapGate in interactive development mode with AI agent access.")
def dev_command(
    mock: bool = typer.Option(False, "--mock", help="Enable mock mode for runner."),
    auto: bool = typer.Option(False, "--auto", help="Auto-select plugin options for runner."),
    no_agent: bool = typer.Option(False, "--no-agent", help="Do not initialize the AI agent."),
    index_agent: bool = typer.Option(False, "--index-agent", help="Force re-indexing of agent knowledge on startup.")
):
    """
    Enters the interactive CapGate Development Mode.
    Initializes CapGateRunner and MCP Agent based on these options.
    """
    logger.info("CapGate Root: Entering interactive development mode...")
    
    # Initialize core CapGateRunner based on command options
    initialize_capgate_application(cli_mock_mode=mock, cli_auto_select=auto)

    # Initialize agent based on command options
    if not no_agent:
        initialize_mcp_agent(force_index=index_agent)
    else:
        logger.info("CapGate Root: AI Agent initialization skipped as requested by --no-agent.")

    logger.info("\nCapGate Development Mode Activated.")
    logger.info("Type 'agent-ask <query>' to ask the agent, 'agent-interactive' for chat, etc.")
    logger.info("Type 'exit' to quit dev mode.")

    while True:
        try:
            command_input = input("CapGate Dev> ").strip()
            if command_input.lower() == 'exit':
                break
            
            # Simple parsing for interactive mode for specific commands
            # This allows you to type commands like "agent-ask <query>" directly in the loop
            parts = command_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "agent-ask":
                if args:
                    response = ask_capgate_agent(args)
                    print(f"\n--- MCP Agent Response ---\n{response}\n--------------------------")
                else:
                    cli_console.print("[yellow]Please provide a query for 'agent-ask'.[/yellow]")
            elif cmd == "agent-interactive":
                start_capgate_agent_interactive_session()
            elif cmd == "agent-index":
                logger.info("CLI: Requesting agent knowledge re-indexing.")
                print("\n--- Rebuilding Agent Knowledge Base ---")
                index_capgate_knowledge()
                print("--- Agent Knowledge Base Rebuilding Initiated. Check logs. ---")
            else:
                cli_console.print(f"[yellow]Unknown command or not yet implemented in dev mode: '{command_input}'[/yellow]")
                cli_console.print("[cyan]Available commands: agent-ask, agent-interactive, agent-index, exit[/cyan]")

        except KeyboardInterrupt:
            print("\nExiting CapGate Development Mode.")
            break
        except Exception as e:
            logger.error(f"Error in dev mode: {e}")
            cli_console.print(f"[red]Error in dev mode:[/red] {e}")
            
    raise typer.Exit() # Exit after dev mode finishes


# --- Example: Add a new root-level command that uses both runner and agent (hypothetically) ---
@root_app.command("orchestrate-network-audit", help="Orchestrates a comprehensive network audit using agent guidance.")
def orchestrate_network_audit_command(
    interface_name: str = typer.Argument(..., help="Network interface to use for the audit.")
):
    """
    A hypothetical command showing how the root orchestrator could combine runner and agent capabilities.
    """
    logger.info(f"Root Orchestrator: Starting comprehensive network audit on {interface_name}...")
    
    # Example: Use runner to get interface details
    runner = _runner_instance
    if runner is None:
        logger.error("CapGateRunner not initialized for orchestration.")
        raise typer.Exit(code=1)

    interfaces = runner.get_interfaces(wireless_only=False, monitor_only=False, up_only=True)
    target_interface = next((i for i in interfaces if i.name == interface_name), None)

    if not target_interface:
        logger.error(f"Interface '{interface_name}' not found or not up.")
        raise typer.Exit(code=1)

    logger.info(f"CapGate Runner: Found interface details for {interface_name}: IP={target_interface.ip_address}")

    # Example: Use agent to get guidance
    # Ensure agent is initialized before asking
    from agent.mod_coor import capgate_agent_instance, ask_capgate_agent
    if capgate_agent_instance is None:
        logger.error("MCP Agent is not initialized. Cannot get audit guidance.")
        raise typer.Exit(code=1)

    agent_guidance_query = f"Given that I want to perform a comprehensive network audit on interface {interface_name} ({target_interface.ip_address}), what are the recommended CapGate plugins and steps, focusing on security best practices?"
    logger.info("Asking agent for audit guidance...")
    audit_guidance = ask_capgate_agent(agent_guidance_query)
    
    print("\n--- Agent's Audit Guidance ---")
    print(audit_guidance)
    print("------------------------------")

    logger.info("Root Orchestrator: Audit guidance received. Now you would proceed with executing plugins based on this.")
    # Here, you could programmatically call runner.run_plugin() based on agent's suggestions
    # E.g., if "nmap_scan_plugin" was suggested: runner.run_plugin("nmap_scan_plugin", interface_name)


# --- Main entry point for the root application ---
if __name__ == "__main__":
    # Typer handles parsing arguments and invoking the callback/commands
    root_app()