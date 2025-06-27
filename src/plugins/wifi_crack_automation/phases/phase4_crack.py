# src/plugins/wifi_crack_automation/phases/phase4_crack.py

import os
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

    wordlist_path_from_context: Optional[str] = app_context.get("wordlist") # Check if wordlist was set in context
    auto_mode: bool = app_context.get("auto_select_interface", False)

    # CRITICAL CHANGE: Set the new preferred default wordlist path
    # This path is relative to the CapGate project root, which will be handled by find_wordlist
    new_default_wordlist = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')),
        'src', 'wordlists', 'wordlist-top4800-probable.txt'
    )
    
    final_wordlist_to_use: Optional[str] = None

    if wordlist_path_from_context:
        final_wordlist_to_use = wordlist_path_from_context
        logger.info(f"[Phase 4] Using wordlist from context: {final_wordlist_to_use}")
    elif auto_mode:
        final_wordlist_to_use = new_default_wordlist
        logger.info(f"[Phase 4] Auto-selecting default wordlist: {final_wordlist_to_use}")
    else:
        try:
            final_wordlist_to_use = input(f"Enter path to wordlist [{new_default_wordlist}]: ").strip() or new_default_wordlist
        except KeyboardInterrupt:
            logger.warning("[Phase 4] User interrupted wordlist prompt. Cracking skipped.")
            app_context.set("password", None)
            app_context.set("key_found", False)
            return False

    cracking_manager = CrackingManager()
    usable_wordlist_path = cracking_manager.find_wordlist(final_wordlist_to_use)

    if not usable_wordlist_path:
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False

    cracked_password = cracking_manager.crack_wpa_handshake(
        handshake_file_path=handshake_file,
        wordlist_path=usable_wordlist_path
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
