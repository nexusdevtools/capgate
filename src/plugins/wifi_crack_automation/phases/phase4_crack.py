# src/plugins/wifi_crack_automation/phases/phase4_crack.py

from typing import Optional

from core.logger import logger
from core.state_management.context import CapGateContext
from core.cracking_manager import CrackingManager

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

    # Get target BSSID from context (useful for targeted cracking, though CrackingManager doesn't use it yet)
    # target_bssid: Optional[str] = app_context.get("target_bssid") # Not directly used in this function's call to CrackingManager

    # Determine wordlist path
    wordlist_path_from_context: Optional[str] = app_context.get("wordlist") # Check if wordlist was set in context
    auto_mode: bool = app_context.get("auto_select_interface", False)

    final_wordlist_to_use: Optional[str] = None
    default_rockyou_path = "/usr/share/wordlists/rockyou.txt" # Base string for rockyou.txt

    if wordlist_path_from_context:
        final_wordlist_to_use = wordlist_path_from_context
        logger.info(f"[Phase 4] Using wordlist from context: {final_wordlist_to_use}")
    elif auto_mode:
        final_wordlist_to_use = default_rockyou_path
        logger.info(f"[Phase 4] Auto-selecting default wordlist: {final_wordlist_to_use}")
    else:
        try:
            # Prompt user for wordlist if not in auto-mode and not provided
            final_wordlist_to_use = input(f"Enter path to wordlist [{default_rockyou_path}]: ").strip() or default_rockyou_path
        except KeyboardInterrupt:
            logger.warning("[Phase 4] User interrupted wordlist prompt. Cracking skipped.")
            app_context.set("password", None)
            app_context.set("key_found", False)
            return False

    # Instantiate the CrackingManager
    cracking_manager = CrackingManager()

    # The CrackingManager.find_wordlist method will now robustly search and decompress.
    # Its internal logging will indicate if it successfully found a usable path.
    usable_wordlist_path = cracking_manager.find_wordlist(final_wordlist_to_use)

    if not usable_wordlist_path:
        # CrackingManager.find_wordlist already logged an error/warning if not found
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False # Exit early if no usable wordlist

    # Call the abstracted cracking method with the *resolved* wordlist path
    cracked_password = cracking_manager.crack_wpa_handshake(
        handshake_file_path=handshake_file,
        wordlist_path=usable_wordlist_path # Pass the resolved path
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