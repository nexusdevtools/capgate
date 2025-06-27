from typing import Optional, List # Import List
from pydantic import BaseModel, ConfigDict # Import ConfigDict

class Interface(BaseModel):
    name: str
    mac: str
    is_up: bool = False # Added to represent interface state (UP/DOWN/NO-CARRIER)
    ip_address: Optional[str] = None # Added to represent CIDR IP (e.g., "192.168.1.10/24")
    mode: Optional[str] = "managed"  # managed / monitor / AP / P2P-client, etc.
    driver: Optional[str] = None
    phy_name: Optional[str] = None # e.g., phy0, for wireless interfaces
    ssid: Optional[str] = None # For managed mode
    tx_power: Optional[str] = None # e.g., "22.00 dBm"
    channel_frequency: Optional[str] = None # e.g., "5720 MHz (channel 144), width 40 MHz"
    signal_quality: Optional[int] = None # You had this, leaving it. Maybe SNR or Link quality.

    # CRITICAL ADDITION: Add the is_wireless field
    is_wireless: bool = False 

    # CRITICAL ADDITION: Add the supported_modes_list field
    supported_modes_list: List[str] = []

    # Flags for capabilities, kept from your original.
    # Note: Consider making these a List[str] like `supported_modes_list: List[str]`
    # and parsing `iw list` to populate it more dynamically,
    # rather than having hundreds of booleans. For now, matching your original.
    supports_monitor: bool = False
    supports_managed: bool = True
    supports_ap: bool = False
    supports_mesh: bool = False
    supports_p2p: bool = False
    supports_adhoc: bool = False
    supports_wds: bool = False
    supports_vap: bool = False
    supports_tdma: bool = False
    supports_mimo: bool = False
    supports_5ghz: bool = False
    supports_6ghz: bool = False
    supports_2ghz: bool = True
    supports_11ax: bool = False
    supports_11ac: bool = False
    supports_11n: bool = True
    supports_11g: bool = True
    supports_11b: bool = True
    supports_11a: bool = True
    supports_11ad: bool = False
    supports_11be: bool = False
    supports_11bf: bool = False
    supports_11ah: bool = False
    supports_11ai: bool = False # 11ai is for Wi-Fi EasyMesh
    # ... (all your other supports_11ax_heXXXX fields) ...
    supports_11ax_eht: bool = False
    supports_11ax_he: bool = False
    supports_11ax_he80: bool = False
    supports_11ax_he160: bool = False
    supports_11ax_he240: bool = False
    supports_11ax_he320: bool = False
    supports_11ax_he480: bool = False
    supports_11ax_he640: bool = False
    supports_11ax_he960: bool = False
    supports_11ax_he1280: bool = False
    supports_11ax_he1600: bool = False
    supports_11ax_he1920: bool = False
    supports_11ax_he2240: bool = False
    supports_11ax_he2560: bool = False
    supports_11ax_he2880: bool = False
    supports_11ax_he3200: bool = False
    supports_11ax_he3520: bool = False
    supports_11ax_he3840: bool = False
    supports_11ax_he4160: bool = False
    supports_11ax_he4480: bool = False
    supports_11ax_he4800: bool = False
    supports_11ax_he5120: bool = False
    supports_11ax_he5440: bool = False
    supports_11ax_he5760: bool = False
    supports_11ax_he6080: bool = False
    supports_11ax_he6400: bool = False
    supports_11ax_he6720: bool = False
    supports_11ax_he7040: bool = False
    supports_11ax_he7360: bool = False
    supports_11ax_he7680: bool = False
    supports_11ax_he8000: bool = False
    supports_11ax_he8320: bool = False
    supports_11ax_he8640: bool = False
    supports_11ax_he8960: bool = False
    supports_11ax_he9280: bool = False
    supports_11ax_he9600: bool = False
    supports_11ax_he9920: bool = False
    supports_11ax_he10240: bool = False
    supports_11ax_he10560: bool = False
    supports_11ax_he10880: bool = False
    supports_11ax_he11200: bool = False
    supports_11ax_he11520: bool = False
    supports_11ax_he11840: bool = False
    supports_11ax_he12160: bool = False
    supports_11ax_he12480: bool = False
    supports_11ax_he12800: bool = False
    supports_11ax_he13120: bool = False
    supports_11ax_he13440: bool = False
    supports_11ax_he13760: bool = False
    supports_11ax_he14080: bool = False
    supports_11ax_he14400: bool = False
    supports_11ax_he14720: bool = False
    supports_11ax_he15040: bool = False
    supports_11ax_he15360: bool = False
    supports_11ax_he15680: bool = False
    supports_11ax_he16000: bool = False
    supports_11ax_he16320: bool = False
    supports_11ax_he16640: bool = False
    supports_11ax_he16960: bool = False
    supports_11ax_he17280: bool = False
    supports_11ax_he17600: bool = False
    supports_11ax_he17920: bool = False
    supports_11ax_he18240: bool = False
    supports_11ax_he18560: bool = False
    supports_11ax_he18880: bool = False
    supports_11ax_he19200: bool = False
    supports_11ax_he19520: bool = False
    supports_11ax_he19840: bool = False
    supports_11ax_he20160: bool = False
    supports_11ax_he20480: bool = False
    supports_11ax_he20800: bool = False
    supports_11ax_he21120: bool = False
    supports_11ax_he21440: bool = False
    supports_11ax_he21760: bool = False
    supports_11ax_he22080: bool = False
    supports_11ax_he22400: bool = False
    supports_11ax_he22720: bool = False
    supports_11ax_he23040: bool = False
    supports_11ax_he23360: bool = False
    supports_11ax_he23680: bool = False
    supports_11ax_he24000: bool = False
    supports_11ax_he24320: bool = False
    supports_11ax_he24640: bool = False
    supports_11ax_he24960: bool = False
    supports_11ax_he25280: bool = False
    supports_11ax_he25600: bool = False
    supports_11ax_he25920: bool = False
    supports_11ax_he26240: bool = False
    supports_11ax_he26560: bool = False
    supports_11ax_he26880: bool = False
    supports_11ax_he27200: bool = False
    supports_11ax_he27520: bool = False
    supports_11ax_he27840: bool = False
    supports_11ax_he28160: bool = False
    supports_11ax_he28480: bool = False
    supports_11ax_he28800: bool = False
    supports_11ax_he29120: bool = False
    supports_11ax_he29440: bool = False
    supports_11ax_he29760: bool = False
    supports_11ax_he30080: bool = False
    supports_11ax_he30400: bool = False
    supports_11ax_he30720: bool = False
    supports_11ax_he31040: bool = False
    supports_11ax_he31360: bool = False
    supports_11ax_he31680: bool = False
    supports_11ax_he32000: bool = False
    supports_11ax_he32320: bool = False
    supports_11ax_he32640: bool = False
    supports_11ax_he32960: bool = False
    supports_11ax_he33280: bool = False
    supports_11ax_he33600: bool = False
    supports_11ax_he33920: bool = False
    supports_11ax_he34240: bool = False
    supports_11ax_he34560: bool = False
    supports_11ax_he34880: bool = False
    supports_11ax_he35200: bool = False
    supports_11ax_he35520: bool = False
    supports_11ax_he35840: bool = False
    supports_11ax_he36160: bool = False
    supports_11ax_he36480: bool = False
    supports_11ax_he36800: bool = False
    supports_11ax_he37120: bool = False
    supports_11ax_he37440: bool = False
    supports_11ax_he37760: bool = False
    supports_11ax_he38080: bool = False
    supports_11ax_he38400: bool = False
    supports_11ax_he38720: bool = False
    supports_11ax_he39040: bool = False
    supports_11ax_he39360: bool = False
    supports_11ax_he39680: bool = False
    supports_11ax_he40000: bool = False
    supports_11ax_he40320: bool = False
    supports_11ax_he40640: bool = False
    supports_11ax_he40960: bool = False
    supports_11ax_he41280: bool = False
    supports_11ax_he41600: bool = False


    model_config = ConfigDict(extra='allow')

    def to_dict(self) -> dict[str, object]:
        """Converts the Interface model instance to a dictionary, excluding unset/None values."""
        return self.model_dump(exclude_none=True)

    def supports_monitor_mode(self) -> bool:
        """Indicates if the interface supports monitor mode."""
        return self.supports_monitor