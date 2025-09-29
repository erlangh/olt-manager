from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="user")  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class OLT(Base):
    __tablename__ = "olts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(15), unique=True, nullable=False)
    snmp_community = Column(String(50), default="public")
    snmp_version = Column(String(10), default="2c")
    snmp_port = Column(Integer, default=161)
    model = Column(String(50), default="ZTE C320")
    location = Column(String(200))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    onts = relationship("ONT", back_populates="olt")
    ports = relationship("OLTPort", back_populates="olt")

class OLTPort(Base):
    __tablename__ = "olt_ports"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False)
    port_number = Column(Integer, nullable=False)
    port_type = Column(String(20), default="GPON")  # GPON, EPON
    status = Column(String(20), default="down")  # up, down, testing
    admin_status = Column(String(20), default="up")  # up, down
    description = Column(String(200))
    max_onts = Column(Integer, default=128)
    current_onts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    olt = relationship("OLT", back_populates="ports")
    onts = relationship("ONT", back_populates="port")

class ONT(Base):
    __tablename__ = "onts"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False)
    port_id = Column(Integer, ForeignKey("olt_ports.id"), nullable=False)
    ont_id = Column(Integer, nullable=False)  # ONT ID on the port
    serial_number = Column(String(50), unique=True)
    mac_address = Column(String(17))
    model = Column(String(50))
    vendor = Column(String(50))
    firmware_version = Column(String(50))
    hardware_version = Column(String(50))
    status = Column(String(20), default="offline")  # online, offline, los, lof
    admin_status = Column(String(20), default="up")  # up, down
    signal_rx = Column(Float)  # Received signal power (dBm)
    signal_tx = Column(Float)  # Transmitted signal power (dBm)
    distance = Column(Float)  # Distance in meters
    last_seen = Column(DateTime(timezone=True))
    description = Column(String(200))
    customer_info = Column(JSON)  # Customer details
    service_profile = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    olt = relationship("OLT", back_populates="onts")
    port = relationship("OLTPort", back_populates="onts")
    services = relationship("ONTService", back_populates="ont")

class ONTService(Base):
    __tablename__ = "ont_services"
    
    id = Column(Integer, primary_key=True, index=True)
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=False)
    service_type = Column(String(20), nullable=False)  # internet, voip, iptv
    vlan_id = Column(Integer)
    bandwidth_up = Column(Integer)  # Kbps
    bandwidth_down = Column(Integer)  # Kbps
    priority = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ont = relationship("ONT", back_populates="services")

class ServiceProfile(Base):
    __tablename__ = "service_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    service_type = Column(String(20), nullable=False)  # internet, voip, iptv
    bandwidth_up = Column(Integer)  # Kbps
    bandwidth_down = Column(Integer)  # Kbps
    vlan_id = Column(Integer)
    priority = Column(Integer, default=0)
    configuration = Column(JSON)  # Additional service configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Alarm(Base):
    __tablename__ = "alarms"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"))
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=True)
    alarm_type = Column(String(50), nullable=False)  # los, lof, high_temp, etc.
    severity = Column(String(20), default="minor")  # critical, major, minor, warning
    status = Column(String(20), default="active")  # active, cleared, acknowledged
    message = Column(Text, nullable=False)
    additional_info = Column(JSON)
    raised_at = Column(DateTime(timezone=True), server_default=func.now())
    cleared_at = Column(DateTime(timezone=True))
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(String(50))

class PerformanceData(Base):
    __tablename__ = "performance_data"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"))
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=True)
    port_id = Column(Integer, ForeignKey("olt_ports.id"), nullable=True)
    metric_type = Column(String(50), nullable=False)  # cpu, memory, temperature, traffic
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"))
    config_type = Column(String(50), nullable=False)  # vlan, qos, security, etc.
    config_name = Column(String(100), nullable=False)
    config_data = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BackupRestore(Base):
    __tablename__ = "backup_restore"
    
    id = Column(Integer, primary_key=True, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"))
    operation_type = Column(String(20), nullable=False)  # backup, restore
    filename = Column(String(200), nullable=False)
    file_path = Column(String(500))
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text)
    created_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))  # olt, ont, user, config
    resource_id = Column(String(50))
    details = Column(JSON)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())