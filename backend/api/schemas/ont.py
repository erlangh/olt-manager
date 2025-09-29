"""
ONT API schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from ...models.ont import ONTStatus, ONTType, ServiceStatus
from ...models.service_profile import ServiceType


class ONTBase(BaseModel):
    """Base ONT schema."""
    serial_number: str = Field(..., min_length=1, max_length=50, description="ONT serial number")
    olt_id: int = Field(..., description="OLT ID")
    olt_port_id: Optional[int] = Field(None, description="OLT port ID")
    ont_id: Optional[int] = Field(None, ge=1, le=128, description="ONT ID on port")
    ont_type: ONTType = Field(ONTType.HG8310M, description="ONT type")
    customer_name: Optional[str] = Field(None, max_length=100, description="Customer name")
    customer_phone: Optional[str] = Field(None, max_length=20, description="Customer phone")
    customer_email: Optional[str] = Field(None, max_length=100, description="Customer email")
    installation_address: Optional[str] = Field(None, max_length=200, description="Installation address")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    
    @validator('customer_email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class ONTCreate(ONTBase):
    """Schema for creating ONT."""
    pass


class ONTUpdate(BaseModel):
    """Schema for updating ONT."""
    serial_number: Optional[str] = Field(None, min_length=1, max_length=50)
    olt_port_id: Optional[int] = Field(None)
    ont_id: Optional[int] = Field(None, ge=1, le=128)
    status: Optional[ONTStatus] = Field(None)
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=100)
    installation_address: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('customer_email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class ONTResponse(ONTBase):
    """Schema for ONT response."""
    id: int
    status: ONTStatus
    firmware_version: Optional[str]
    hardware_version: Optional[str]
    mac_address: Optional[str]
    rx_power: Optional[float]
    tx_power: Optional[float]
    voltage: Optional[float]
    temperature: Optional[float]
    distance: Optional[int]
    uptime_seconds: Optional[int]
    last_seen: Optional[datetime]
    rx_bytes: Optional[int]
    tx_bytes: Optional[int]
    rx_packets: Optional[int]
    tx_packets: Optional[int]
    rx_errors: Optional[int]
    tx_errors: Optional[int]
    rx_drops: Optional[int]
    tx_drops: Optional[int]
    config_status: Optional[str]
    provisioning_status: Optional[str]
    service_activation_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ONTListResponse(BaseModel):
    """Schema for ONT list response."""
    onts: List[ONTResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ONTServiceBase(BaseModel):
    """Base ONT service schema."""
    service_profile_id: Optional[int] = Field(None, description="Service profile ID")
    service_name: str = Field(..., min_length=1, max_length=100, description="Service name")
    service_type: ServiceType = Field(ServiceType.INTERNET, description="Service type")
    vlan_id: Optional[int] = Field(None, ge=1, le=4094, description="VLAN ID")
    bandwidth_up: Optional[int] = Field(None, ge=0, description="Upload bandwidth in Kbps")
    bandwidth_down: Optional[int] = Field(None, ge=0, description="Download bandwidth in Kbps")
    description: Optional[str] = Field(None, max_length=200, description="Service description")


class ONTServiceCreate(ONTServiceBase):
    """Schema for creating ONT service."""
    pass


class ONTServiceUpdate(BaseModel):
    """Schema for updating ONT service."""
    service_profile_id: Optional[int] = Field(None)
    service_name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[ServiceStatus] = Field(None)
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    bandwidth_up: Optional[int] = Field(None, ge=0)
    bandwidth_down: Optional[int] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=200)


class ONTServiceResponse(ONTServiceBase):
    """Schema for ONT service response."""
    id: int
    ont_id: int
    status: ServiceStatus
    activation_date: Optional[datetime]
    deactivation_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ONTStatsResponse(BaseModel):
    """Schema for ONT statistics response."""
    ont_id: int
    total_services: int
    active_services: int
    active_alarms: int
    rx_power: float
    tx_power: float
    distance: int
    uptime_seconds: int
    rx_bytes: int
    tx_bytes: int


class ONTSignalResponse(BaseModel):
    """Schema for ONT signal response."""
    ont_id: int
    rx_power: Optional[float] = Field(None, description="Received optical power in dBm")
    tx_power: Optional[float] = Field(None, description="Transmitted optical power in dBm")
    voltage: Optional[float] = Field(None, description="Supply voltage in V")
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    distance: Optional[int] = Field(None, description="Distance from OLT in meters")
    signal_quality: str = Field(..., description="Signal quality assessment")
    last_update: datetime = Field(..., description="Last signal measurement timestamp")


class ONTProvisionRequest(BaseModel):
    """Schema for ONT provisioning request."""
    service_profile_ids: List[int] = Field(..., description="List of service profile IDs to provision")
    force_reprovision: bool = Field(False, description="Force reprovisioning even if already provisioned")