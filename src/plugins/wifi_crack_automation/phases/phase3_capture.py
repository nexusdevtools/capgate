# /home/nexus/capgate/src/plugins/wifi_crack_automation/phases/phase3_capture.py

from typing import Optional # Keep for type hints
# Removed subprocess, os, time imports - now handled by CaptureManager

from base.logger import logger
from base.state_management.context import CapGateContext # Import CapGateContext
from base.capture_manager import CaptureManager # Import the new CaptureManager

def capture_handshake(app_context: CapGateContext) -> bool:
    """
    Phase 3: Initiates WPA handshake capture for the selected target network
    using the CaptureManager.

    Args:
        app_context (CapGateContext): The global CapGate context for the current run.

    Returns:
        bool: True if a handshake is successfully captured and the file path is stored, False otherwise.
    """
    logger.info("[Phase 3] Capturing WPA handshake...")

    # Retrieve necessary parameters from app_context.runtime_meta (set by main plugin or previous phases)
    target_bssid: Optional[str] = app_context.get("target_bssid")
    target_channel: Optional[str] = app_context.get("target_channel")
    target_essid: Optional[str] = app_context.get("target_essid")
    monitor_interface: Optional[str] = app_context.get("monitor_interface")
    
    capture_time: int = app_context.get("capture_time_seconds", 30) # Default to 30 seconds
    deauth_count: int = app_context.get("deauth_count", 5) # Default deauth packets
    auto_mode: bool = app_context.get("auto_select_interface", False) # Use consistent auto-select key

    if not target_bssid or not target_channel or not monitor_interface:
        logger.error("Target BSSID, channel, or monitor interface missing in context. Cannot capture handshake.")
        return False

    # Create a descriptive output file prefix for the capture
    output_file_prefix = f"handshake_{target_essid.replace(' ', '_').replace('/', '_')}_{target_bssid.replace(':', '')}"

    # Instantiate the CaptureManager
    capture_manager = CaptureManager()

    # Call the abstracted capture handshake method
    captured_file_path = capture_manager.capture_handshake(
        monitor_interface=monitor_interface,
        target_bssid=target_bssid,
        target_channel=target_channel,
        output_file_prefix=output_file_prefix,
        capture_time_seconds=capture_time,
        deauth_count=deauth_count,
        auto_mode=auto_mode
    )

    if captured_file_path:
        app_context.set("handshake_file", captured_file_path) # Store full path to captured file
        logger.info(f"[✓] Handshake captured. File: {captured_file_path}")
        return True
    else:
        logger.error("[✘] Handshake capture failed.")
        app_context.set("handshake_file", None) # Ensure context is clear
        return False

# Removed the __main__ block (consistent with other plugin phases)