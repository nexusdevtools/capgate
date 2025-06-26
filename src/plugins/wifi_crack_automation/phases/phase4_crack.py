# src/plugins/wifi_crack_automation/phases/phase4_crack.py

from typing import Optional
import os  # Needed for os.path.exists

from core.logger import logger
from core.state_management.context import CapGateContext # Import CapGateContext
from core.cracking_manager import CrackingManager # Import the new CrackingManager

def crack_handshake(app_context: CapGateContext) -> bool:
    """
    Phase 4: Attempts to crack a WPA handshake using the CrackingManager.

    Args:
        app_context (CapGateContext): The global CapGate context for the current run.

    Returns:
        bool: True if the password is cracked and stored, False otherwise.
    """
    logger.info("[Phase 4] Cracking WPA handshake...")

    handshake_file: Optional[str] = app_context.get("handshake_file")
    if not handshake_file:
        logger.error("No handshake file available in context for cracking (expected from Phase 3).")
        return False

    # Get target BSSID from context (useful for targeted cracking)
    # target_bssid: Optional[str] = app_context.get("target_bssid")

    # Determine wordlist path
    wordlist_path: Optional[str] = app_context.get("wordlist") # Check if wordlist was set in context
    auto_mode: bool = app_context.get("auto_select_interface", False) # Use consistent auto-select key

    if not wordlist_path: # If no wordlist explicitly set in context
        default_wordlist = "/usr/share/wordlists/rockyou.txt" # Common Kali path
        
        if auto_mode:
            wordlist_path = default_wordlist
            logger.info(f"[Phase 4] Auto-selecting default wordlist: {wordlist_path}")
        else:
            try:
                # Prompt user for wordlist if not in auto-mode
                wordlist_path = input(f"Enter path to wordlist [{default_wordlist}]: ").strip() or default_wordlist
            except KeyboardInterrupt:
                logger.warning("[Phase 4] User interrupted wordlist prompt. Cracking skipped.")
                app_context.set("password", None)
                app_context.set("key_found", False)
                return False

    if not wordlist_path or not os.path.exists(wordlist_path): # os is still needed here for path check
        logger.error(f"[Phase 4] Wordlist not found or not specified: {wordlist_path}")
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False

    # Instantiate the CrackingManager
    cracking_manager = CrackingManager()

    # Call the abstracted cracking method
    cracked_password = cracking_manager.crack_wpa_handshake(
        handshake_file_path=handshake_file,
        wordlist_path=wordlist_path
        # You could pass target_bssid here if cracking_manager supported targeted cracking
    )

    if cracked_password:
        app_context.set("password", cracked_password)
        app_context.set("key_found", True)
        logger.info(f"[✓] Password cracked and stored in context.")
        return True
    else:
        logger.warning("[✘] Password not cracked or found in handshake file.")
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False

# Removed the __main__ block (consistent with other plugin phases)