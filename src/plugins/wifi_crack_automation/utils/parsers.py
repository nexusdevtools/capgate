import os
import re

def parse_airodump_csv(csv_lines):
    networks = []
    for line in csv_lines:
        if re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", line):
            parts = line.split(',')
            if len(parts) > 13:
                networks.append({
                    "bssid": parts[0].strip(),
                    "channel": parts[3].strip(),
                    "essid": parts[13].strip()
                })
    return networks

def parse_hashcat_potfile(hccapx_path, potfile_path):
    if not os.path.exists(potfile_path):
        return None
    with open(potfile_path, 'r') as f:
        for line in f:
            if hccapx_path in line:
                return line.split(':')[-1].strip()
    return None
def parse_crack_results(crack_output):
    """
    Parses the output of a hashcat cracking session.
    Returns a dictionary with the cracked key and any additional details.
    """
    results = {}
    for line in crack_output.splitlines():
        if line.startswith("Session"):
            continue  # Skip session header lines
        if line.startswith("All hashes processed"):
            continue  # Skip summary lines
        if ':' in line:
            parts = line.split(':', 1)
            results[parts[0].strip()] = parts[1].strip()
    return results if results else None
