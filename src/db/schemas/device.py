from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class Device(BaseModel):
    mac: str
    ip: Optional[str] = None
    hostname: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    model: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    product_name: Optional[str] = None
    product_id: Optional[str] = None
    product_url: Optional[str] = None
    product_description: Optional[str] = None
    product_image: Optional[str] = None
    product_category: Optional[str] = None
    product_subcategory: Optional[str] = None
    product_tags: Optional[list[str]] = None
    product_features: Optional[list[str]] = None
    product_specs: Optional[dict[str, Any]] = None
    product_manual: Optional[str] = None
    product_support_url: Optional[str] = None
    product_support_email: Optional[str] = None
    product_support_phone: Optional[str] = None
    product_support_hours: Optional[str] = None
    product_release_date: Optional[str] = None
    product_discontinued: Optional[bool] = None
    product_warranty: Optional[str] = None
    product_certifications: Optional[list[str]] = None
    product_compliance: Optional[list[str]] = None
    product_compatibility: Optional[list[str]] = None
    product_accessories: Optional[list[str]] = None
    product_related: Optional[list[str]] = None
    product_resources: Optional[list[str]] = None
    product_notes: Optional[str] = None
    product_custom_fields: Optional[dict[str, Any]] = None
    product_custom_tags: Optional[list[str]] = None
    vendor: Optional[str] = None
    signal_strength: Optional[int] = None
    is_router: bool = False
    last_seen: Optional[float] = None # Timestamp (float)
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
    is_unknown: bool = False
    is_custom: bool = False

    model_config = ConfigDict(extra='allow')

    def to_dict(self) -> dict[str, Any]:
        """Converts the Device model instance to a dictionary, excluding unset/None values."""
        # Use model_dump for Pydantic v2. `exclude_none=True` is typically default for `dict()` if Optional
        # fields are not provided, but explicitly stating it is good.
        return self.model_dump(exclude_none=True)