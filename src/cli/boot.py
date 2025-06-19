from time import sleep
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
fig = Figlet(font='slant')

def boot_sequence():
    console.print(fig.renderText('CapGate'), style="bold cyan")

    tagline = Text("⚡ The Network That Maps Itself", style="bold magenta")
    console.print(Panel(tagline, expand=False, border_style="cyan"))

    stages = [
        ("Injecting neural topology engine", "green"),
        ("Loading scanner modules", "yellow"),
        ("Initializing context and schemas", "blue"),
        ("Starting passive recon daemon", "magenta"),
        ("Establishing recursive graph sync", "green"),
        ("Booting vision core", "cyan"),
        ("System ready: CapGate is online", "bold green"),
    ]

    for message, color in stages:
        console.print(f"[{color}]✓ {message}")
        sleep(0.4)

    console.print("\n[bold red]Open source cyber-intel for the people.[/bold red]")
    console.print("[bold blue]Built from the streets up.[/bold blue]")
    console.print("[dim white]github.com/nexusdevtools/capgate[/dim white]\n")
