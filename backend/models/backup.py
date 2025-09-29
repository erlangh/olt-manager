"""
Backup model for configuration backups and restore operations.
"""

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base


class BackupType(str, enum.Enum):
    """Backup types."""
    FULL_CONFIG = "full_config"
    RUNNING_CONFIG = "running_config"
    STARTUP_CONFIG = "startup_config"
    SYSTEM_CONFIG = "system_config"
    USER_CONFIG = "user_config"
    SECURITY_CONFIG = "security_config"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(str, enum.Enum):
    """Backup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"
    DELETED = "deleted"


class BackupTrigger(str, enum.Enum):
    """Backup trigger types."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PRE_CHANGE = "pre_change"
    POST_CHANGE = "post_change"
    ALARM_TRIGGERED = "alarm_triggered"
    AUTO_DISCOVERY = "auto_discovery"
    SYSTEM_EVENT = "system_event"


class RestoreStatus(str, enum.Enum):
    """Restore operation status."""
    NOT_RESTORED = "not_restored"
    RESTORE_PENDING = "restore_pending"
    RESTORE_IN_PROGRESS = "restore_in_progress"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    RESTORE_PARTIAL = "restore_partial"


class Backup(Base):
    """Backup model for configuration backups and restore operations."""
    
    __tablename__ = "backups"
    
    # Backup identification
    backup_name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    backup_type = Column(Enum(BackupType), nullable=False, index=True)
    
    # Source device
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=False, index=True)
    
    # Backup content
    backup_data = Column(Text, nullable=False)  # Configuration data
    backup_format = Column(String(20), default="json", nullable=False)  # json, xml, cli
    compression_type = Column(String(20), nullable=True)  # gzip, zip, none
    
    # Backup metadata
    backup_size = Column(Integer, nullable=False, default=0)  # Bytes
    compressed_size = Column(Integer, nullable=True)  # Bytes (if compressed)
    checksum = Column(String(64), nullable=True)  # SHA-256 checksum
    
    # Status and lifecycle
    status = Column(Enum(BackupStatus), default=BackupStatus.PENDING, nullable=False, index=True)
    trigger = Column(Enum(BackupTrigger), default=BackupTrigger.MANUAL, nullable=False)
    
    # Timing information
    backup_started_at = Column(String(255), nullable=True)
    backup_completed_at = Column(String(255), nullable=True)
    backup_duration = Column(Float, nullable=True)  # Seconds
    
    # User information
    created_by = Column(String(100), nullable=True)  # Username
    scheduled_by = Column(String(100), nullable=True)  # Username (for scheduled backups)
    
    # Storage information
    file_path = Column(String(500), nullable=True)
    storage_location = Column(String(200), nullable=True)  # local, s3, ftp, etc.
    remote_url = Column(String(500), nullable=True)
    
    # Validation and integrity
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_errors = Column(Text, nullable=True)  # JSON formatted errors
    integrity_check_passed = Column(Boolean, nullable=True)
    
    # Versioning
    version_number = Column(String(50), nullable=True)
    parent_backup_id = Column(Integer, nullable=True)  # For incremental backups
    baseline_backup_id = Column(Integer, nullable=True)  # For differential backups
    
    # Restore information
    restore_status = Column(Enum(RestoreStatus), default=RestoreStatus.NOT_RESTORED, nullable=False)
    last_restored_at = Column(String(255), nullable=True)
    restored_by = Column(String(100), nullable=True)  # Username
    restore_count = Column(Integer, default=0, nullable=False)
    
    # Retention and archival
    retention_period = Column(Integer, nullable=True)  # Days
    expires_at = Column(String(255), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    archive_location = Column(String(500), nullable=True)
    
    # Backup scheduling
    schedule_expression = Column(String(100), nullable=True)  # Cron expression
    next_backup_at = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    
    # Change tracking
    config_changes_count = Column(Integer, nullable=True)
    significant_changes = Column(Text, nullable=True)  # JSON list of significant changes
    change_summary = Column(Text, nullable=True)
    
    # Additional metadata
    tags = Column(Text, nullable=True)  # JSON formatted tags
    notes = Column(Text, nullable=True)
    external_reference = Column(String(200), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Relationships
    olt = relationship("OLT", back_populates="backups")
    
    def __repr__(self):
        return f"<Backup(name='{self.backup_name}', type='{self.backup_type}', status='{self.status}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if backup is completed successfully."""
        return self.status == BackupStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if backup failed."""
        return self.status == BackupStatus.FAILED
    
    @property
    def can_be_restored(self) -> bool:
        """Check if backup can be restored."""
        return (
            self.status == BackupStatus.COMPLETED and
            self.is_validated and
            not self.is_archived
        )
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if not self.compressed_size or self.backup_size == 0:
            return 1.0
        return self.compressed_size / self.backup_size
    
    @property
    def size_mb(self) -> float:
        """Get backup size in MB."""
        return self.backup_size / (1024 * 1024)
    
    @property
    def age_days(self) -> float:
        """Calculate backup age in days."""
        from datetime import datetime
        try:
            created_time = datetime.fromisoformat(self.created_at.isoformat())
            now = datetime.now()
            return (now - created_time).total_seconds() / (24 * 3600)
        except:
            return 0.0
    
    @property
    def is_expired(self) -> bool:
        """Check if backup is expired."""
        if not self.expires_at:
            return False
        
        from datetime import datetime
        try:
            expiry_time = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now(expiry_time.tzinfo) > expiry_time
        except:
            return False
    
    @property
    def days_until_expiry(self) -> int:
        """Get days until backup expires."""
        if not self.expires_at:
            return -1
        
        from datetime import datetime
        try:
            expiry_time = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            now = datetime.now(expiry_time.tzinfo)
            delta = expiry_time - now
            return max(0, delta.days)
        except:
            return -1
    
    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of backup data."""
        import hashlib
        if not self.backup_data:
            return ""
        
        checksum = hashlib.sha256(self.backup_data.encode('utf-8')).hexdigest()
        self.checksum = checksum
        return checksum
    
    def validate_backup(self) -> dict:
        """Validate backup data integrity."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check if backup data exists
        if not self.backup_data:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Backup data is empty")
        
        # Verify checksum
        if self.checksum:
            calculated_checksum = self.calculate_checksum()
            if calculated_checksum != self.checksum:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Checksum mismatch - backup may be corrupted")
        
        # Format validation
        if self.backup_format == "json":
            try:
                import json
                json.loads(self.backup_data)
            except json.JSONDecodeError as e:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Invalid JSON format: {str(e)}")
        
        # Size validation
        actual_size = len(self.backup_data.encode('utf-8'))
        if abs(actual_size - self.backup_size) > 100:  # Allow 100 bytes difference
            validation_result["warnings"].append("Backup size mismatch")
        
        self.is_validated = validation_result["is_valid"]
        self.integrity_check_passed = validation_result["is_valid"]
        
        if not validation_result["is_valid"]:
            import json
            self.validation_errors = json.dumps(validation_result["errors"])
        
        return validation_result
    
    def get_backup_summary(self) -> dict:
        """Get backup summary information."""
        return {
            "name": self.backup_name,
            "type": self.backup_type,
            "status": self.status,
            "size_mb": self.size_mb,
            "age_days": self.age_days,
            "is_validated": self.is_validated,
            "can_be_restored": self.can_be_restored,
            "restore_count": self.restore_count,
            "created_by": self.created_by,
            "backup_completed_at": self.backup_completed_at,
            "checksum": self.checksum[:8] if self.checksum else None,
            "expires_in_days": self.days_until_expiry
        }
    
    def mark_as_restored(self, username: str) -> None:
        """Mark backup as restored."""
        from datetime import datetime
        self.restore_status = RestoreStatus.RESTORE_COMPLETED
        self.last_restored_at = datetime.now().isoformat()
        self.restored_by = username
        self.restore_count += 1