# src/plugins/wifi_crack_automation/phases/phase4_crack.py

from typing import Optional

from base.logger import logger
from base.state_management.context import CapGateContext
from base.cracking_manager import CrackingManager
# Import the paths module to get the WORDLISTS_DIR
from paths import WORDLISTS_DIR


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

    wordlist_path_from_context: Optional[str] = app_context.get("wordlist")
    auto_mode: bool = app_context.get("auto_select_interface", False)

    # CRITICAL CHANGE: Set the new preferred default wordlist path using WORDLISTS_DIR
    new_default_wordlist = str(WORDLISTS_DIR / "wordlist-top4800-probable.txt") # Convert Path object to string
    logger.debug("[Phase 4] New default wordlist path: %s", new_default_wordlist)
    # Determine the final wordlist to use based on context or user input
    # If a wordlist was provided in the context, use that; otherwise, prompt the user or use the default.
    if not handshake_file:
        logger.error("[Phase 4] No handshake file found in context. Cannot proceed with cracking.")
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False
    logger.debug("[Phase 4] Handshake file to crack: %s", handshake_file)
    # Check if a wordlist was provided in the context
    wordlist_path_from_context = app_context.get("wordlist")
    logger.debug("[Phase 4] Wordlist path from context: %s", wordlist_path_from_context)
    # If no wordlist was provided, use the new default wordlist
    # If auto mode is enabled, use the new default wordlist
    # Otherwise, prompt the user for a wordlist path
    # If the user interrupts, skip cracking and set password to None
    if not wordlist_path_from_context:
        logger.debug("[Phase 4] No wordlist provided in context, using default or prompting user.")
    else:
        logger.debug("[Phase 4] Wordlist provided in context: %s", wordlist_path_from_context)
    # Determine the final wordlist to use
    # If a wordlist was provided in the context, use that; otherwise, prompt the user or use the default.
    # If auto mode is enabled, use the new default wordlist
    # Otherwise, prompt the user for a wordlist path
    # If the user interrupts, skip cracking and set password to None
    final_wordlist_to_use: Optional[str] = None

    if wordlist_path_from_context:
        final_wordlist_to_use = wordlist_path_from_context
        logger.info("[Phase 4] Using wordlist from context: %s", final_wordlist_to_use)
    elif auto_mode:
        final_wordlist_to_use = new_default_wordlist
        logger.info("[Phase 4] Auto-selecting default wordlist: %s", final_wordlist_to_use)
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
        logger.info("[✓] Password cracked and stored in context.")
        return True
    else:
        logger.warning("[✘] Password not cracked or found in handshake file.")
        app_context.set("password", None)
        app_context.set("key_found", False)
        return False
