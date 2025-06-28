# Evil Twin Rogue AP Attack Plugin

## Overview

The `evil_twin` plugin is a powerful CapGate module designed to automate and orchestrate a sophisticated rogue Access Point (AP) attack. It impersonates a legitimate Wi-Fi network, captures client credentials, and provides a framework for advanced Wi-Fi penetration testing.

Leveraging CapGate's modular design and core assets (like `APManager`, `DhcpDnsManager`, `TrafficRedirector`, `WebServerManager`, `CredentialVerifier`), this plugin goes beyond traditional Evil Twin tools by providing an intelligent, integrated, and extensible attack platform.

## How it Works

The plugin follows a multi-stage process to execute the Evil Twin attack:

1. **Interface Selection & Setup:** Identifies and configures appropriate wireless interfaces for each role (Rogue AP, Deauthentication, Verification).
2. **Target AP Scan:** Scans for and selects a legitimate Wi-Fi Access Point to impersonate.
3. **Infrastructure Spin-up:**
    * Starts a **Rogue AP** using `hostapd`.
    * Configures **DHCP and DNS services** using `dnsmasq` to assign IP addresses and redirect DNS requests to the attacker's web server.
    * Sets up **traffic redirection rules** using `iptables` to intercept HTTP/HTTPS traffic and route it to the rogue web server, while enabling NAT for internet access (if configured).
    * Launches a **Flask web server** to host a fake router login page and spoof connectivity check domains.
4. **Client Deauthentication:** Continuously deauthenticates clients from the legitimate AP to force them to connect to the Evil Twin.
5. **Credential Capture:** Clients connecting to the Evil Twin are presented with a fake login page. Submitted credentials are captured and logged.
6. **Credential Verification (Optional):** Captured credentials can be automatically verified against the legitimate AP.
7. **Cleanup:** All deployed services (`hostapd`, `dnsmasq`, web server, `iptables` rules) are gracefully shut down, and interfaces are returned to their original states.

## Prerequisites

To successfully run the `evil_twin` plugin, ensure the following are met:

1. **Root Privileges:**
    * The plugin requires root privileges (`sudo`) to manage network interfaces, configure kernel parameters (`iptables`, `sysctl`), and run underlying tools (`hostapd`, `dnsmasq`, `aircrack-ng` suite, `nmcli`).
    * **Always run `capgate` with `sudo` for this plugin, or ensure your user has appropriate `CAP_NET_ADMIN` capabilities set.**
    * Example: `sudo capgate run evil_twin --auto`

2. **Wireless Cards:**
    * **Minimum (2 Recommended):** You should ideally have at least **two** wireless network adapters.
        * One capable of **AP mode** (for hosting the Rogue AP).
        * One capable of **monitor mode** (for sending deauthentication packets).
    * **Ideal (3 for Full Functionality):** For the most robust and stable attack, **three** wireless cards are recommended:
        * One for the **Rogue AP** (`--ap-iface`).
        * One for **Deauthentication** (`--deauth-iface`).
        * One for **Credential Verification** (managed mode capable, able to reconnect to the real network for verification via `--verify-iface`).
    * If fewer cards are available, the plugin may attempt to reuse interfaces, which can lead to instability or reduced effectiveness.

3. **Installed Tools:**
    Ensure the following command-line tools are installed on your system and are available in your system's PATH:
    * `hostapd`
    * `dnsmasq`
    * `aircrack-ng` suite (`airodump-ng`, `aireplay-ng`, `aircrack-ng`)
    * `nmcli` (NetworkManager CLI)

4. **Web Assets:**
    * Ensure the fake login page templates (`index.html`, connectivity responses like `hotspot-detect.html`, `ncsi.txt`, `generate_204`, `connecttest.txt`) are present in `src/web_assets/templates`.
    * If using a custom login endpoint (e.g., `/cgi-bin/login.py`), ensure `src/web_assets/cgi-bin/login.py` exists (though the Flask app handles this endpoint directly).

## CLI Arguments

The `evil_twin` plugin accepts the following command-line arguments to customize its behavior. These are passed after the plugin name in the `capgate run` command.

