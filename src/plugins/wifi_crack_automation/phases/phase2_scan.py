# /home/nexus/capgate/src/plugins/wifi_crack_automation/phases/phase2_scan.py

from typing import Dict, Optional, List

from base.logger import logger
from base.state_management.context import CapGateContext # Import CapGateContext
from base.network_scanner import NetworkScanner # Import the new NetworkScanner

def scan_for_networks(app_context: CapGateContext) -> Optional[Dict[str, str]]:
    """
    Scan nearby Wi-Fi networks using airodump-ng via NetworkScanner.
    Updates app_context with selected target BSSID, channel, and ESSID.
    Returns the selected target network dictionary or None on failure.
    """
    logger.info("[Phase 2] Scanning for nearby Wi-Fi networks...")

    monitor_interface: Optional[str] = app_context.get("monitor_interface")
    if not monitor_interface:
        logger.error("Monitor interface not set in context (expected from Phase 1). Cannot scan.")
        return None

    # Retrieve settings from app_context's runtime_meta (set by plugin's main.py)
    scan_duration_seconds: int = app_context.get("scan_duration_seconds", 15)
    auto_select: bool = app_context.get("auto_select_interface", False) # Use auto_select_interface as set by main.py
    network_security_filter: str = app_context.get("network_security_filter", "WPA")
    
    # Check for CLI-provided target BSSID
    target_bssid_cli_arg: Optional[str] = app_context.get("target_bssid_cli_arg")

    # Instantiate the NetworkScanner
    network_scanner = NetworkScanner()

    # Perform the scan using the abstracted NetworkScanner
    # The output_prefix is handled internally by NetworkScanner.perform_airodump_scan
    networks: List[Dict[str, str]] = network_scanner.perform_airodump_scan(
        monitor_interface,
        scan_duration_seconds,
        network_security_filter
    )

    if not networks:
        logger.warning(f"No networks matching filter '{network_security_filter}' found after scan.")
        return None

    selected_target: Optional[Dict[str, str]] = None

    if target_bssid_cli_arg:
        # If a target BSSID was provided via CLI, try to find it
        found_cli_target = next((net for net in networks if net['bssid'].lower() == target_bssid_cli_arg.lower()), None)
        if found_cli_target:
            selected_target = found_cli_target
            logger.info(f"CLI specified target network found: {selected_target['essid']} ({selected_target['bssid']})")
        else:
            logger.warning(f"CLI specified target BSSID '{target_bssid_cli_arg}' not found in scan results. Falling back to selection.")

    if not selected_target: # If no CLI target or CLI target not found
        if auto_select or len(networks) == 1:
            selected_target = networks[0]
            logger.info(f"Auto-selected network: {selected_target['essid']} ({selected_target['bssid']}) [Ch: {selected_target['channel']}, Pwr: {selected_target['power']}]")
        else:
            print("\nDetected networks (sorted by signal strength):")
            for idx, net in enumerate(networks):
                print(f"  {idx+1}. {net['essid']} ({net['bssid']}) [Ch: {net['channel']}, Pwr: {net['power']}, Sec: {net['privacy']}]")
            
            while True:
                try:
                    choice_str = input(f"Select target network number [1-{len(networks)}]: ").strip()
                    if not choice_str and len(networks) >= 1:
                        choice_str = "1"
                    
                    choice_idx = int(choice_str) - 1
                    if 0 <= choice_idx < len(networks):
                        selected_target = networks[choice_idx]
                        break
                    else:
                        print(f"Invalid selection. Please enter a number between 1 and {len(networks)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                except EOFError:
                    logger.warning("Input stream closed (EOF). No network selected.")
                    return None

    if selected_target:
        # Store selected network details in app_context's runtime_meta
        app_context.set("target_bssid", selected_target["bssid"])
        app_context.set("target_channel", selected_target["channel"])
        app_context.set("target_essid", selected_target["essid_raw"])
        app_context.set("target_privacy", selected_target["privacy"])
        
        logger.info(f"[✓] Target selected: {selected_target['essid']} ({selected_target['bssid']}) on channel {selected_target['channel']}")
        return selected_target
    else:
        logger.error("No target network was selected.")
        return None

# Removed __main__ block (consistent with other plugin phases)