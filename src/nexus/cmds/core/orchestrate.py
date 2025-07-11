# src/nexus/cmds/core/orchestrate.py

import typer
from base.logger import logger
from typing import Optional # For typer.Argument type hints

# Import runner instance getter and agent functions
from nexus.index import get_nexus_runner # New way to get runner
from agent.mod_coor import capgate_agent_instance, ask_capgate_agent # Re-import to check state


@typer.command("orchestrate-network-audit", help="Orchestrates a comprehensive network audit using agent guidance.")
def orchestrate_network_audit(
    interface_name: str = typer.Argument(..., help="Network interface to use for the audit.")
):
    """
    A hypothetical command showing how the root orchestrator could combine runner and agent capabilities.
    """
    logger.info(f"Root Orchestrator: Starting comprehensive network audit on {interface_name}...")
    
    runner = get_nexus_runner() # Get the runner from the nexus orchestrator
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
