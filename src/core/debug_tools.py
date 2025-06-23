# src/core/debug_tools.py

import json
import traceback
from typing import Any
from rich.console import Console

console = Console()

def debug_var(var: Any, name: str = "var"):
    """
    Pretty-print a variable’s name, type, and value.
    """
    console.print(f"[bold yellow][DEBUG][/bold yellow] {name} (type={type(var).__name__}): {repr(var)}")

def debug_dict(d: dict[Any, Any], name: str = "dict"):
    """
    Print keys and value types of a dictionary.
    """
    console.print(f"[bold cyan]🔍 Debugging dict: {name}[/bold cyan]")
    for k, v in d.items():
        console.print(f"  [green]{k}[/green] : ({type(v).__name__}) {repr(v)}")

def dump_context(ctx: Any, name: str = "AppContext"):
    """
    Safely print AppContext contents.
    """
    from core.logger import logger
    try:
        output = ctx.as_dict() if hasattr(ctx, "as_dict") else ctx
        formatted = json.dumps(output, indent=2, default=str)
        console.print(f"[bold green]🧠 {name} Dump:[/bold green]")
        console.print(formatted)
    except Exception as e:
        logger.error(f"Failed to dump context: {e}")
        print_exception(e)

def print_exception(e: Exception):
    """
    Print the full traceback of an exception.
    """
    console.print("[red bold]⚠ Exception Traceback:[/red bold]")
    traceback_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    console.print(traceback_str)
