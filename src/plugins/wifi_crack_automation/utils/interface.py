# capgate/plugins/wifi_crack_automation/utils/interface.py
import re
from typing import Optional, Tuple # Ensure Tuple is imported

from core.logger import logger
from helpers import shelltools # Import your shelltools
# import subprocess # Removed as shelltools is used for all commands

def list_wireless_interfaces() -> list[str]:
    """
    List wireless interfaces using iw dev (via shelltools).
    Returns a list of interface names.
    """
    try:
        # iw dev typically does not require root for listing.
        output = shelltools.run_command("iw dev", require_root=False, check=True)
        return re.findall(r"^\s*Interface\s+(\w+)", output, re.MULTILINE)
    except Exception as e: # Catches CalledProcessError if check=True, or other errors
        logger.error(f"Failed to list wireless interfaces using 'iw dev': {e}")
        return []

def list_all_interfaces() -> list[str]:
    """
    List available wireless interfaces using airmon-ng and iwconfig as fallbacks.
    Returns a sorted list of unique interface names.
    """
    interfaces = set()
    try:
        # airmon-ng usually requires root to list devices that can be put into monitor mode.
        airmon_output = shelltools.run_command("airmon-ng", require_root=True, check=True)
        # Typical airmon-ng output has interface name in the first column.
        # Skip header lines if any.
        for line in airmon_output.splitlines():
            if line.strip() and not line.lower().startswith(("phy", "interface")):
                parts = line.split()
                if parts:
                    interfaces.add(parts[0]) # Assuming first column is interface name
    except Exception as e:
        logger.warning(f"airmon-ng failed or not found when listing interfaces ({e}), falling back to iwconfig...")

    try:
        # iwconfig usually does not require root for listing.
        iwconfig_output = shelltools.run_command("iwconfig", require_root=False, check=False)
        for line in iwconfig_output.splitlines():
            if "ieee 802.11" in line.lower(): # A common indicator of a wireless interface
                parts = line.split()
                if parts:
                    interfaces.add(parts[0])
    except Exception as e:
        logger.warning(f"iwconfig also failed to list interfaces: {e}")

    return sorted(list(interfaces))


