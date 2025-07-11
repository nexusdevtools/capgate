# src/nexus/cmds/core/boot.py

import typer
from cli.commands.boot import boot_sequence # Import original boot sequence

@typer.command(help="Launch the animated CapGate boot sequence.")
def boot():
    """Launch the animated CapGate boot sequence."""
    boot_sequence()
