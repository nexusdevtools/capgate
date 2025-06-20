# capgate/types/db/schemas/device_types.py

from typing import TypedDict, Optional


class DeviceSchema(TypedDict, total=False):
    mac: str
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: bool
    last_seen: float
    is_active: bool
    is_tracked: bool
    is_ignored: bool
    is_blocked: bool
    is_whitelisted: bool
    is_blacklisted: bool
    is_suspicious: bool
    is_known: bool
    is_new: bool
    is_rogue: bool
    is_hidden: bool
    is_guest: bool
    is_persistent: bool
    is_critical: bool
    is_vulnerable: bool
    is_exploited: bool
    is_compromised: bool
    is_malicious: bool
    is_anomalous: bool
    is_inactive: bool
    is_offline: bool
    is_online: bool
    is_connected: bool
    is_disconnected: bool
    is_authenticated: bool
    is_deauthenticated: bool
    is_roaming: bool
    is_station: bool
    is_ap: bool
    is_client: bool
    is_server: bool
    is_bridge: bool
    is_repeater: bool
    is_gateway: bool
    is_switch: bool
    is_router_mode: bool
    is_access_point: bool
    is_mesh_node: bool
    is_iot_device: bool
    is_smart_device: bool
    is_printer: bool
    is_camera: bool
    is_speaker: bool
    is_tv: bool
    is_laptop: bool
    is_desktop: bool
    is_mobile: bool
    is_tablet: bool
    is_wearable: bool
    is_vehicle: bool

class DeviceUpdateSchema(TypedDict, total=False):
    mac: Optional[str]
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: Optional[bool]
    last_seen: Optional[float]
    is_active: Optional[bool]
    is_tracked: Optional[bool]
    is_ignored: Optional[bool]
    is_blocked: Optional[bool]
    is_whitelisted: Optional[bool]
    is_blacklisted: Optional[bool]
    is_suspicious: Optional[bool]
    is_known: Optional[bool]
    is_new: Optional[bool]
    is_rogue: Optional[bool]
    is_hidden: Optional[bool]
    is_guest: Optional[bool]
    is_persistent: Optional[bool]
    is_critical: Optional[bool]
    is_vulnerable: Optional[bool]
    is_exploited: Optional[bool]
    is_compromised: Optional[bool]
    is_malicious: Optional[bool]
    is_anomalous: Optional[bool]
    is_inactive: Optional[bool]
    is_offline: Optional[bool]
    is_online: Optional[bool]
    is_connected: Optional[bool]
    is_disconnected: Optional[bool]
    is_authenticated: Optional[bool]
    is_deauthenticated: Optional[bool]
    is_roaming: Optional[bool]
    is_station: Optional[bool]
    is_ap: Optional[bool]
    is_client: Optional[bool]
    is_server: Optional[bool]
    is_bridge: Optional[bool]
    is_repeater: Optional[bool]
    is_gateway: Optional[bool]
    is_switch: Optional[bool]
    is_router_mode: Optional[bool]
    is_access_point: Optional[bool]
    is_mesh_node: Optional[bool]
    is_iot_device: Optional[bool]
    is_smart_device: Optional[bool]
    is_printer: Optional[bool]
    is_camera: Optional[bool]
    is_speaker: Optional[bool]
    is_tv: Optional[bool]
    is_laptop: Optional[bool]
    is_desktop: Optional[bool]
    is_mobile: Optional[bool]
    is_tablet: Optional[bool]
    is_wearable: Optional[bool]
    is_vehicle: Optional[bool]

class DeviceCreateSchema(TypedDict, total=False):
    mac: str
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: bool
    last_seen: float
    is_active: bool
    is_tracked: bool
    is_ignored: bool
    is_blocked: bool
    is_whitelisted: bool
    is_blacklisted: bool
    is_suspicious: bool
    is_known: bool
    is_new: bool
    is_rogue: bool
    is_hidden: bool
    is_guest: bool
    is_persistent: bool
    is_critical: bool
    is_vulnerable: bool
    is_exploited: bool
    is_compromised: bool
    is_malicious: bool
    is_anomalous: bool
    is_inactive: bool
    is_offline: bool
    is_online: bool
    is_connected: bool
    is_disconnected: bool
    is_authenticated: bool
    is_deauthenticated: bool
    is_roaming: bool
    is_station: bool
    is_ap: bool
    is_client: bool
    is_server: bool
    is_bridge: bool
    is_repeater: bool
    is_gateway: bool
    is_switch: bool
    is_router_mode: bool
    is_access_point: bool
    is_mesh_node: bool
    is_iot_device: bool
    is_smart_device: bool
    is_printer: bool
    is_camera: bool
    is_speaker: bool
    is_tv: bool
    is_laptop: bool
    is_desktop: bool
    is_mobile: bool
    is_tablet: bool
    is_wearable: bool
    is_vehicle: bool

