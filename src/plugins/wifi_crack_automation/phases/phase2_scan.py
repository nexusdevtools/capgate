# /home/nexus/dev/projects/capgate/src/capgate/plugins/wifi_crack_automation/phases/phase2_scan.py
import subprocess
import tempfile
import time
import os
import csv # For more robust CSV parsing, though manual splitting is often fine for airodump.
from typing import Dict, Any, Optional, List

from core.logger import logger
# from helpers import shelltools # Not strictly needed if using subprocess.Popen directly

def scan_for_networks(plugin_local_context: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Scan nearby Wi-Fi networks using airodump-ng.
    Updates plugin_local_context with target BSSID, channel, and ESSID.
    Returns the selected target network dictionary or None on failure.
    """
    logger.info("[Phase 2] Scanning for nearby Wi-Fi networks...")

    # CRITICAL: Use the monitor_interface set by Phase 1
    monitor_interface = plugin_local_context.get("monitor_interface")
    if not monitor_interface:
        logger.error("Monitor interface not set in context (expected from Phase 1). Cannot scan.")
        return None

    scan_duration_seconds: int = plugin_local_context.get("scan_duration_seconds", 15) # More descriptive key
    auto_select: bool = plugin_local_context.get("auto_select", False)
    # Example: filter for networks with WPA/WPA2. 'WPA' would catch WPA, WPA2, WPA3.
    # For more specific filtering, this logic would need to be more nuanced.
    network_security_filter: str = plugin_local_context.get("network_security_filter", "WPA") 

    # Create a temporary file for airodump-ng output prefix
    # delete=False is important because airodump-ng writes to it, and we read it after.
    # The actual CSV file will be named {output_prefix}-01.csv
    temp_csv_handle = None
    try:
        temp_csv_handle = tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False)
        # We just need the prefix, airodump-ng appends "-01.csv"
        output_prefix = temp_csv_handle.name[:-4] 
        temp_csv_handle.close() # Close it so airodump-ng can write
    except Exception as e:
        logger.error(f"Failed to create temporary file for scan: {e}")
        if temp_csv_handle:
            os.unlink(temp_csv_handle.name) # Ensure cleanup if temp_csv_handle exists
        return None

    airodump_csv_file = f"{output_prefix}-01.csv"
    airodump_log_files_to_clean = [airodump_csv_file, f"{output_prefix}.cap", f"{output_prefix}.kismet.csv", f"{output_prefix}.kismet.netxml", f"{output_prefix}.log.csv"]


    proc = None
    try:
        # Ensure airodump-ng is in PATH or provide full path
        # Using --write-interval 1 to flush CSV data more frequently (optional)
        airodump_cmd = [
            "airodump-ng",
            "--output-format", "csv",
            "--write", output_prefix,
            "--write-interval", "1", # Flush CSV more often
            monitor_interface
        ]
        logger.debug(f"Executing airodump-ng command: {' '.join(airodump_cmd)}")
        
        # Using subprocess.Popen directly for better control over this long-running process
        proc = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.info(f"Scanning for networks on {monitor_interface} for {scan_duration_seconds} seconds (filter: {network_security_filter})...")
        
        # Allow scan to run, with handling for user interruption
        interrupted = False
        for _ in range(scan_duration_seconds):
            if proc.poll() is not None: # Process terminated unexpectedly
                logger.warning("airodump-ng terminated prematurely.")
                break
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Scan interrupted by user.")
                interrupted = True
                break
        if interrupted: # If loop was broken by interrupt
             pass # Proceed to terminate and parse

    except FileNotFoundError:
        logger.error("airodump-ng command not found. Please ensure it's installed and in your PATH.")
        return None
    except Exception as e:
        logger.error(f"Failed to start airodump-ng: {e}")
        return None
    finally:
        if proc:
            if proc.poll() is None: # If process is still running
                logger.info("Terminating airodump-ng...")
                proc.terminate()
            try:
                proc.wait(timeout=5) # Wait for it to terminate
            except subprocess.TimeoutExpired:
                logger.warning("airodump-ng did not terminate gracefully, killing.")
                proc.kill()
                proc.wait() # Wait for kill
            logger.debug("airodump-ng process finished.")

    if not os.path.exists(airodump_csv_file):
        logger.error(f"Airodump-ng output CSV file not found: {airodump_csv_file}")
        # Clean up other potential airodump files even if CSV is missing
        for f_to_clean in airodump_log_files_to_clean:
            if os.path.exists(f_to_clean) and f_to_clean != airodump_csv_file:
                try:
                    os.remove(f_to_clean)
                except OSError: pass # Ignore if removal fails
        return None

    networks: List[Dict[str, str]] = []
    try:
        with open(airodump_csv_file, "r", encoding='utf-8', errors='ignore') as f:
            # airodump-ng CSV is split into two sections: APs then Stations
            # The AP section ends when a line starts with "Station MAC"
            ap_section = True
            for line in f:
                line = line.strip()
                if not line: continue # Skip blank lines
                if line.startswith("Station MAC"): # Start of the client section
                    ap_section = False
                    continue
                if not ap_section: continue # We only care about APs for now

                # Header for APs is "BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key"
                if line.startswith("BSSID"): continue # Skip header

                parts = [p.strip() for p in line.split(",")] # Strip whitespace from each part

                # Basic check for enough parts for an AP line
                if len(parts) < 14: # ESSID is typically the 14th field (index 13)
                    continue

                bssid = parts[0]
                # First time seen = parts[1]
                # Last time seen = parts[2]
                channel = parts[3]
                # Speed = parts[4]
                privacy = parts[5] # e.g., "WPA2", "WPA", "WEP", "OPN", "WPA2 WPA"
                # Cipher = parts[6]
                # Authentication = parts[7]
                # Power = parts[8]
                essid = parts[13] # ESSID is often the 14th field (index 13)

                # Filter out "hidden" SSIDs (empty or with null bytes like '\x00')
                if not essid or '\x00' in essid:
                    essid_display = "<Hidden SSID>"
                else:
                    essid_display = essid
                
                # Apply security filter
                # The 'network_security_filter' should be a substring of the 'privacy' field
                # e.g., if filter is "WPA", it matches "WPA", "WPA2", "WPA2 WPA"
                if network_security_filter.upper() in privacy.upper():
                    networks.append({
                        "bssid": bssid,
                        "channel": channel,
                        "essid": essid_display, # Use display version for user
                        "essid_raw": essid,    # Keep raw for potential later use
                        "privacy": privacy,
                        "power": parts[8] # Power is parts[8]
                    })
    except Exception as e:
        logger.error(f"Failed to parse airodump-ng CSV output: {e}")
        return None
    finally:
        # Clean up all airodump-ng generated files
        for f_to_clean in airodump_log_files_to_clean:
            if os.path.exists(f_to_clean):
                try:
                    os.remove(f_to_clean)
                    logger.debug(f"Removed temp file: {f_to_clean}")
                except OSError as e_remove:
                    logger.warning(f"Could not remove temp file {f_to_clean}: {e_remove}")


    if not networks:
        logger.warning(f"No networks matching filter '{network_security_filter}' found after scan.")
        return None

    # Sort networks by power (descending) if power info is available
    try:
        networks.sort(key=lambda x: int(x.get("power", -100)), reverse=True)
    except ValueError:
        logger.warning("Could not sort networks by power due to non-integer power values.")


    selected_target: Optional[Dict[str, str]] = None
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
                if not choice_str and len(networks) >= 1: # Default to 1 if input is empty and list not empty
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
        # Update context with individual keys for easier access by subsequent phases
        plugin_local_context["target_bssid"] = selected_target["bssid"]
        plugin_local_context["target_channel"] = selected_target["channel"]
        plugin_local_context["target_essid"] = selected_target["essid_raw"] # Store raw ESSID
        plugin_local_context["target_privacy"] = selected_target["privacy"] # Store privacy/security info
        
        # For logging/display, use the potentially cleaned ESSID
        logger.info(f"[✓] Target selected: {selected_target['essid']} ({selected_target['bssid']}) on channel {selected_target['channel']}")
        return selected_target # Return the full selected target dict as well
    else:
        logger.error("No target network was selected.")
        return None

if __name__ == "__main__":
# # For standalone testing of phase2_scan:
# # 1. Ensure airodump-ng is installed and in PATH.
# # 2. This test will attempt to run airodump-ng on a real interface.
# # 3. Manually ensure the interface is in monitor mode before running.
# 
     test_context_phase2 = {
         "monitor_interface": "wlan0mon",  # REPLACE with your actual monitor interface name
         "scan_duration_seconds": 10,
         "auto_select": False,
         "network_security_filter": "WPA" # or "WEP", "OPN" etc.
     }
     logger.info(f"Starting standalone test for Phase 2 with context: {test_context_phase2}")
     if not os.geteuid() == 0:
         logger.error("Standalone test for Phase 2 needs root if airodump-ng requires it.")
     else:
         selected_network = scan_for_networks(test_context_phase2)
         if selected_network:
             logger.info(f"Standalone Test Succeeded. Selected: {selected_network}")
             logger.info(f"Context after scan: BSSID={test_context_phase2.get('target_bssid')}, Channel={test_context_phase2.get('target_channel')}, ESSID={test_context_phase2.get('target_essid')}")
         else:
             logger.error("Standalone Test Failed: No network selected or scan error.")
         logger.info("Test completed.")