def enable_monitor_mode(interface: str, app_context=None) -> Tuple[Optional[str], bool]:
    """
    Enable monitor mode on the given interface.
    - Manages NetworkManager to prevent interference.
    - Tries ip/iw first, then falls back to airmon-ng.
    - Parses the actual monitor interface name.
    Returns a tuple: (monitor_interface_name_or_None, nm_was_set_unmanaged_flag).
    """
    actual_monitor_iface_name: Optional[str] = None
    nm_was_set_unmanaged: bool = False

    try:
        # --- Check if NetworkManager is managing the interface ---
        # Using GENERAL.NM-MANAGED as confirmed by your system's nmcli stderr.
        nm_managed_command = f"nmcli -g GENERAL.NM-MANAGED dev show {interface}"
        nm_managed_output = shelltools.run_command_no_check(
            nm_managed_command, require_root=True
        ).strip().lower()

        logger.debug(f"Output of '{nm_managed_command}': '{nm_managed_output}'")

        if nm_managed_output == "yes":
            logger.info(f"NetworkManager is managing {interface} (state: 'yes'). Setting to unmanaged.")
            shelltools.run_command(f"nmcli dev set {interface} managed no", require_root=True)
            nm_was_set_unmanaged = True
        else:
            logger.info(f"NetworkManager is not actively managing {interface} (nmcli output for GENERAL.NM-MANAGED was not 'yes', was: '{nm_managed_output}').")

    except Exception as e:
        logger.warning(f"Could not check or modify NetworkManager status for {interface}: {e}. Proceeding with caution.")

    try:
        # --- Attempt 1: Using ip + iw ---
        logger.info(f"Attempting to set {interface} to monitor mode using ip/iw.")
        shelltools.run_command(f"ip link set {interface} down", require_root=True)
        shelltools.run_command(f"iw dev {interface} set type monitor", require_root=True)
        shelltools.run_command(f"ip link set {interface} up", require_root=True)
        
        iw_info = shelltools.run_command(f"iw dev {interface} info", require_root=True)
        if "type monitor" in iw_info.lower():
            actual_monitor_iface_name = interface
            logger.info(f"[✓] {interface} successfully set to monitor mode using ip/iw.")
        else:
            logger.warning(f"ip/iw commands ran for {interface}, but mode is not 'monitor'. Current info: {iw_info}")
            raise Exception("Mode not 'monitor' after ip/iw attempt") # Custom exception to trigger fallback

    except Exception as e_iw: 
        logger.warning(f"Setting monitor mode with ip/iw failed for {interface} (Error: {e_iw}). Trying airmon-ng...")
        try:
            # --- Attempt 2: Using airmon-ng ---
            logger.info(f"Attempting to set {interface} to monitor mode using airmon-ng.")
            # Consider 'airmon-ng check kill' if persistent issues with interfering processes.
            # shelltools.run_command("airmon-ng check kill", require_root=True)
            
            airmon_output = shelltools.run_command(f"airmon-ng start {interface}", require_root=True)
            logger.debug(f"airmon-ng start {interface} output: {airmon_output}")

            # Regex to find common patterns for monitor interface name from airmon-ng output
            match = re.search(
                r"(?:vif enabled for \[\w+\]\w+ on \[\w+\](\w+)|enabled on (\w+mon\d*|\w+mon))",
                airmon_output,
                re.IGNORECASE
            )
            parsed_name = None
            if match:
                parsed_name = match.group(1) or match.group(2) # Check both capture groups

            if parsed_name:
                actual_monitor_iface_name = parsed_name.strip()
                logger.info(f"[✓] Monitor mode enabled via airmon-ng. New monitor interface: {actual_monitor_iface_name}.")
            else:
                # Fallback: Check if original interface is now in monitor mode (some airmon-ng versions/setups)
                iw_info_after_airmon = shelltools.run_command(f"iw dev {interface} info", require_root=True, check=False)
                if "type monitor" in iw_info_after_airmon.lower():
                    actual_monitor_iface_name = interface
                    logger.info(f"[✓] airmon-ng seems to have set {interface} to monitor mode directly.")
                else:
                    logger.error(f"airmon-ng ran but could not parse monitor interface name from output, and {interface} is not in monitor mode.")
                    # actual_monitor_iface_name remains None
        
        except Exception as e_airmon: # Catches CalledProcessError from shelltools or FileNotFoundError
            logger.error(f"airmon-ng also failed to set monitor mode for {interface}. Error: {e_airmon}")
            # actual_monitor_iface_name remains None
    
    finally:
        # This finally block only restores NM management if monitor mode setup FAILED
        # AND we had previously set it to unmanaged.
        # If monitor mode SUCCEEDED, the nm_was_set_unmanaged flag will be True,
        # and the CALLER is responsible for restoring NM management in its own finally block.
        if actual_monitor_iface_name is None and nm_was_set_unmanaged:
            logger.info(f"Monitor mode setup failed for {interface}. Restoring NetworkManager management as immediate cleanup.")
            try:
                shelltools.run_command(f"nmcli dev set {interface} managed yes", require_root=True)
                nm_was_set_unmanaged = False # Indicate we've handled the restoration due to failure
            except Exception as e_nm_restore:
                logger.error(f"Failed to restore NetworkManager management for {interface} after setup failure: {e_nm_restore}")

    if actual_monitor_iface_name:
        logger.info(f"[✓] Monitor mode active on: {actual_monitor_iface_name}. Original NM management was {'yes' if nm_was_set_unmanaged else 'no/other (not modified or restored yet)'}.")
    else:
        logger.error(f"[✘] Failed to enable monitor mode for {interface} after all attempts.")
    
    return actual_monitor_iface_name, nm_was_set_unmanaged