# core/debug_tools.py

from typing import Any
from rich.console import Console
from rich.pretty import pprint

# Assuming these are the correct imports for your state management
from core.state_management.context import CapGateContext
from core.state_management.state import AppState

console = Console()

def debug_var(var_value: Any, var_name: str = "Variable"):
    """Prints a debug message with variable name and value."""
    console.log(f"[DEBUG] {var_name} (type={type(var_value).__name__}): {var_value!r}") # !r for representation

def print_exception(e: Exception):
    """Prints a formatted exception traceback."""
    console.print_exception(show_locals=True)

def dump_context(ctx: CapGateContext, title: str = "AppContext Dump"):
    """
    Dumps the contents of the CapGateContext and its associated AppState
    for debugging purposes.
    """
    console.print(f"\n🧠 [bold green]{title}[/bold green]:")
    
    # Dump runtime_meta from CapGateContext
    console.print("[yellow]--- Runtime Metadata (CapGateContext.runtime_meta) ---[/yellow]")
    pprint(ctx.to_dict()) # ctx.to_dict() gives runtime_meta

    # Dump global AppState (accessed via ctx.state)
    console.print("\n[yellow]--- Global Application State (CapGateContext.state / AppState) ---[/yellow]")
    pprint(ctx.state.to_dict()) # ctx.state is the AppState singleton, use its to_dict

    console.print("\n" + "="*80) # Separator for clarity

# You might also want a direct AppState dumper for specific use cases
def dump_app_state(app_state: AppState, title: str = "AppState Dump"):
    """
    Dumps the contents of the AppState object directly.
    """
    console.print(f"\n🧠 [bold cyan]{title}[/bold cyan]:")
    pprint(app_state.to_dict())
    console.print("\n" + "="*80)