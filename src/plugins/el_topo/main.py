# src/plugins/el_topo/main.py

# Removed subprocess and re imports as discovery logic is moved
# Removed time import as last_seen is handled by scanners/runner
# from core.debug_tools import debug_var, dump_context, print_exception # These are generally useful for plugins
from base.logger import logger
from base.state_management.context import CapGateContext # Import CapGateContext, not AppContext
# Removed AppContext import as CapGateContext is the new entry point
from base.graphs.topology import TopologyGraph
# Removed db.schemas.device.Device as device injection is moved
# Removed parse_arp_table as discovery is moved
# Removed inject_devices_into_context as device injection is moved


# --- MAIN ENTRY POINT ---
# CRITICAL CHANGE: app_context is now CapGateContext, as that's what the runner passes
def run(app_context: CapGateContext, *plugin_args: str):
    """
    Plugin entry point for 'el_topo'.
    This plugin visualizes the network topology based on data already present in AppState.

    Args:
        app_context (CapGateContext): Global context shared across CapGate,
                                       containing a reference to AppState.
        plugin_args (tuple[str]): Optional CLI args passed to the plugin.
    """
    try:
        logger.info("🌐 Running el_topo: Topology Visualization Plugin...")

        # No need to inject devices here; they should already be in app_context.state.discovery_graph
        # via the runner's initialization phase.

        # debug_var(app_context, "app_context") # Uncomment for debugging context passed to plugin
        # debug_var(plugin_args, "plugin_args") # Uncomment for debugging plugin args
        # dump_context(app_context) # Uncomment to see the full context state at plugin start

        # The TopologyGraph.build_from_context() method is already designed
        # to fetch data directly from app_context.state.discovery_graph.
        topo = TopologyGraph.build_from_context()
        
        # Determine output options from plugin_args or default behavior
        # Example: if you want to allow --ascii or --png flags for the plugin
        # In this simple case, we'll just export PNG by default.
        export_png = True # Default behavior
        print_ascii = False # Default behavior

        # You can parse plugin_args here if you want to control output
        # For example:
        if "--ascii" in plugin_args:
            print_ascii = True
        if "--no-png" in plugin_args: # Example for disabling default PNG
            export_png = False

        if print_ascii:
            topo.print_ascii()

        if export_png:
            topo.export_png()
            logger.info("✅ el_topo: Topology PNG exported.")
        else:
            logger.info("ℹ️ el_topo: PNG export skipped (use --no-png to disable).")

        logger.info("✅ el_topo: Topology visualization completed.")
    except Exception as e:
        # Using print_exception from core.debug_tools for consistent error logging
        from base.debug_tools import print_exception
        print_exception(e, "An error occurred during el_topo plugin execution") # Pass message
        logger.error(f"❌ el_topo: Plugin execution failed: {e}")
        return False
    return True
# --- END OF MAIN ENTRY POINT ---