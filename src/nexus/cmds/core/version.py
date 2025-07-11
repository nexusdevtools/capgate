# src/nexus/cmds/core/version.py

import typer

@typer.command(help="Display the current version of CapGate.")
def version():
    """Display the current version of CapGate."""
    typer.echo("CapGate v0.1.0")