class DeviceDeleteSchema(TypedDict, total=False):
    mac: str
    is_active: Optional[bool]  # To mark as deleted without removing from DB

class DeviceFilterSchema(TypedDict, total=False):
    mac: Optional[str]
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: Optional[bool]
    last_seen: Optional[float]
    is_active: Optional[bool]
    is_tracked: Optional[bool]
    is_ignored: Optional[bool]
    is_blocked: Optional[bool]
    is_whitelisted: Optional[bool]
    is_blacklisted: Optional[bool]
    is_suspicious: Optional[bool]
    is_known: Optional[bool]
    is_new: Optional[bool]
    is_rogue: Optional[bool]
    is_hidden: Optional[bool]
    is_guest: Optional[bool]
    is_persistent: Optional[bool]
    is_critical: Optional[bool]
    is_vulnerable: Optional[bool]
    is_exploited: Optional[bool]
    is_compromised: Optional[bool]
    is_malicious: Optional[bool]
    is_anomalous: Optional[bool]
    is_inactive: Optional[bool]
    is_offline: Optional[bool]
    is_online: Optional[bool]
    is_connected: Optional[bool]
    is_disconnected: Optional[bool]
    is_authenticated: Optional[bool]
    is_deauthenticated: Optional[bool]
    is_roaming: Optional[bool]
    is_station: Optional[bool]
    is_ap: Optional[bool]
    is_client: Optional[bool]
    is_server: Optional[bool]
    is_bridge: Optional[bool]
    is_repeater: Optional[bool]
    is_gateway: Optional[bool]
    is_switch: Optional[bool]
    is_router_mode: Optional[bool]
    is_access_point: Optional[bool]
    is_mesh_node: Optional[bool]
    is_iot_device: Optional[bool]
    is_smart_device: Optional[bool]
    is_printer: Optional[bool]
    is_camera: Optional[bool]
    is_speaker: Optional[bool]
    is_tv: Optional[bool]
    is_laptop: Optional[bool]
    is_desktop: Optional[bool]
    is_mobile: Optional[bool]
    is_tablet: Optional[bool]
    is_wearable: Optional[bool]
    is_vehicle: Optional[bool]

class DeviceListSchema(TypedDict, total=False):
    devices: list[DeviceSchema]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters: DeviceFilterSchema  # Optional filters applied to the list
    sort_by: Optional[str]  # Field to sort by, e.g., "last_seen"
    sort_order: Optional[str]  # "asc" or "desc"

class DeviceStatsSchema(TypedDict, total=False):
    total_devices: int
    active_devices: int
    inactive_devices: int
    rogue_devices: int
    suspicious_devices: int
    blocked_devices: int
    whitelisted_devices: int
    blacklisted_devices: int
    critical_devices: int
    vulnerable_devices: int
    compromised_devices: int
    malicious_devices: int
    anomalous_devices: int
    last_updated: float  # Timestamp of the last update to the stats

class DeviceEventSchema(TypedDict, total=False):
    timestamp: float
    type: str  # e.g., "device_created", "device_updated", "device_deleted"
    device: DeviceSchema  # The device involved in the event
    source: Optional[str]  # Source of the event, e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class DeviceEventLogSchema(TypedDict, total=False):
    events: list[DeviceEventSchema]  # List of device events
    total_count: int  # Total number of events in the log
    page: int  # Current page number
    page_size: int  # Number of events per page
    total_pages: int  # Total number of pages available
    filters: DeviceFilterSchema  # Optional filters applied to the event log
    sort_by: Optional[str]  # Field to sort by, e.g., "timestamp"
    sort_order: Optional[str]  # "asc" or "desc"

class DeviceSearchSchema(TypedDict, total=False):   
    query: str  # Search query string
    filters: DeviceFilterSchema  # Optional filters to apply to the search
    sort_by: Optional[str]  # Field to sort by, e.g., "last_seen"
    sort_order: Optional[str]  # "asc" or "desc"
    page: int  # Current page number for pagination
    page_size: int  # Number of results per page
    total_count: int  # Total number of results found
    total_pages: int  # Total number of pages available

