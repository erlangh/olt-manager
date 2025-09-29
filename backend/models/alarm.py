"""
Alarm model for system alerts and notifications.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
import enum

from .base import Base


class AlarmSeverity(str, enum.Enum):
    """Alarm severity levels."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFO = "info"


class AlarmType(str, enum.Enum):
    """Alarm types."""
    DEVICE_DOWN = "device_down"
    DEVICE_UP = "device_up"
    PORT_DOWN = "port_down"
    PORT_UP = "port_up"
    ONT_OFFLINE = "ont_offline"
    ONT_ONLINE = "ont_online"
    HIGH_TEMPERATURE = "high_temperature"
    LOW_SIGNAL = "low_signal"
    HIGH_ERROR_RATE = "high_error_rate"
    BANDWIDTH_EXCEEDED = "bandwidth_exceeded"
    CONFIGURATION_CHANGED = "configuration_changed"
    AUTHENTICATION_FAILED = "authentication_failed"
    BACKUP_FAILED = "backup_failed"
    SYSTEM_ERROR = "system_error"
    MAINTENANCE_REQUIRED = "maintenance_required"


class AlarmStatus(str, enum.Enum):
    """Alarm status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"
    SUPPRESSED = "suppressed"


class AlarmCategory(str, enum.Enum):
    """Alarm categories."""
    EQUIPMENT = "equipment"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    ENVIRONMENTAL = "environmental"
    NETWORK = "network"
    SERVICE = "service"


class Alarm(Base):
    """Alarm model for system alerts and notifications."""
    
    __tablename__ = "alarms"
    
    # Alarm identification
    alarm_id = Column(String(100), nullable=False, unique=True, index=True)
    sequence_number = Column(Integer, nullable=False, index=True)
    
    # Alarm classification
    alarm_type = Column(Enum(AlarmType), nullable=False, index=True)
    severity = Column(Enum(AlarmSeverity), nullable=False, index=True)
    category = Column(Enum(AlarmCategory), nullable=False, index=True)
    
    # Alarm content
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON formatted details
    
    # Source information
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=True, index=True)
    ont_id = Column(Integer, ForeignKey("onts.id"), nullable=True, index=True)
    port_id = Column(Integer, ForeignKey("olt_ports.id"), nullable=True, index=True)
    source_component = Column(String(100), nullable=True)  # Component that generated alarm
    source_ip = Column(String(45), nullable=True)
    
    # Alarm status and lifecycle
    status = Column(Enum(AlarmStatus), default=AlarmStatus.ACTIVE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    
    # Timing information
    first_occurrence = Column(String(255), nullable=False)
    last_occurrence = Column(String(255), nullable=False)
    acknowledged_at = Column(String(255), nullable=True)
    cleared_at = Column(String(255), nullable=True)
    
    # User actions
    acknowledged_by = Column(String(100), nullable=True)  # Username
    cleared_by = Column(String(100), nullable=True)       # Username
    assigned_to = Column(String(100), nullable=True)      # Username
    
    # Alarm management
    occurrence_count = Column(Integer, default=1, nullable=False)
    escalation_level = Column(Integer, default=0, nullable=False)
    auto_clear_enabled = Column(Boolean, default=True, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)
    
    # Additional information
    probable_cause = Column(String(200), nullable=True)
    recommended_action = Column(Text, nullable=True)
    impact_assessment = Column(Text, nullable=True)
    
    # Correlation and grouping
    correlation_id = Column(String(100), nullable=True, index=True)
    parent_alarm_id = Column(String(100), nullable=True)
    root_cause_alarm_id = Column(String(100), nullable=True)
    
    # External references
    ticket_number = Column(String(50), nullable=True)
    external_reference = Column(String(200), nullable=True)
    
    # Suppression and filtering
    is_suppressed = Column(Boolean, default=False, nullable=False)
    suppressed_until = Column(String(255), nullable=True)
    suppression_reason = Column(Text, nullable=True)
    
    # Relationships
    olt = relationship("OLT", back_populates="alarms")
    ont = relationship("ONT", back_populates="alarms")
    
    def __repr__(self):
        return f"<Alarm(id='{self.alarm_id}', type='{self.alarm_type}', severity='{self.severity}', status='{self.status}')>"
    
    @property
    def is_critical(self) -> bool:
        """Check if alarm is critical."""
        return self.severity == AlarmSeverity.CRITICAL
    
    @property
    def is_major(self) -> bool:
        """Check if alarm is major or critical."""
        return self.severity in [AlarmSeverity.CRITICAL, AlarmSeverity.MAJOR]
    
    @property
    def requires_immediate_attention(self) -> bool:
        """Check if alarm requires immediate attention."""
        return (
            self.is_active and 
            not self.is_acknowledged and 
            self.severity in [AlarmSeverity.CRITICAL, AlarmSeverity.MAJOR]
        )
    
    @property
    def age_hours(self) -> float:
        """Calculate alarm age in hours."""
        from datetime import datetime
        try:
            first_time = datetime.fromisoformat(self.first_occurrence.replace('Z', '+00:00'))
            now = datetime.now(first_time.tzinfo)
            return (now - first_time).total_seconds() / 3600
        except:
            return 0.0
    
    @property
    def severity_weight(self) -> int:
        """Get numeric weight for severity."""
        weights = {
            AlarmSeverity.CRITICAL: 5,
            AlarmSeverity.MAJOR: 4,
            AlarmSeverity.MINOR: 3,
            AlarmSeverity.WARNING: 2,
            AlarmSeverity.INFO: 1
        }
        return weights.get(self.severity, 0)
    
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
        elif self.source_ip:
            return f"Device {self.source_ip}"
        else:
            return "System"
    
    def acknowledge(self, username: str) -> None:
        """Acknowledge the alarm."""
        from datetime import datetime
        self.is_acknowledged = True
        self.acknowledged_by = username
        self.acknowledged_at = datetime.now().isoformat()
        if self.status == AlarmStatus.ACTIVE:
            self.status = AlarmStatus.ACKNOWLEDGED
    
    def clear(self, username: str = None) -> None:
        """Clear the alarm."""
        from datetime import datetime
        self.is_cleared = True
        self.is_active = False
        self.cleared_by = username
        self.cleared_at = datetime.now().isoformat()
        self.status = AlarmStatus.CLEARED
    
    def escalate(self) -> None:
        """Escalate the alarm."""
        self.escalation_level += 1
        if self.severity != AlarmSeverity.CRITICAL:
            # Escalate severity
            severity_order = [
                AlarmSeverity.INFO,
                AlarmSeverity.WARNING,
                AlarmSeverity.MINOR,
                AlarmSeverity.MAJOR,
                AlarmSeverity.CRITICAL
            ]
            current_index = severity_order.index(self.severity)
            if current_index < len(severity_order) - 1:
                self.severity = severity_order[current_index + 1]