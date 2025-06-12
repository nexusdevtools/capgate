# **Disclaimer**: This information is provided for educational and ethical purposes only. Unauthorized access to computer systems and networks is illegal and unethical. Always ensure you have explicit permission before performing any penetration testing or security assessments on networks you do not own or administer

-----

## Workflow: WPA2 Handshake Capture and Cracking with Aircrack-ng

This workflow will guide you through the process of putting your wireless card into monitor mode, scanning for target networks, deauthenticating a client to capture the 4-way handshake, and finally attempting to crack the password using a dictionary attack.

**Tools Used:** Aircrack-ng Suite (airmon-ng, airodump-ng, aireplay-ng, aircrack-ng)

**Prerequisites:**

* A compatible wireless adapter that supports **monitor mode** and **packet injection**. (Common chipsets like Atheros, Ralink, and some Realtek are generally good.)
* A Linux distribution (Kali Linux is recommended as it comes pre-installed with Aircrack-ng and necessary drivers).
* A wordlist for cracking (e.g., `rockyou.txt` or a custom list).

-----

### Phase 1: Preparation and Interface Setup

**Objective:** Get your wireless adapter ready for sniffing and injection by putting it into monitor mode.

**TTP (Tactics, Techniques, and Procedures):**

* **Tactic:** Reconnaissance / Initial Access
* **Technique:** Wireless Interface Configuration
* **Procedure:** Identify wireless interfaces, kill conflicting processes, enable monitor mode.

**Walkthrough:**

1. **Identify Wireless Interfaces:**

      * Open a terminal.
      * List your network interfaces to find your wireless adapter's name (e.g., `wlan0`, `wlan1`, `phy0`).

    <!-- end list -->

    ```bash
    # List all network interfaces
    ip a

    # Or specifically for wireless interfaces
    iwconfig
    ```

      * **Inline Documentation:** `ip a` displays all network interfaces and their configurations (IP addresses, MAC addresses). `iwconfig` specifically shows wireless interface details, including their mode (managed, monitor).

2. **Kill Conflicting Processes:**

      * Many services (like NetworkManager, wpa\_supplicant) can interfere with monitor mode. Aircrack-ng provides a utility to automatically kill these.

    <!-- end list -->

    ```bash
    # Kill processes that might interfere with monitor mode
    sudo airmon-ng check kill
    ```

      * **Inline Documentation:** `airmon-ng check kill` identifies and terminates processes that might prevent a wireless adapter from entering or operating correctly in monitor mode. This is crucial for stable operation.

3. **Put Adapter into Monitor Mode:**

      * Now, switch your identified wireless interface to monitor mode. Replace `<interface_name>` with your actual interface (e.g., `wlan0`).

    <!-- end list -->

    ```bash
    # Put the wireless interface into monitor mode
    sudo airmon-ng start <interface_name>
    ```

      * **Inline Documentation:** `airmon-ng start` takes a wireless interface as an argument and attempts to put it into monitor mode. It will often rename the interface (e.g., `wlan0` might become `wlan0mon` or `mon0`) to indicate it's in monitor mode. Note the new interface name, as you'll use it for subsequent steps.

4. **Verify Monitor Mode:**

      * Check if the interface is successfully in monitor mode.

    <!-- end list -->

    ```bash
    # Verify the interface is in monitor mode
    iwconfig
    ```

      * **Inline Documentation:** Confirm that the output for your wireless adapter now shows `Mode:Monitor`.

-----

#### Phase 2: Scanning for Target Networks

**Objective:** Discover nearby Wi-Fi networks, identify their BSSIDs (MAC addresses of APs), channels, and associated clients.

**TTP:**

* **Tactic:** Reconnaissance
* **Technique:** Passive Wireless Scanning
* **Procedure:** Use airodump-ng to capture beacon frames and probe responses to enumerate networks and clients.

**Walkthrough:**

1. **Start Scanning:**

      * Use `airodump-ng` on your monitor interface to start scanning. Replace `<monitor_interface_name>` with the name you got from `airmon-ng start` (e.g., `wlan0mon`, `mon0`).

    <!-- end list -->

    ```bash
    # Start scanning for networks and clients
    sudo airodump-ng <monitor_interface_name>
    ```

      * **Inline Documentation:** `airodump-ng` is a packet sniffer that captures raw 802.11 frames. It displays information about access points (BSSID, ESSID, channel, encryption type) and associated clients (station MAC, AP BSSID).

