"""
Configuration model for storing device configurations and settings.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ConfigurationType(str, enum.Enum):
    """Configuration types."""
    DEVICE_CONFIG = "device_config"
    INTERFACE_CONFIG = "interface_config"
    VLAN_CONFIG = "vlan_config"
    QOS_CONFIG = "qos_config"
    SECURITY_CONFIG = "security_config"
    ROUTING_CONFIG = "routing_config"
    SNMP_CONFIG = "snmp_config"
    SYSTEM_CONFIG = "system_config"
    SERVICE_CONFIG = "service_config"
    BACKUP_CONFIG = "backup_config"


class ConfigurationStatus(str, enum.Enum):
    """Configuration status."""
    ACTIVE = "active"
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLBACK = "rollback"
    ARCHIVED = "archived"


class ConfigurationSource(str, enum.Enum):
    """Configuration source."""
    MANUAL = "manual"
    TEMPLATE = "template"
    IMPORT = "import"
    BACKUP = "backup"
    AUTO_GENERATED = "auto_generated"
    DISCOVERY = "discovery"


class Configuration(Base):
    """Configuration model for storing device configurations."""
    
    __tablename__ = "configurations"
    
    # Configuration identification
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    config_type = Column(Enum(ConfigurationType), nullable=False, index=True)
    
    # Target device
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False, index=True)
    
    # Configuration content
    config_data = Column(Text, nullable=False)  # JSON or XML formatted configuration
    config_format = Column(String(20), default="json", nullable=False)  # json, xml, cli
    config_version = Column(String(50), nullable=True)
    
    # Configuration metadata
    source = Column(Enum(ConfigurationSource), default=ConfigurationSource.MANUAL, nullable=False)
    template_id = Column(String(100), nullable=True)
    template_version = Column(String(50), nullable=True)
    
    # Status and lifecycle
    status = Column(Enum(ConfigurationStatus), default=ConfigurationStatus.PENDING, nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    is_validated = Column(Boolean, default=False, nullable=False)
    
    # Application tracking
    applied_at = Column(String(255), nullable=True)
    applied_by = Column(String(100), nullable=True)  # Username
    rollback_config_id = Column(Integer, nullable=True)  # Reference to rollback configuration
    
    # Validation and testing
    validation_status = Column(String(50), nullable=True)
    validation_errors = Column(Text, nullable=True)  # JSON formatted errors
    test_results = Column(Text, nullable=True)  # JSON formatted test results
    
    # Change management
    change_request_id = Column(String(100), nullable=True)
    approval_status = Column(String(50), nullable=True)
    approved_by = Column(String(100), nullable=True)  # Username
    approved_at = Column(String(255), nullable=True)
    
    # Scheduling
    scheduled_at = Column(String(255), nullable=True)
    maintenance_window = Column(String(100), nullable=True)
    auto_rollback_enabled = Column(Boolean, default=True, nullable=False)
    rollback_timeout = Column(Integer, default=300, nullable=False)  # Seconds
    
    # Impact assessment
    impact_level = Column(String(20), nullable=True)  # low, medium, high, critical
    affected_services = Column(Text, nullable=True)  # JSON list of affected services
    downtime_estimate = Column(Integer, nullable=True)  # Minutes
    
    # Configuration comparison
    parent_config_id = Column(Integer, nullable=True)  # Previous configuration
    config_diff = Column(Text, nullable=True)  # Diff from parent configuration
    checksum = Column(String(64), nullable=True)  # SHA-256 checksum
    
    # Backup and archival
    backup_location = Column(String(500), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    archive_location = Column(String(500), nullable=True)
    retention_period = Column(Integer, nullable=True)  # Days
    
    # Additional metadata
    tags = Column(Text, nullable=True)  # JSON formatted tags
    notes = Column(Text, nullable=True)
    external_reference = Column(String(200), nullable=True)
    
    # Relationships
    olt = relationship("OLT", back_populates="configurations")
    
    def __repr__(self):
        return f"<Configuration(name='{self.name}', type='{self.config_type}', status='{self.status}')>"
    
    @property
    def is_pending_approval(self) -> bool:
        """Check if configuration is pending approval."""
        return self.approval_status == "pending"
    
    @property
    def is_approved(self) -> bool:
        """Check if configuration is approved."""
        return self.approval_status == "approved"
    
    @property
    def can_be_applied(self) -> bool:
        """Check if configuration can be applied."""
        return (
            self.status == ConfigurationStatus.PENDING and
            self.is_validated and
            (self.approval_status == "approved" or self.approval_status is None)
        )
    
    @property
    def is_scheduled(self) -> bool:
        """Check if configuration is scheduled for future application."""
        if not self.scheduled_at:
            return False
        
        from datetime import datetime
        try:
            scheduled_time = datetime.fromisoformat(self.scheduled_at.replace('Z', '+00:00'))
            return scheduled_time > datetime.now(scheduled_time.tzinfo)
        except:
            return False
    
    @property
    def config_size_kb(self) -> float:
        """Get configuration size in KB."""
        if not self.config_data:
            return 0.0
        return len(self.config_data.encode('utf-8')) / 1024
    
    @property
    def age_hours(self) -> float:
        """Calculate configuration age in hours."""
        from datetime import datetime
        try:
            created_time = datetime.fromisoformat(self.created_at.isoformat())
            now = datetime.now()
            return (now - created_time).total_seconds() / 3600
        except:
            return 0.0
    
    def validate_configuration(self) -> dict:
        """Validate configuration data."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic validation
        if not self.config_data:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Configuration data is empty")
        
        # Format validation
        if self.config_format == "json":
            try:
                import json
                json.loads(self.config_data)
            except json.JSONDecodeError as e:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Invalid JSON format: {str(e)}")
        
        # Size validation
        if self.config_size_kb > 1024:  # 1MB limit
            validation_result["warnings"].append("Configuration size is large (>1MB)")
        
        self.is_validated = validation_result["is_valid"]
        if not validation_result["is_valid"]:
            import json
            self.validation_errors = json.dumps(validation_result["errors"])
        
        return validation_result
    
    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of configuration data."""
        import hashlib
        if not self.config_data:
            return ""
        
        checksum = hashlib.sha256(self.config_data.encode('utf-8')).hexdigest()
        self.checksum = checksum
        return checksum
    
    def compare_with_parent(self) -> dict:
        """Compare configuration with parent configuration."""
        if not self.parent_config_id:
            return {"has_changes": True, "diff": "New configuration"}
        
        # This would typically use a proper diff algorithm
        # For now, return a simple comparison
        return {
            "has_changes": True,
            "diff": "Configuration comparison not implemented",
            "added_lines": 0,
            "removed_lines": 0,
            "modified_lines": 0
        }
    
    def get_config_summary(self) -> dict:
        """Get configuration summary."""
        return {
            "name": self.name,
            "type": self.config_type,
            "status": self.status,
            "size_kb": self.config_size_kb,
            "is_validated": self.is_validated,
            "is_active": self.is_active,
            "applied_at": self.applied_at,
            "applied_by": self.applied_by,
            "age_hours": self.age_hours,
            "checksum": self.checksum[:8] if self.checksum else None
        }