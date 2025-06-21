# capgate/db/schemas/device.py
from pydantic import BaseModel
from typing import Optional
import time

class Device(BaseModel):
    mac: str
    vendor: Optional[str] = None
    signal_strength: Optional[int] = None
    is_router: bool = False
    last_seen: Optional[float] = None
    is_active: bool = True
    is_tracked: bool = False
    is_ignored: bool = False
    is_blocked: bool = False
    is_whitelisted: bool = False
    is_blacklisted: bool = False
    is_suspicious: bool = False
    is_known: bool = False
    is_new: bool = True
    is_rogue: bool = False
    is_hidden: bool = False
    is_guest: bool = False
    is_persistent: bool = False
    is_critical: bool = False
    is_vulnerable: bool = False
    is_exploited: bool = False
    is_compromised: bool = False
    is_malicious: bool = False
    is_anomalous: bool = False
    is_inactive: bool = False
    is_offline: bool = False
    is_online: bool = True
    is_connected: bool = True
    is_disconnected: bool = False
    is_authenticated: bool = False
    is_deauthenticated: bool = False
    is_roaming: bool = False
    is_station: bool = False
    is_ap: bool = False
    is_client: bool = False
    is_server: bool = False
    is_bridge: bool = False
    is_repeater: bool = False
    is_gateway: bool = False
    is_switch: bool = False
    is_router_mode: bool = False
    is_access_point: bool = False
    is_mesh_node: bool = False
    is_iot_device: bool = False
    is_smart_device: bool = False
    is_printer: bool = False
    is_camera: bool = False
    is_speaker: bool = False
    is_tv: bool = False
    is_laptop: bool = False
    is_desktop: bool = False
    is_mobile: bool = False
    is_tablet: bool = False
    is_wearable: bool = False
    is_vehicle: bool = False
    is_unknown: bool = False # Catch-all for any device not classified
    is_custom: bool = False  # For user-defined device types