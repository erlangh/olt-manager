"""
Service Profile model for ONT service configurations.
"""

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ServiceType(str, enum.Enum):
    """Service types."""
    INTERNET = "internet"
    IPTV = "iptv"
    VOIP = "voip"
    ENTERPRISE = "enterprise"
    GAMING = "gaming"
    STREAMING = "streaming"


class QoSClass(str, enum.Enum):
    """Quality of Service classes."""
    BEST_EFFORT = "best_effort"
    ASSURED_FORWARDING = "assured_forwarding"
    EXPEDITED_FORWARDING = "expedited_forwarding"
    NETWORK_CONTROL = "network_control"


class ServiceProfile(Base):
    """Service profile model for defining service configurations."""
    
    __tablename__ = "service_profiles"
    
    # Profile identification
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    service_type = Column(Enum(ServiceType), nullable=False, index=True)
    
    # Bandwidth configuration
    bandwidth_up = Column(Integer, nullable=False)      # Mbps
    bandwidth_down = Column(Integer, nullable=False)    # Mbps
    burst_up = Column(Integer, nullable=True)           # Mbps
    burst_down = Column(Integer, nullable=True)         # Mbps
    
    # Quality of Service
    qos_class = Column(Enum(QoSClass), default=QoSClass.BEST_EFFORT, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # 0-7
    dscp_marking = Column(Integer, nullable=True)          # 0-63
    
    # VLAN configuration
    vlan_id = Column(Integer, nullable=True)
    vlan_priority = Column(Integer, default=0, nullable=False)  # 0-7
    
    # Traffic shaping
    committed_information_rate = Column(Integer, nullable=True)  # CIR in Kbps
    peak_information_rate = Column(Integer, nullable=True)       # PIR in Kbps
    committed_burst_size = Column(Integer, nullable=True)        # CBS in bytes
    excess_burst_size = Column(Integer, nullable=True)           # EBS in bytes
    
    # Service limits
    max_concurrent_sessions = Column(Integer, nullable=True)
    session_timeout = Column(Integer, nullable=True)  # Minutes
    idle_timeout = Column(Integer, nullable=True)     # Minutes
    
    # Multicast configuration (for IPTV)
    multicast_enabled = Column(Boolean, default=False, nullable=False)
    max_multicast_streams = Column(Integer, nullable=True)
    multicast_vlan = Column(Integer, nullable=True)
    
    # Security settings
    mac_learning_enabled = Column(Boolean, default=True, nullable=False)
    max_mac_addresses = Column(Integer, default=1, nullable=False)
    port_security_enabled = Column(Boolean, default=False, nullable=False)
    
    # Advanced features
    igmp_snooping_enabled = Column(Boolean, default=False, nullable=False)
    dhcp_option82_enabled = Column(Boolean, default=False, nullable=False)
    pppoe_plus_enabled = Column(Boolean, default=False, nullable=False)
    
    # Monitoring and logging
    traffic_monitoring_enabled = Column(Boolean, default=True, nullable=False)
    logging_enabled = Column(Boolean, default=True, nullable=False)
    
    # Profile status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Pricing information (optional)
    monthly_cost = Column(Float, nullable=True)
    setup_cost = Column(Float, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Template configuration
    config_template = Column(Text, nullable=True)  # JSON or XML template
    
    # Usage statistics
    active_subscribers = Column(Integer, default=0, nullable=False)
    total_subscribers = Column(Integer, default=0, nullable=False)
    
    # Relationships
    ont_services = relationship("ONTService", back_populates="service_profile")
    
    def __repr__(self):
        return f"<ServiceProfile(name='{self.name}', type='{self.service_type}', up={self.bandwidth_up}, down={self.bandwidth_down})>"
    
    @property
    def bandwidth_ratio(self) -> float:
        """Calculate upload/download bandwidth ratio."""
        if self.bandwidth_down == 0:
            return 0.0
        return self.bandwidth_up / self.bandwidth_down
    
    @property
    def is_symmetric(self) -> bool:
        """Check if service has symmetric bandwidth."""
        return self.bandwidth_up == self.bandwidth_down
    
    @property
    def max_theoretical_throughput(self) -> int:
        """Get maximum theoretical throughput in Mbps."""
        return max(self.bandwidth_up, self.bandwidth_down)
    
    @property
    def service_category(self) -> str:
        """Get service category based on bandwidth."""
        max_bw = self.max_theoretical_throughput
        
        if max_bw >= 1000:
            return "Enterprise"
        elif max_bw >= 100:
            return "Premium"
        elif max_bw >= 50:
            return "Standard"
        elif max_bw >= 10:
            return "Basic"
        else:
            return "Economy"
    
    @property
    def qos_priority_level(self) -> str:
        """Get QoS priority level description."""
        if self.priority >= 6:
            return "Critical"
        elif self.priority >= 4:
            return "High"
        elif self.priority >= 2:
            return "Medium"
        else:
            return "Low"
    
    def calculate_monthly_revenue(self) -> float:
        """Calculate monthly revenue from this profile."""
        if self.monthly_cost is None:
            return 0.0
        return self.monthly_cost * self.active_subscribers
    
    def get_config_dict(self) -> dict:
        """Get configuration as dictionary."""
        return {
            "name": self.name,
            "service_type": self.service_type,
            "bandwidth": {
                "up": self.bandwidth_up,
                "down": self.bandwidth_down,
                "burst_up": self.burst_up,
                "burst_down": self.burst_down
            },
            "qos": {
                "class": self.qos_class,
                "priority": self.priority,
                "dscp": self.dscp_marking
            },
            "vlan": {
                "id": self.vlan_id,
                "priority": self.vlan_priority
            },
            "traffic_shaping": {
                "cir": self.committed_information_rate,
                "pir": self.peak_information_rate,
                "cbs": self.committed_burst_size,
                "ebs": self.excess_burst_size
            },
            "features": {
                "multicast": self.multicast_enabled,
                "mac_learning": self.mac_learning_enabled,
                "port_security": self.port_security_enabled,
                "igmp_snooping": self.igmp_snooping_enabled,
                "dhcp_option82": self.dhcp_option82_enabled,
                "pppoe_plus": self.pppoe_plus_enabled
            }
        }