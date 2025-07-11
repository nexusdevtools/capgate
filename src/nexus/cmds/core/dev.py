# src/nexus/cmds/core/dev.py

from base.logger import logger
import typer
from typing import Optional, List # For typer.Option type hints

# Import agent components (these are the LlamaIndex-specific initialization parts)
from agent.mod_coor import ask_capgate_agent, start_capgate_agent_interactive_session, index_capgate_knowledge, initialize_capgate_agent # initialize_capgate_agent is now only called by initialize_mcp_agent

# Import cli_console for consistent output in the interactive loop
from cli.capgate_cli import console as cli_console

# Import the main application initialization and agent setup functions
# These are the high-level functions that orchestrate the runner and the full agent stack (including Ollama)
from capgate import initialize_capgate_application, initialize_mcp_agent


logger = logging.getLogger(__name__)

# NOTE: This file defines a single command 'dev'. It does NOT define a Typer app instance (`app = typer.Typer()`).
# The `dev` command function below will be imported and registered directly to the `nexus_app` in `src/nexus/index.py`.

@typer.command(help="Run CapGate in interactive development mode with AI agent access.")
def dev(
    mock: bool = typer.Option(False, "--mock", help="Enable mock mode for runner."),
    auto: bool = typer.Option(False, "--auto", help="Auto-select plugin options for runner."),
    no_agent: bool = typer.Option(False, "--no-agent", help="Do not initialize the AI agent."),
    index_agent: bool = typer.Option(False, "--index-agent", help="Force re-indexing of agent knowledge on startup.")
) -> None:
    """
    Enters the interactive CapGate Development Mode.
    Initializes CapGateRunner and MCP Agent based on these options.
    """
    logger.info("CapGate Root: Entering interactive development mode...")
    
    # Initialize core CapGateRunner based on command options
    initialize_capgate_application(cli_mock_mode=mock, cli_auto_select=auto)

    # Initialize agent based on command options (this high-level function handles Ollama too)
    if not no_agent:
        initialize_mcp_agent(force_index=index_agent)
    else:
        logger.info("CapGate Root: AI Agent initialization skipped as requested by --no-agent.")

    logger.info("\nCapGate Development Mode Activated.")
    logger.info("Type 'agent-ask <query>' to ask the agent, 'agent-interactive' for chat, etc.")
    logger.info("Type 'exit' to quit dev mode.")

    while True:
        try:
            command_input = typer.prompt("CapGate Dev>") # Use typer.prompt for cleaner input
            if command_input.lower() == 'exit':
                break
            
            # Simple parsing for interactive mode for specific commands
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