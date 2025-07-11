# src/core/debug_tools.py

from rich.console import Console
from rich.pretty import pprint
from typing import Any, Optional # Import Optional

# Assuming these are the correct imports for your state management
from base.state_management.context import CapGateContext
from base.state_management.state import AppState

console = Console()

def debug_var(var_value: Any, var_name: str = "Variable"):
    """Prints a debug message with variable name and value."""
    console.log(f"[DEBUG] {var_name} (type={type(var_value).__name__}): {var_value!r}")

# CRITICAL FIX: Added optional 'message' argument
def print_exception(e: Exception, message: Optional[str] = None):
    """Prints a formatted exception traceback with an optional message."""
    if message:
        console.log(f"[bold red]ERROR:[/bold red] {message}") # Use console.log for consistent timestamping
    console.print_exception(show_locals=True)

def dump_context(ctx: CapGateContext, title: str = "AppContext Dump"):
    """
    Dumps the contents of the CapGateContext's runtime_meta
    and its associated global AppState for debugging purposes.
    """
    console.print(f"\n🧠 [bold green]{title}[/bold green]:")
    
    # Dump runtime_meta from CapGateContext
    console.print("[yellow]--- Runtime Metadata (CapGateContext.runtime_meta) ---[/yellow]")
    runtime_meta_copy = ctx.to_dict()
    if runtime_meta_copy:
        pprint(runtime_meta_copy)
    else:
        console.print("[dim]No runtime metadata set.[/dim]")

    # Dump global AppState (accessed via ctx.state)
    console.print("\n[yellow]--- Global Application State (CapGateContext.state / AppState) ---[/yellow]")
    app_state_copy = ctx.state.to_dict()
    if app_state_copy:
        pprint(app_state_copy)
    else:
        console.print("[dim]Global AppState is empty or not initialized.[/dim]")

    console.print("\n" + "="*80)

def dump_app_state(app_state: AppState, title: str = "AppState Dump"):
    """
    Dumps the contents of the AppState object directly.
    """
    console.print(f"\n🧠 [bold cyan]{title}[/bold cyan]:")
    app_state_copy = app_state.to_dict()
    if app_state_copy:
        pprint(app_state_copy)
    else:
        console.print("[dim]AppState is empty or not initialized.[/dim]")
    console.print("\n" + "="*80)