| Argument          | Type     | Required? | Description                                                                                                                                                                                                                                                                                       |
| :---------------- | :------- | :-------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--target-bssid`  | `str`    | No        | The BSSID (MAC address) of the legitimate Access Point (AP) you want to clone (e.g., `AA:BB:CC:DD:EE:FF`).                                                                                                                                                                         |
| `--target-ssid`   | `str`    | No        | The SSID (name) of the legitimate AP you want to clone.                                                                                                                                                                                                                           |
| `--target-channel`| `int`    | No        | The channel of the legitimate AP to clone.                                                                                                                                                                                                                                          |
| `--ap-iface`      | `str`    | No        | The name of the wireless interface to use for **hosting the Evil Twin Access Point** (e.g., `wlan0`).                                                                                                                                                                                 |
| `--deauth-iface`  | `str`    | No        | The name of the wireless interface to use for **sending deauthentication packets** to clients of the real AP (e.g., `wlan1`).                                                                                                                                                       |
| `--verify-iface`  | `str`    | No        | The name of the wireless interface to use for **verifying captured credentials** against the real AP (e.g., `wlan2`).                                                                                                                                                                 |
| `--internet-iface`| `str`    | No        | The name of the **internet-facing interface** on your system (e.g., `eth0`). This is used for traffic masquerading/NAT so clients redirected to your Evil Twin can still access the internet (if desired).                                                                               |
| `--auto-select`   | `flag`   | No        | Use as a flag (`--auto-select`). If set, the plugin will attempt to automatically select interfaces and a target AP from scan results without user prompts. **Highly recommended for initial testing or scripted runs.** |

**Important Notes on Interface Arguments:**

* **Capabilities:** The interfaces specified for `--ap-iface`, `--deauth-iface`, and `--verify-iface` must support the required wireless modes (AP mode, monitor mode, and managed mode, respectively). CapGate will verify `AppState` for these capabilities.
* **Physical Separation:** For optimal stability and effectiveness of the attack, it is strongly recommended to use physically *different* wireless network adapters for each role if you have them. The plugin will attempt to pick distinct interfaces, but will reuse if necessary.
* **Initial State:** Ensure the chosen interfaces are in a clean, inactive state (e.g., not already connected to a network, or not already in monitor mode if intended for AP mode) before running the plugin. While CapGate attempts to manage interface states, a clean starting state minimizes potential conflicts.

## Example Usage Scenarios

Here are common ways to run the `evil_twin` plugin:

1. **Fully Automated Run (Recommended for initial tests and quick deployment):**
    The plugin will automatically select interfaces based on capabilities and choose a target AP from scan results without user interaction.

    ```bash
    sudo capgate run evil_twin --auto-select
    ```

2. **Target a Specific AP (Interfaces Auto-selected):**
    You explicitly define the target AP (BSSID, SSID, Channel), and CapGate will automatically select suitable interfaces.

    ```bash
    sudo capgate run evil_twin --target-bssid "AA:BB:CC:DD:EE:FF" --target-ssid "MyHomeWifi" --target-channel 6 --auto-select
    ```

3. **Manual Interface Selection (Interactive Target Selection):**
    You specify which interfaces to use for each role, but interactively choose the target AP from the scan results.

    ```bash
    sudo capgate run evil_twin --ap-iface wlan0 --deauth-iface wlan1 --verify-iface wlan2
    ```

4. **Full Manual Control:**
    You provide all details explicitly, including target AP and all interface assignments.

    ```bash
    sudo capgate run evil_twin --target-bssid "AA:BB:CC:DD:EE:FF" --target-ssid "MyHomeWifi" --target-channel 6 \
        --ap-iface wlan0 --deauth-iface wlan1 --verify-iface wlan2 --internet-iface eth0
    ```

## Attack Flow During Execution

When the `evil_twin` plugin runs, it performs the following high-level steps:

1. **Interface Setup:** Configures the selected interfaces into their required modes (AP mode, Monitor mode, Managed mode).
2. **Infrastructure Spin-up:**
    * Starts `hostapd` to broadcast the cloned AP.
    * Launches `dnsmasq` to provide DHCP leases and redirect DNS queries to the rogue web server.
    * Applies `iptables` rules to intercept HTTP/HTTPS traffic and perform network address translation (NAT).
    * Starts the Flask web server to host the fake login page and spoof internet connectivity checks.
3. **Client Deauthentication:** Uses `aireplay-ng` (or similar) to continuously deauthenticate clients from the legitimate AP, encouraging them to connect to your Evil Twin.
4. **Credential Capture:** If a client connects to your Evil Twin and attempts to log in on the fake page, their submitted username and password will be captured and written to `data/captured_credentials.jsonl`.
5. **Verification (if configured):** The plugin attempts to verify the captured credentials against the real Access Point using a separate wireless interface.
6. **Comprehensive Cleanup:** All deployed services (`hostapd`, `dnsmasq`, web server) are gracefully shut down, `iptables` rules are cleared, and interfaces are returned to their original states (or to NetworkManager management).

This plugin aims to provide a robust, automated, and extensible platform for advanced Wi-Fi attacks within CapGate.
