# capgate/db/schemas/device.py

from pydantic import BaseModel, Field
from typing import Optional


class Device(BaseModel):
    """
    Represents a discovered network device.
    Used across scanners and network visualization components.
    """

    ip: str = Field(..., description="IPv4 address of the device")
    mac: Optional[str] = Field(None, description="MAC address of the device")
    hostname: Optional[str] = Field(None, description="Resolved hostname, if available")
    vendor: Optional[str] = Field(None, description="Device vendor/manufacturer")
    os: Optional[str] = Field(None, description="Operating system (if fingerprinted)")
    interface: Optional[str] = Field(None, description="Interface on which device was seen")

    def __str__(self):
        return f"{self.hostname or 'Unknown'} @ {self.ip} [{self.mac or 'No MAC'}]"
