"""
OLT API schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator, IPvAnyAddress

from ...models.olt import OLTStatus, OLTType, PortStatus, PortType


class OLTBase(BaseModel):
    """Base OLT schema."""
    name: str = Field(..., min_length=1, max_length=100, description="OLT name")
    ip_address: str = Field(..., description="OLT IP address")
    snmp_port: int = Field(161, ge=1, le=65535, description="SNMP port")
    snmp_community: str = Field("public", min_length=1, max_length=50, description="SNMP community")
    snmp_version: str = Field("2c", regex="^(1|2c|3)$", description="SNMP version")
    location: Optional[str] = Field(None, max_length=200, description="Physical location")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    olt_type: OLTType = Field(OLTType.ZTE_C320, description="OLT type")
    
    @validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')


class OLTCreate(OLTBase):
    """Schema for creating OLT."""
    pass


class OLTUpdate(BaseModel):
    """Schema for updating OLT."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ip_address: Optional[str] = Field(None)
    snmp_port: Optional[int] = Field(None, ge=1, le=65535)
    snmp_community: Optional[str] = Field(None, min_length=1, max_length=50)
    snmp_version: Optional[str] = Field(None, regex="^(1|2c|3)$")
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[OLTStatus] = Field(None)
    
    @validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v is not None:
            try:
                IPvAnyAddress(v)
                return v
            except ValueError:
                raise ValueError('Invalid IP address format')
        return v


class OLTResponse(OLTBase):
    """Schema for OLT response."""
    id: int
    status: OLTStatus
    firmware_version: Optional[str]
    hardware_version: Optional[str]
    serial_number: Optional[str]
    mac_address: Optional[str]
    uptime_seconds: Optional[int]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    temperature: Optional[float]
    power_consumption: Optional[float]
    fan_speed: Optional[int]
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OLTListResponse(BaseModel):
    """Schema for OLT list response."""
    olts: List[OLTResponse]
    total: int
    page: int
    per_page: int
    pages: int


class OLTPortBase(BaseModel):
    """Base OLT port schema."""
    slot_number: int = Field(..., ge=0, description="Slot number")
    port_number: int = Field(..., ge=1, description="Port number")
    port_type: PortType = Field(PortType.GPON, description="Port type")
    name: Optional[str] = Field(None, max_length=50, description="Port name")
    description: Optional[str] = Field(None, max_length=200, description="Port description")
    max_distance: Optional[int] = Field(None, ge=0, description="Maximum distance in meters")
    split_ratio: Optional[str] = Field(None, max_length=10, description="Split ratio (e.g., 1:32)")


class OLTPortCreate(OLTPortBase):
    """Schema for creating OLT port."""
    pass


class OLTPortUpdate(BaseModel):
    """Schema for updating OLT port."""
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    status: Optional[PortStatus] = Field(None)
    max_distance: Optional[int] = Field(None, ge=0)
    split_ratio: Optional[str] = Field(None, max_length=10)
    admin_status: Optional[bool] = Field(None)


class OLTPortResponse(OLTPortBase):
    """Schema for OLT port response."""
    id: int
    olt_id: int
    status: PortStatus
    admin_status: bool
    optical_power_tx: Optional[float]
    optical_power_rx: Optional[float]
    temperature: Optional[float]
    voltage: Optional[float]
    bias_current: Optional[float]
    ont_count: Optional[int]
    max_ont_count: Optional[int]
    bandwidth_profile: Optional[str]
    vlan_config: Optional[str]
    rx_bytes: Optional[int]
    tx_bytes: Optional[int]
    rx_packets: Optional[int]
    tx_packets: Optional[int]
    rx_errors: Optional[int]
    tx_errors: Optional[int]
    rx_drops: Optional[int]
    tx_drops: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OLTStatsResponse(BaseModel):
    """Schema for OLT statistics response."""
    olt_id: int
    total_ports: int
    active_ports: int
    total_onts: int
    online_onts: int
    active_alarms: int
    cpu_usage: float
    memory_usage: float
    temperature: float
    uptime_seconds: int


class OLTHealthResponse(BaseModel):
    """Schema for OLT health response."""
    olt_id: int
    health_status: str = Field(..., description="Overall health status")
    health_score: int = Field(..., ge=0, le=100, description="Health score (0-100)")
    issues: List[str] = Field(default_factory=list, description="List of health issues")
    last_check: datetime = Field(..., description="Last health check timestamp")