2. **Identify Target Network:**

      * Observe the output. Look for your target WPA2 network. Note down its:

          * **BSSID:** The MAC address of the Access Point.
          * **Channel (CH):** The channel it's operating on.
          * **ESSID:** The network name (SSID).

      * Also, look for any clients listed under the "STATION" section that are connected to your target BSSID. The presence of a client is crucial for deauthentication.

      * **Example Output (Partial):**

        ```txt
        CH  1  ][ Elapsed: 1 min ][ 2025-05-21 02:20

        BSSID              PWR RXQ  Beacons    #Data, #/s  CH  MB   ENC  CIPHER AUTH ESSID

        AA:BB:CC:DD:EE:FF  -50  90      120        5    0   6  54e  WPA2 CCMP   PSK  MyTargetWIFI
        00:11:22:33:44:55  -65  85       80        2    0   1  54e  WPA2 CCMP   PSK  AnotherNetwork

        BSSID              STATION            PWR   Rate    Lost    Frames  Probe

        AA:BB:CC:DD:EE:FF  11:22:33:44:55:66  -60   1 - 1     0       150
        ```

      * **Inline Documentation:** The `BSSID` is the unique identifier of the AP. `CH` indicates the frequency channel. The `STATION` section lists connected clients, with `BSSID` showing which AP they are connected to and `STATION` being the client's MAC address.

3. **Stop Scanning:**

      * Once you've identified your target, press `Ctrl+C` in the `airodump-ng` terminal.

-----

#### Phase 3: Targeted Handshake Capture

**Objective:** Capture the WPA2 4-way handshake by forcing a connected client to reauthenticate.

**TTP:**

* **Tactic:** Credential Access / Network Access
* **Technique:** Deauthentication Attack
* **Procedure:** Send deauthentication frames to a client, forcing a reconnect and capturing the handshake.

**Walkthrough:**

1. **Start Targeted Capture:**

      * You need to run `airodump-ng` again, but this time, focused on your target network's channel and saving the output to a file. This file will contain the captured handshake.
      * Replace `<monitor_interface_name>`, `<target_bssid>`, `<target_channel>`, and `<output_filename>` with your values.

    <!-- end list -->

    ```bash
    # Start capturing packets on the target channel and save to a file
    sudo airodump-ng --bssid <target_bssid> --channel <target_channel> --write <output_filename> <monitor_interface_name>
    ```

      * **Inline Documentation:** `--bssid` filters traffic to a specific AP. `--channel` sets the adapter to a fixed channel, improving capture efficiency. `--write` specifies a prefix for the output files (`.cap`, `.csv`, etc.) where the captured packets will be stored. The `.cap` file is essential for handshake cracking.

2. **Perform Deauthentication Attack (in a new terminal):**

      * Open a **new terminal window**. This is crucial because `airodump-ng` needs to keep running in the first terminal to capture the handshake.

      * Send deauthentication frames to the target client. You can send it to a specific client (recommended if one is identified) or broadcast it to all clients connected to the AP.

      * **Option A: Deauthenticate a Specific Client (Recommended if available)**

          * Replace `<deauth_count>` (e.g., `5` or `10` to send multiple deauth packets), `<target_bssid>`, `<client_mac_address>`, and `<monitor_interface_name>`.

        <!-- end list -->

        ```bash
        # Send deauthentication packets to a specific client
        sudo aireplay-ng --deauth <deauth_count> -a <target_bssid> -c <client_mac_address> <monitor_interface_name>
        ```

          * **Inline Documentation:** `aireplay-ng` is used for injecting and replaying packets. `--deauth` performs a deauthentication attack. `-a` specifies the AP's BSSID. `-c` specifies the client's MAC address. Targeting a specific client is often more effective and less disruptive than a broadcast deauth.

      * **Option B: Broadcast Deauthentication (If no specific client is found, less effective against PMF)**

          * Replace `<deauth_count>`, `<target_bssid>`, and `<monitor_interface_name>`.

        <!-- end list -->

        ```bash
        # Send broadcast deauthentication packets to all clients of the AP
        sudo aireplay-ng --deauth <deauth_count> -a <target_bssid> <monitor_interface_name>
        ```

          * **Inline Documentation:** This method sends deauth packets to the broadcast address, aiming to disconnect all clients. However, due to Protected Management Frames (PMF) on modern networks, this can be less reliable than targeting a specific client.

