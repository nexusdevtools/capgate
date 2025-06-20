# capgate/types/core/context_types.py

from __future__ import annotations
from typing import Union, Literal, Optional
from typing_extensions import TypedDict


class InterfaceData(TypedDict, total=False):
    name: str
    mac: str
    mode: Optional[str]  # managed/monitor
    driver: Optional[str]
    signal_quality: Optional[int]
    supports_monitor: bool
    supports_5ghz: Optional[bool]
    supports_6ghz: Optional[bool]
    supports_24ghz: Optional[bool]
    supports_60ghz: Optional[bool]
    supports_80211ac: Optional[bool]
    supports_80211ax: Optional[bool]
    supports_80211ad: Optional[bool]
    supports_80211be: Optional[bool]
    supports_80211ah: Optional[bool]
    supports_80211af: Optional[bool]
    supports_80211bgn: Optional[bool]
    supports_80211bg: Optional[bool]
    supports_80211n: Optional[bool]
    supports_80211g: Optional[bool]
    supports_80211b: Optional[bool]
    supports_80211a: Optional[bool]
    supports_2ghz: Optional[bool]
    supports_11n: Optional[bool]
    supports_11g: Optional[bool]
    supports_11b: Optional[bool]
    supports_11a: Optional[bool]


class DeviceData(TypedDict, total=False):
    mac: str
    vendor: Optional[str]
    signal_strength: Optional[int]
    is_router: bool
    last_seen: float


class CredentialData(TypedDict, total=False):
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


class EventLogEntry(TypedDict):
    timestamp: float
    type: EventType
    id: str
    data: dict[str, object]  # Specify key and value types

class AppContextData(TypedDict):
    interfaces: dict[str, InterfaceData]
    devices: dict[str, DeviceData]
    credentials: dict[str, CredentialData]
    metadata: dict[str, MetadataEntry]
    event_log: list[EventLogEntry]
    store: dict[str, Union[str, int, float, bool, None]]