class DeviceScanResultSchema(TypedDict, total=False):
    devices: list[DeviceSchema]  # List of devices found during the scan
    total_count: int  # Total number of devices found
    scan_duration: float  # Duration of the scan in seconds
    timestamp: float  # When the scan was performed
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class DeviceScanSummarySchema(TypedDict, total=False):
    total_devices: int  # Total number of devices found during the scan
    active_devices: int  # Number of active devices
    inactive_devices: int  # Number of inactive devices
    rogue_devices: int  # Number of rogue devices
    suspicious_devices: int  # Number of suspicious devices
    blocked_devices: int  # Number of blocked devices
    whitelisted_devices: int  # Number of whitelisted devices
    blacklisted_devices: int  # Number of blacklisted devices
    critical_devices: int  # Number of critical devices
    vulnerable_devices: int  # Number of vulnerable devices
    compromised_devices: int  # Number of compromised devices
    malicious_devices: int  # Number of malicious devices
    anomalous_devices: int  # Number of anomalous devices
    scan_duration: float  # Duration of the scan in seconds
    timestamp: float  # When the summary was generated
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"

class DeviceScanErrorSchema(TypedDict, total=False):
    error_type: str  # e.g., "DeviceScanError"
    message: str  # Description of the error
    timestamp: float  # When the error occurred
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class DeviceScanConfigSchema(TypedDict, total=False):
    scan_interval: int  # Interval between scans in seconds
    scan_timeout: int  # Timeout for each scan in seconds
    include_hidden: bool  # Whether to include hidden devices
    include_inactive: bool  # Whether to include inactive devices
    include_rogue: bool  # Whether to include rogue devices
    include_suspicious: bool  # Whether to include suspicious devices
    filters: DeviceFilterSchema  # Optional filters to apply during the scan
    sort_by: Optional[str]  # Field to sort by, e.g., "last_seen"
    sort_order: Optional[str]  # "asc" or "desc"

class DeviceScanOptionsSchema(TypedDict, total=False):
    include_hidden: bool  # Whether to include hidden devices
    include_inactive: bool  # Whether to include inactive devices
    include_rogue: bool  # Whether to include rogue devices
    include_suspicious: bool  # Whether to include suspicious devices
    timeout: int  # Timeout for the scan in seconds
    page: int  # Current page number for pagination
    page_size: int  # Number of results per page
    total_count: int  # Total number of results found
    total_pages: int  # Total number of pages available

class DeviceScanFilterSchema(TypedDict, total=False):
    device_type: Optional[str]  # Filter by device type, e.g., "laptop", "mobile"
    os: Optional[str]  # Filter by operating system, e.g., "Windows", "Linux"
    last_seen: Optional[dict[str, float]]  # Filter by last seen timestamp
    status: Optional[str]  # Filter by device status, e.g., "active", "inactive"
    tags: Optional[list[str]]  # Filter by tags associated with the device

class DeviceScanResultListSchema(TypedDict, total=False):
    devices: list[DeviceScanResultSchema]  # List of device scan results
    total_count: int  # Total number of devices found
    page: int  # Current page number for pagination
    page_size: int  # Number of results per page
    total_pages: int  # Total number of pages available
    filters: DeviceScanFilterSchema  # Optional filters applied to the scan results
    sort_by: Optional[str]  # Field to sort by, e.g., "last_seen"
    sort_order: Optional[str]  # "asc" or "desc"
    context: Optional[dict[str, object]]  # Additional context if needed

class DeviceScanEventSchema(TypedDict, total=False):
    timestamp: float  # When the scan event occurred
    type: str  # e.g., "device_scan_started", "device_scan_completed", "device_scan_error"
    data: DeviceScanResultSchema  # The device scan result involved in the event
    source: Optional[str]  # Source of the event, e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class DeviceScanEventLogSchema(TypedDict, total=False):
    events: list[DeviceScanEventSchema]  # List of device scan events
    total_count: int  # Total number of events in the log
    page: int  # Current page number
    page_size: int  # Number of events per page
    total_pages: int  # Total number of pages available
    filters: DeviceScanFilterSchema  # Optional filters applied to the event log
    sort_by: Optional[str]  # Field to sort by, e.g., "timestamp"
    sort_order: Optional[str]  # "asc" or "desc"
