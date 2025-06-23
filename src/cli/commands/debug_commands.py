# cli/debug_commands.py

import json
import typer
from core.state_management.state import get_state
from core.state_management.context import get_context

debug_cli = typer.Typer(help="🧩 Inspect internal CapGate state and context")

@debug_cli.command("state")
def show_state():
    """
    Show the current AppState snapshot.
    """
    state = get_state()
    typer.echo(json.dumps(state.to_dict(), indent=4))


@debug_cli.command("context")
def inspect_context():
    """
    Show the current CapGateContext session metadata.
    """
    context = get_context()
    typer.echo(json.dumps(context.to_dict(), indent=4))
