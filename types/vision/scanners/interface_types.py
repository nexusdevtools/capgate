# capgate/types/vision/scanners/interface_types.py

from typing import Literal, Optional
from typing_extensions import TypedDict



class InterfaceScanResult(TypedDict, total=False):
    name: str
    mac: str
    supports_monitor: bool
    supports_2ghz: Optional[bool]
    supports_11n: Optional[bool]
    supports_11g: Optional[bool]
    supports_11b: Optional[bool]
    supports_11a: Optional[bool]

class DeviceScanResult(TypedDict, total=False):
    mac: str
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: bool
    last_seen: float

class CredentialScanResult(TypedDict, total=False):
    id: str
    type: str  # e.g., "WPA2", "hashcat"
    value: str
    cracked: Optional[bool]
    source: Optional[str]
    
class MetadataEntry(TypedDict, total=False):
    plugin: str
    status: str
    updated: float

EventType = Literal["interface", "device", "credential", "meta"]

class ScanEvent(TypedDict, total=False):
    type: EventType
    data: InterfaceScanResult | DeviceScanResult | CredentialScanResult | MetadataEntry
    timestamp: float
    source: Optional[str]  # e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class ScanResult(TypedDict, total=False):
    interfaces: list[InterfaceScanResult]
    devices: list[DeviceScanResult]
    credentials: list[CredentialScanResult]
    metadata: list[MetadataEntry]
    events: list[ScanEvent]  # List of events captured during the scan
    timestamp: float  # When the scan was performed
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"

class ScanSummary(TypedDict, total=False):
    total_interfaces: int
    total_devices: int
    total_credentials: int
    total_metadata: int
    scan_duration: float  # Duration of the scan in seconds
    timestamp: float  # When the summary was generated
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"

class ScanError(TypedDict, total=False):
    error_type: str  # e.g., "InterfaceScanError", "DeviceScanError"
    message: str  # Description of the error
    timestamp: float  # When the error occurred
    source: Optional[str]  # Source of the scan, e.g., "iface_scan", "device_scan"
    context: Optional[dict[str, object]]  # Additional context if needed

class ScanConfig(TypedDict, total=False):
    interface: dict[str, object]
    device: dict[str, object]
    credential: dict[str, object]
    metadata: dict[str, object]

class ScanOptions(TypedDict, total=False):
    include_hidden: bool  # Whether to include hidden devices
    include_inactive: bool  # Whether to include inactive devices
    include_rogue: bool  # Whether to include rogue devices
    include_suspicious: bool  # Whether to include suspicious devices
    timeout: Optional[int]  # Timeout for the scan in seconds
    max_results: Optional[int]  # Maximum number of results to return
    filter_by_vendor: Optional[str]  # Filter results by vendor name

class ScanContext(TypedDict, total=False):
    scan_id: str  # Unique identifier for the scan
    start_time: float  # When the scan started
    end_time: Optional[float]  # When the scan ended
    options: ScanOptions  # Options used for the scan
    results: ScanResult  # Results of the scan
    summary: ScanSummary  # Summary of the scan
    errors: list[ScanError]  # List of errors encountered during the scan

class ScanReport(TypedDict, total=False):
    scan_id: str  # Unique identifier for the scan
    timestamp: float  # When the report was generated
    context: ScanContext  # Context of the scan
    results: ScanResult  # Results of the scan
    summary: ScanSummary  # Summary of the scan
    errors: list[ScanError]  # List of errors encountered during the scan
    config: ScanConfig  # Configuration used for the scan

class ScanHistoryEntry(TypedDict, total=False):
    scan_id: str  # Unique identifier for the scan
    timestamp: float  # When the scan was performed
    context: ScanContext  # Context of the scan
    results: ScanResult  # Results of the scan
    summary: ScanSummary  # Summary of the scan
    errors: list[ScanError]  # List of errors encountered during the scan
    config: ScanConfig  # Configuration used for the scan

class ScanHistory(TypedDict, total=False):
    entries: list[ScanHistoryEntry]  # List of scan history entries
    total_scans: int  # Total number of scans in the history
    last_scan_id: Optional[str]  # ID of the last scan performed
    last_scan_timestamp: Optional[float]  # Timestamp of the last scan performed
    last_scan_context: Optional[ScanContext]  # Context of the last scan performed

class ScanHistorySummary(TypedDict, total=False):
    total_scans: int  # Total number of scans in the history
    first_scan_timestamp: Optional[float]  # Timestamp of the first scan performed
    last_scan_timestamp: Optional[float]  # Timestamp of the last scan performed
    average_scan_duration: Optional[float]  # Average duration of scans in seconds
    total_errors: int  # Total number of errors encountered in the history
    most_common_error: Optional[str]  # Most common error type encountered
    most_active_source: Optional[str]  # Source with the most scans performed
