# capgate/types/brain/event_types.py

from typing import Literal, TypedDict


EventType = Literal[
    "interface",
    "device",
    "credential",
    "meta",
    "flat_event",
]


class FlatEventRow(TypedDict, total=False):
    timestamp: float
    type: EventType
    id: str
    vendor: str
    signal_strength: int
    is_router: bool
    mode: str
    mac: str

class FlatEvent(TypedDict, total=False):
    rows: list[FlatEventRow]
    metadata: dict[str, object]

class EventLogEntry(TypedDict):
    timestamp: float
    type: EventType
    id: str
    data: dict[str, object]  # Specify key and value types

class AppContextData(TypedDict):
    interfaces: dict[str, object]  # Replace with actual interface data type
    devices: dict[str, object]  # Replace with actual device data type
    credentials: dict[str, object]  # Replace with actual credential data type
    metadata: dict[str, object]  # Replace with actual metadata entry type
    event_log: list[EventLogEntry]
    flat_events: list[FlatEvent]  # List of flat events for easier processing

class EventSummary(TypedDict, total=False):
    total_interfaces: int
    total_devices: int
    total_credentials: int
    total_metadata: int
    scan_duration: float  # Duration of the scan in seconds
    event_count: int  # Total number of events captured
    last_updated: float  # Timestamp of the last update to the event log
    source: str  # Source of the events, e.g., "iface_scan", "device_scan"

class EventData(TypedDict, total=False):
    type: EventType
    id: str
    data: dict[str, object]  # Specify key and value types
    timestamp: float  # When the event was captured
    source: str  # Source of the event, e.g., "iface_scan", "device_scan"
    context: dict[str, object]  # Additional context if needed

class EventLog(TypedDict, total=False):
    entries: list[EventLogEntry]
    metadata: dict[str, object]

class EventConfig(TypedDict, total=False):
    interface: dict[str, object]  # Configuration for interface events
    device: dict[str, object]  # Configuration for device events
    credential: dict[str, object]  # Configuration for credential events
    metadata: dict[str, object]  # Configuration for metadata events
    flat_event: dict[str, object]  # Configuration for flat events
    event_summary: EventSummary  # Summary of the event log

class EventError(TypedDict, total=False):
    error_type: str  # e.g., "InterfaceEventError", "DeviceEventError"
    message: str  # Description of the error
    timestamp: float  # When the error occurred
    source: str  # Source of the event, e.g., "iface_scan", "device_scan"
    context: dict[str, object]  # Additional context if needed

class EventScanResult(TypedDict, total=False):
    interfaces: list[dict[str, object]]  # List of interface scan results
    devices: list[dict[str, object]]  # List of device scan results
    credentials: list[dict[str, object]]  # List of credential scan results
    metadata: list[dict[str, object]]  # List of metadata entries
    events: list[EventData]  # List of events captured during the scan
    timestamp: float  # When the scan was performed
    source: str  # Source of the scan, e.g., "iface_scan", "device_scan"

class EventScanSummary(TypedDict, total=False):
    total_interfaces: int
    total_devices: int
    total_credentials: int
    total_metadata: int
    scan_duration: float  # Duration of the scan in seconds
    timestamp: float  # When the summary was generated
    source: str  # Source of the scan, e.g., "iface_scan", "device_scan"

class EventScanError(TypedDict, total=False):
    error_type: str  # e.g., "InterfaceScanError", "DeviceScanError"
    message: str  # Description of the error
    timestamp: float  # When the error occurred
    source: str  # Source of the scan, e.g., "iface_scan", "device_scan"
    context: dict[str, object]  # Additional context if needed

class EventScanConfig(TypedDict, total=False):
    interface: dict[str, object]  # Configuration for interface scans
    device: dict[str, object]  # Configuration for device scans
    credential: dict[str, object]  # Configuration for credential scans
    metadata: dict[str, object]  # Configuration for metadata scans
    flat_event: dict[str, object]  # Configuration for flat events
    event_summary: EventSummary  # Summary of the event scan

class EventScanResultSummary(TypedDict, total=False):
    total_interfaces: int
    total_devices: int
    total_credentials: int
    total_metadata: int
    total_events: int  # Total number of events captured
    scan_duration: float  # Duration of the scan in seconds
    timestamp: float  # When the summary was generated
    source: str  # Source of the scan, e.g., "iface_scan", "device_scan"

class EventScanOptions(TypedDict, total=False):
    include_hidden: bool  # Whether to include hidden devices
    include_inactive: bool  # Whether to include inactive devices
    include_rogue: bool  # Whether to include rogue devices
    include_suspicious: bool  # Whether to include suspicious devices
    timeout: int  # Timeout for the scan in seconds
    max_results: int  # Maximum number of results to return
    flat_event_format: str  # Format for flat events, e.g., "csv", "json"

class EventScanContext(TypedDict, total=False):
    interfaces: dict[str, object]  # Context for interface scans
    devices: dict[str, object]  # Context for device scans
    credentials: dict[str, object]  # Context for credential scans
    metadata: dict[str, object]  # Context for metadata scans
    flat_events: list[FlatEvent]  # List of flat events for easier processing
    event_log: EventLog  # Event log containing all captured events
    event_summary: EventSummary  # Summary of the event log

class EventScanContextData(TypedDict, total=False):
    interfaces: dict[str, object]  # Context for interface scans
    devices: dict[str, object]  # Context for device scans
    credentials: dict[str, object]  # Context for credential scans
    metadata: dict[str, object]  # Context for metadata scans
    flat_events: list[FlatEvent]  # List of flat events for easier processing
    event_log: EventLog  # Event log containing all captured events
    event_summary: EventSummary  # Summary of the event log

class EventScanContextSummary(TypedDict, total=False):
    total_interfaces: int
    total_devices: int
    total_credentials: int
    total_metadata: int
    total_events: int  # Total number of events captured
    scan_duration: float  # Duration of the scan in seconds
    last_updated: float  # Timestamp of the last update to the event log
    source: str  # Source of the events, e.g., "iface_scan", "device_scan"

class EventScanContextError(TypedDict, total=False):
    error_type: str  # e.g., "InterfaceEventError", "DeviceEventError"
    message: str  # Description of the error
    timestamp: float  # When the error occurred
    source: str  # Source of the event, e.g., "iface_scan", "device_scan"
    context: dict[str, object]  # Additional context if needed

class EventScanContextConfig(TypedDict, total=False):
    interface: dict[str, object]  # Configuration for interface scans
    device: dict[str, object]  # Configuration for device scans
    credential: dict[str, object]  # Configuration for credential scans
    metadata: dict[str, object]  # Configuration for metadata scans
    flat_event: dict[str, object]  # Configuration for flat events
    event_summary: EventSummary  # Summary of the event scan
    event_log: EventLog  # Event log containing all captured events

class EventScanContextOptions(TypedDict, total=False):
    include_hidden: bool  # Whether to include hidden devices
    include_inactive: bool  # Whether to include inactive devices
    include_rogue: bool  # Whether to include rogue devices
    include_suspicious: bool  # Whether to include suspicious devices
    timeout: int  # Timeout for the scan in seconds
    max_results: int  # Maximum number of results to return
    flat_event_format: str  # Format for flat events, e.g., "csv", "json"

# Note: The above code defines various TypedDicts for event types, event logs, and scan results.
# These TypedDicts can be used to structure data related to events, scans, and their configurations.
# They provide a clear schema for the data, making it easier to work with and understand.
# The use of TypedDicts allows for type checking and better code completion in IDEs,
# improving the overall development experience.
