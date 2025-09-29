"""
Performance Data model for monitoring and metrics storage.
"""

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

from .base import Base


class MetricType(str, enum.Enum):
    """Performance metric types."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    TEMPERATURE = "temperature"
    POWER_CONSUMPTION = "power_consumption"
    BANDWIDTH_UTILIZATION = "bandwidth_utilization"
    PACKET_LOSS = "packet_loss"
    LATENCY = "latency"
    JITTER = "jitter"
    ERROR_RATE = "error_rate"
    SIGNAL_STRENGTH = "signal_strength"
    UPTIME = "uptime"
    THROUGHPUT = "throughput"
    CONNECTION_COUNT = "connection_count"
    DISK_USAGE = "disk_usage"
    NETWORK_UTILIZATION = "network_utilization"


class DataSource(str, enum.Enum):
    """Data source types."""
    SNMP = "snmp"
    CLI = "cli"
    API = "api"
    SYSLOG = "syslog"
    NETCONF = "netconf"
    SYSTEM = "system"
    CALCULATED = "calculated"


class AggregationType(str, enum.Enum):
    """Data aggregation types."""
    RAW = "raw"
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    SUM = "sum"
    COUNT = "count"
    PERCENTILE_95 = "percentile_95"
    PERCENTILE_99 = "percentile_99"


class PerformanceData(Base):
    """Performance data model for storing monitoring metrics."""
    
    __tablename__ = "performance_data"
    
    # Data identification
    metric_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(Enum(MetricType), nullable=False, index=True)
    
    # Source information
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=True, index=True)
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=True, index=True)
    port_id = Column(Integer, ForeignKey("olt_ports.id"), nullable=True, index=True)
    
    # Data source
    data_source = Column(Enum(DataSource), default=DataSource.SNMP, nullable=False)
    source_component = Column(String(100), nullable=True)
    collection_method = Column(String(50), nullable=True)
    
    # Metric values
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # e.g., %, Mbps, °C, dBm
    
    # Value context
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    threshold_warning = Column(Float, nullable=True)
    threshold_critical = Column(Float, nullable=True)
    
    # Data quality
    is_valid = Column(Boolean, default=True, nullable=False)
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    confidence_level = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Aggregation information
    aggregation_type = Column(Enum(AggregationType), default=AggregationType.RAW, nullable=False)
    aggregation_period = Column(Integer, nullable=True)  # Seconds
    sample_count = Column(Integer, default=1, nullable=False)
    
    # Timing information
    timestamp = Column(String(255), nullable=False, index=True)
    collection_time = Column(String(255), nullable=True)
    processing_time = Column(String(255), nullable=True)
    
    # Additional metadata
    tags = Column(Text, nullable=True)  # JSON formatted tags
    attributes = Column(Text, nullable=True)  # JSON formatted attributes
    context = Column(Text, nullable=True)  # Additional context information
    
    # Data retention
    retention_period = Column(Integer, nullable=True)  # Days
    is_archived = Column(Boolean, default=False, nullable=False)
    archive_location = Column(String(200), nullable=True)
    
    # Relationships
    olt = relationship("OLT", back_populates="performance_data")
    
    def __repr__(self):
        return f"<PerformanceData(metric='{self.metric_name}', value={self.value}, timestamp='{self.timestamp}')>"
    
    @property
    def is_threshold_exceeded(self) -> bool:
        """Check if value exceeds warning threshold."""
        if self.threshold_warning is None:
            return False
        return self.value > self.threshold_warning
    
    @property
    def is_critical_threshold_exceeded(self) -> bool:
        """Check if value exceeds critical threshold."""
        if self.threshold_critical is None:
            return False
        return self.value > self.threshold_critical
    
    @property
    def threshold_status(self) -> str:
        """Get threshold status."""
        if self.is_critical_threshold_exceeded:
            return "critical"
        elif self.is_threshold_exceeded:
            return "warning"
        else:
            return "normal"
    
    @property
    def formatted_value(self) -> str:
        """Get formatted value with unit."""
        if self.unit:
            return f"{self.value:.2f} {self.unit}"
        else:
            return f"{self.value:.2f}"
    
    @property
    def source_description(self) -> str:
        """Get human-readable source description."""
        if self.olt_id and self.ont_id:
            return f"ONT {self.ont_id} on OLT {self.olt_id}"
        elif self.olt_id and self.port_id:
            return f"Port {self.port_id} on OLT {self.olt_id}"
        elif self.olt_id:
            return f"OLT {self.olt_id}"
        elif self.ont_id:
            return f"ONT {self.ont_id}"
        else:
            return "System"
    
    @property
    def age_minutes(self) -> float:
        """Calculate data age in minutes."""
        from datetime import datetime
        try:
            timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            now = datetime.now(timestamp.tzinfo)
            return (now - timestamp).total_seconds() / 60
        except:
            return 0.0
    
    @property
    def is_recent(self) -> bool:
        """Check if data is recent (within last 5 minutes)."""
        return self.age_minutes <= 5.0
    
    @property
    def is_stale(self) -> bool:
        """Check if data is stale (older than 1 hour)."""
        return self.age_minutes > 60.0
    
    def calculate_percentage_of_range(self) -> float:
        """Calculate value as percentage of min-max range."""
        if self.min_value is None or self.max_value is None:
            return 0.0
        
        if self.max_value == self.min_value:
            return 100.0
        
        return ((self.value - self.min_value) / (self.max_value - self.min_value)) * 100
    
    def get_trend_indicator(self, previous_value: float) -> str:
        """Get trend indicator compared to previous value."""
        if previous_value is None:
            return "stable"
        
        change_percent = ((self.value - previous_value) / previous_value) * 100
        
        if change_percent > 5:
            return "increasing"
        elif change_percent < -5:
            return "decreasing"
        else:
            return "stable"
    
    def to_metric_dict(self) -> dict:
        """Convert to metric dictionary format."""
        return {
            "name": self.metric_name,
            "type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "source": self.source_description,
            "status": self.threshold_status,
            "formatted_value": self.formatted_value,
            "is_recent": self.is_recent,
            "quality_score": self.quality_score,
            "confidence_level": self.confidence_level
        }