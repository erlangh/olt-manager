"""
OLT (Optical Line Terminal) models for ZTE C320 devices.
"""

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base


class OLTStatus(str, enum.Enum):
    """OLT device status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class OLTPortType(str, enum.Enum):
    """OLT port types."""
    GPON = "gpon"
    EPON = "epon"
    ETHERNET = "ethernet"
    UPLINK = "uplink"


class OLTPortStatus(str, enum.Enum):
    """OLT port status."""
    UP = "up"
    DOWN = "down"
    DISABLED = "disabled"
    ERROR = "error"


class OLT(Base):
    """OLT (Optical Line Terminal) device model."""
    
    __tablename__ = "olts"
    
    # Basic information
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    model = Column(String(50), default="ZTE C320", nullable=False)
    serial_number = Column(String(100), nullable=True, unique=True)
    
    # Network configuration
    ip_address = Column(String(45), nullable=False, unique=True, index=True)  # IPv4/IPv6
    snmp_port = Column(Integer, default=161, nullable=False)
    snmp_community = Column(String(100), default="public", nullable=False)
    snmp_version = Column(String(10), default="2c", nullable=False)
    snmp_username = Column(String(100), nullable=True)  # For SNMPv3
    snmp_auth_key = Column(String(255), nullable=True)  # For SNMPv3
    snmp_priv_key = Column(String(255), nullable=True)  # For SNMPv3
    
    # Location and organization
    location = Column(String(200), nullable=True)
    site_id = Column(String(50), nullable=True, index=True)
    region = Column(String(100), nullable=True)
    
    # Status and monitoring
    status = Column(Enum(OLTStatus), default=OLTStatus.OFFLINE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(String(255), nullable=True)
    uptime = Column(Integer, nullable=True)  # Seconds
    
    # Hardware information
    firmware_version = Column(String(50), nullable=True)
    hardware_version = Column(String(50), nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    
    # Configuration
    max_onts = Column(Integer, default=1024, nullable=False)
    total_ports = Column(Integer, default=16, nullable=False)
    
    # Relationships
    ports = relationship("OLTPort", back_populates="olt", cascade="all, delete-orphan")
    onts = relationship("ONT", back_populates="olt", cascade="all, delete-orphan")
    alarms = relationship("Alarm", back_populates="olt", cascade="all, delete-orphan")
    performance_data = relationship("PerformanceData", back_populates="olt", cascade="all, delete-orphan")
    configurations = relationship("Configuration", back_populates="olt", cascade="all, delete-orphan")
    backups = relationship("Backup", back_populates="olt", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OLT(name='{self.name}', ip='{self.ip_address}', status='{self.status}')>"
    
    @property
    def is_online(self) -> bool:
        """Check if OLT is online."""
        return self.status == OLTStatus.ONLINE
    
    @property
    def active_onts_count(self) -> int:
        """Get count of active ONTs."""
        return len([ont for ont in self.onts if ont.is_active])
    
    @property
    def active_ports_count(self) -> int:
        """Get count of active ports."""
        return len([port for port in self.ports if port.status == OLTPortStatus.UP])


class OLTPort(Base):
    """OLT port model."""
    
    __tablename__ = "olt_ports"
    
    # Port identification
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False, index=True)
    port_number = Column(Integer, nullable=False)
    port_name = Column(String(50), nullable=True)
    port_type = Column(Enum(OLTPortType), default=OLTPortType.GPON, nullable=False)
    
    # Port configuration
    description = Column(Text, nullable=True)
    vlan_id = Column(Integer, nullable=True)
    max_onts = Column(Integer, default=64, nullable=False)
    
    # Port status
    status = Column(Enum(OLTPortStatus), default=OLTPortStatus.DOWN, nullable=False)
    admin_status = Column(Boolean, default=True, nullable=False)
    
    # Performance metrics
    rx_power = Column(Float, nullable=True)  # dBm
    tx_power = Column(Float, nullable=True)  # dBm
    temperature = Column(Float, nullable=True)  # Celsius
    voltage = Column(Float, nullable=True)  # Volts
    current = Column(Float, nullable=True)  # mA
    
    # Traffic statistics
    rx_bytes = Column(Integer, default=0, nullable=False)
    tx_bytes = Column(Integer, default=0, nullable=False)
    rx_packets = Column(Integer, default=0, nullable=False)
    tx_packets = Column(Integer, default=0, nullable=False)
    rx_errors = Column(Integer, default=0, nullable=False)
    tx_errors = Column(Integer, default=0, nullable=False)
    
    # Relationships
    olt = relationship("OLT", back_populates="ports")
    onts = relationship("ONT", back_populates="port")
    
    def __repr__(self):
        return f"<OLTPort(olt_id={self.olt_id}, port={self.port_number}, status='{self.status}')>"
    
    @property
    def is_up(self) -> bool:
        """Check if port is up."""
        return self.status == OLTPortStatus.UP
    
    @property
    def ont_count(self) -> int:
        """Get count of ONTs on this port."""
        return len(self.onts)
    
    @property
    def active_ont_count(self) -> int:
        """Get count of active ONTs on this port."""
        return len([ont for ont in self.onts if ont.is_active])
    
    @property
    def utilization_percentage(self) -> float:
        """Calculate port utilization percentage."""
        if self.max_onts == 0:
            return 0.0
        return (self.active_ont_count / self.max_onts) * 100