3. **Monitor for Handshake:**

      * Switch back to the first terminal where `airodump-ng` is running.
      * Look for the `[ WPA Handshake: <AP_BSSID> ]` message in the top right corner of the `airodump-ng` output. This indicates a successful handshake capture.
      * **Inline Documentation:** The presence of `[ WPA Handshake: <AP_BSSID> ]` confirms that a 4-way handshake containing the necessary challenge/response for cracking has been captured and saved to your `.cap` file.

4. **Stop Capture:**

      * Once the handshake is captured, press `Ctrl+C` in the `airodump-ng` terminal.
      * Stop the `aireplay-ng` command in the second terminal (if it's still running) with `Ctrl+C`.

-----

#### Phase 4: Cracking the WPA2 Handshake

**Objective:** Attempt to recover the WPA2 passphrase using a dictionary attack against the captured handshake.

**TTP:**

* **Tactic:** Credential Access
* **Technique:** Password Cracking (Dictionary Attack)
* **Procedure:** Use aircrack-ng with a wordlist to attempt to deduce the PSK from the captured 4-way handshake.

**Walkthrough:**

1. **Choose a Wordlist:**

      * Ensure you have a good wordlist. `rockyou.txt` (often located at `/usr/share/wordlists/rockyou.txt.gz` and needs to be unzipped) is a common starting point.
      * For unzipping `rockyou.txt.gz`:

        ```bash
        sudo gunzip /usr/share/wordlists/rockyou.txt.gz
        ```

      * **Inline Documentation:** The quality and comprehensiveness of your wordlist are the single most important factors for WPA2 cracking success. If the password isn't in your wordlist, it cannot be cracked this way.

2. **Start Cracking:**

      * Use `aircrack-ng` to attempt to crack the handshake. Replace `<output_filename-01.cap>` with the actual name of your `.cap` file (e.g., `mycapture-01.cap`) and `<path_to_wordlist>` with the path to your dictionary file.

    <!-- end list -->

    ```bash
    # Crack the WPA2 handshake using a dictionary attack
    sudo aircrack-ng -w <path_to_wordlist> <output_filename-01.cap>
    ```

      * **Inline Documentation:** `aircrack-ng` is the main cracking utility. `-w` specifies the path to the wordlist file. It will iterate through each word in the dictionary, compute the Pairwise Master Key (PMK) for each, and compare it against the captured handshake.

3. **Monitor Cracking Progress:**

      * `aircrack-ng` will show you the cracking progress (keys tested per second, percentage complete).
      * If a match is found, it will display the `KEY FOUND!` message and the passphrase.
      * **Inline Documentation:** The cracking process can take anywhere from seconds to hours or even days, depending on the complexity of the password and the size/quality of your wordlist.

-----

#### Phase 5: Cleanup

**Objective:** Return your wireless adapter to its normal operating mode.

**TTP:**

* **Tactic:** Post-Exploitation / Clean-up
* **Technique:** Wireless Interface Configuration
* **Procedure:** Disable monitor mode and restart network services.

**Walkthrough:**

1. **Stop Monitor Mode:**

      * Switch your adapter back to managed mode. Replace `<monitor_interface_name>` with the name of your monitor interface.

    <!-- end list -->

    ```bash
    # Stop monitor mode on the wireless interface
    sudo airmon-ng stop <monitor_interface_name>
    ```

      * **Inline Documentation:** `airmon-ng stop` returns the specified interface from monitor mode back to managed mode.

2. **Restart Network Services:**

      * Restart NetworkManager or other relevant network services to regain normal network connectivity.

    <!-- end list -->

    ```bash
    # Restart NetworkManager (common for most Linux desktops)
    sudo systemctl start NetworkManager

    # Or if you're using a different service or need to be general:
    sudo systemctl restart networking
    ```

      * **Inline Documentation:** Restarting NetworkManager or the networking service ensures that your system can now properly connect to Wi-Fi networks in its standard operating mode.

-----

This comprehensive workflow with inline documentation and TTPs should provide a clear and effective guide for using the Aircrack-ng suite for WPA2 handshake capture and cracking. Remember to always operate ethically and within legal boundaries.
