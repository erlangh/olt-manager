"""
ONT (Optical Network Terminal) models.
"""

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ONTStatus(str, enum.Enum):
    """ONT status."""
    ONLINE = "online"
    OFFLINE = "offline"
    PROVISIONED = "provisioned"
    DISCOVERED = "discovered"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ONTType(str, enum.Enum):
    """ONT device types."""
    GPON = "gpon"
    EPON = "epon"
    BRIDGE = "bridge"
    ROUTER = "router"


class ONTServiceStatus(str, enum.Enum):
    """ONT service status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ERROR = "error"


class ONT(Base):
    """ONT (Optical Network Terminal) model."""
    
    __tablename__ = "onts"
    
    # Device identification
    serial_number = Column(String(100), nullable=False, unique=True, index=True)
    mac_address = Column(String(17), nullable=True, unique=True, index=True)
    equipment_id = Column(String(100), nullable=True)
    
    # Network location
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False, index=True)
    port_id = Column(Integer, ForeignKey("olt_ports.id"), nullable=False, index=True)
    ont_id = Column(Integer, nullable=False)  # ONT ID on the port (0-127)
    
    # Device information
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    model = Column(String(50), nullable=True)
    vendor = Column(String(50), nullable=True)
    ont_type = Column(Enum(ONTType), default=ONTType.GPON, nullable=False)
    
    # Status and monitoring
    status = Column(Enum(ONTStatus), default=ONTStatus.DISCOVERED, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    admin_status = Column(Boolean, default=True, nullable=False)
    
    # Customer information
    customer_name = Column(String(100), nullable=True)
    customer_id = Column(String(50), nullable=True, index=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(100), nullable=True)
    installation_address = Column(Text, nullable=True)
    
    # Technical parameters
    firmware_version = Column(String(50), nullable=True)
    hardware_version = Column(String(50), nullable=True)
    software_version = Column(String(50), nullable=True)
    
    # Signal quality
    rx_power = Column(Float, nullable=True)  # dBm
    tx_power = Column(Float, nullable=True)  # dBm
    voltage = Column(Float, nullable=True)   # Volts
    temperature = Column(Float, nullable=True)  # Celsius
    distance = Column(Float, nullable=True)  # km
    
    # Performance metrics
    uptime = Column(Integer, nullable=True)  # Seconds
    last_seen = Column(String(255), nullable=True)
    last_offline = Column(String(255), nullable=True)
    
    # Traffic statistics
    rx_bytes = Column(Integer, default=0, nullable=False)
    tx_bytes = Column(Integer, default=0, nullable=False)
    rx_packets = Column(Integer, default=0, nullable=False)
    tx_packets = Column(Integer, default=0, nullable=False)
    rx_errors = Column(Integer, default=0, nullable=False)
    tx_errors = Column(Integer, default=0, nullable=False)
    
    # Configuration
    max_bandwidth_up = Column(Integer, nullable=True)    # Mbps
    max_bandwidth_down = Column(Integer, nullable=True)  # Mbps
    vlan_id = Column(Integer, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # Service activation
    provisioned_at = Column(String(255), nullable=True)
    activated_at = Column(String(255), nullable=True)
    
    # Relationships
    olt = relationship("OLT", back_populates="onts")
    port = relationship("OLTPort", back_populates="onts")
    services = relationship("ONTService", back_populates="ont", cascade="all, delete-orphan")
    alarms = relationship("Alarm", back_populates="ont", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ONT(sn='{self.serial_number}', status='{self.status}', ont_id={self.ont_id})>"
    
    @property
    def is_online(self) -> bool:
        """Check if ONT is online."""
        return self.status == ONTStatus.ONLINE
    
    @property
    def is_provisioned(self) -> bool:
        """Check if ONT is provisioned."""
        return self.status in [ONTStatus.PROVISIONED, ONTStatus.ONLINE]
    
    @property
    def full_location(self) -> str:
        """Get full location string."""
        return f"OLT-{self.olt_id}/Port-{self.port_id}/ONT-{self.ont_id}"
    
    @property
    def signal_quality(self) -> str:
        """Get signal quality assessment."""
        if self.rx_power is None:
            return "Unknown"
        
        if self.rx_power >= -20:
            return "Excellent"
        elif self.rx_power >= -25:
            return "Good"
        elif self.rx_power >= -28:
            return "Fair"
        else:
            return "Poor"
    
    @property
    def active_services_count(self) -> int:
        """Get count of active services."""
        return len([service for service in self.services if service.status == ONTServiceStatus.ACTIVE])


class ONTService(Base):
    """ONT service configuration model."""
    
    __tablename__ = "ont_services"
    
    # Service identification
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=False, index=True)
    service_profile_id = Column(Integer, ForeignKey("service_profiles.id"), nullable=False, index=True)
    
    # Service configuration
    service_name = Column(String(100), nullable=False)
    vlan_id = Column(Integer, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    
    # Bandwidth configuration
    bandwidth_up = Column(Integer, nullable=False)    # Mbps
    bandwidth_down = Column(Integer, nullable=False)  # Mbps
    burst_up = Column(Integer, nullable=True)         # Mbps
    burst_down = Column(Integer, nullable=True)       # Mbps
    
    # Service status
    status = Column(Enum(ONTServiceStatus), default=ONTServiceStatus.INACTIVE, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Service details
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Activation tracking
    activated_at = Column(String(255), nullable=True)
    deactivated_at = Column(String(255), nullable=True)
    
    # Traffic statistics
    rx_bytes = Column(Integer, default=0, nullable=False)
    tx_bytes = Column(Integer, default=0, nullable=False)
    rx_packets = Column(Integer, default=0, nullable=False)
    tx_packets = Column(Integer, default=0, nullable=False)
    
    # Relationships
    ont = relationship("ONT", back_populates="services")
    service_profile = relationship("ServiceProfile", back_populates="ont_services")
    
    def __repr__(self):
        return f"<ONTService(ont_id={self.ont_id}, service='{self.service_name}', status='{self.status}')>"
    
    @property
    def is_active_service(self) -> bool:
        """Check if service is active."""
        return self.status == ONTServiceStatus.ACTIVE and self.is_active
    
    @property
    def bandwidth_ratio(self) -> float:
        """Calculate upload/download bandwidth ratio."""
        if self.bandwidth_down == 0:
            return 0.0
        return self.bandwidth_up / self.bandwidth_down