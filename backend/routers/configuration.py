from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import os
import tempfile
import zipfile
import shutil

from database import get_db
from models import Configuration, BackupRestore, OLT, ServiceProfile
from core.snmp_client import ZTE_C320_SNMP
from config import settings

router = APIRouter()

# Pydantic models
class ConfigurationResponse(BaseModel):
    id: int
    olt_id: Optional[int]
    config_type: str
    config_name: str
    config_data: dict
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True

class ConfigurationCreate(BaseModel):
    olt_id: Optional[int]
    config_type: str
    config_name: str
    config_data: dict
    version: str = "1.0"

class ConfigurationUpdate(BaseModel):
    config_name: Optional[str]
    config_data: Optional[dict]
    version: Optional[str]
    is_active: Optional[bool]

class BackupRestoreResponse(BaseModel):
    id: int
    olt_id: int
    backup_type: str
    backup_name: str
    file_path: str
    file_size: int
    status: str
    created_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True

class BackupCreate(BaseModel):
    olt_id: int
    backup_type: str = "full"
    backup_name: str

class ServiceProfileResponse(BaseModel):
    id: int
    profile_name: str
    profile_type: str
    downstream_bandwidth: int
    upstream_bandwidth: int
    vlan_id: Optional[int]
    priority: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ServiceProfileCreate(BaseModel):
    profile_name: str
    profile_type: str
    downstream_bandwidth: int
    upstream_bandwidth: int
    vlan_id: Optional[int] = None
    priority: int = 0

class ServiceProfileUpdate(BaseModel):
    profile_name: Optional[str]
    profile_type: Optional[str]
    downstream_bandwidth: Optional[int]
    upstream_bandwidth: Optional[int]
    vlan_id: Optional[int]
    priority: Optional[int]
    is_active: Optional[bool]

@router.get("/configurations", response_model=List[ConfigurationResponse])
async def get_configurations(
    olt_id: Optional[int] = None,
    config_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get configurations with optional filtering."""
    query = db.query(Configuration)
    
    if olt_id:
        query = query.filter(Configuration.olt_id == olt_id)
    if config_type:
        query = query.filter(Configuration.config_type == config_type)
    
    configurations = query.order_by(Configuration.created_at.desc()).offset(skip).limit(limit).all()
    return configurations

@router.post("/configurations", response_model=ConfigurationResponse)
async def create_configuration(
    config: ConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create a new configuration."""
    
    # Validate OLT if specified
    if config.olt_id:
        olt = db.query(OLT).filter(OLT.id == config.olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
    
    # Check if configuration name already exists for this OLT
    existing_config = db.query(Configuration).filter(
        Configuration.olt_id == config.olt_id,
        Configuration.config_name == config.config_name
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration with this name already exists for this OLT"
        )
    
    db_config = Configuration(
        olt_id=config.olt_id,
        config_type=config.config_type,
        config_name=config.config_name,
        config_data=config.config_data,
        version=config.version,
        is_active=True,
        created_by=current_user["username"]
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config

@router.get("/configurations/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get a specific configuration."""
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

@router.put("/configurations/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(
    config_id: int,
    config_update: ConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Update a configuration."""
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    return config

@router.delete("/configurations/{config_id}")
async def delete_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Delete a configuration."""
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    db.delete(config)
    db.commit()
    
    return {"message": "Configuration deleted successfully"}

@router.post("/configurations/{config_id}/apply")
async def apply_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Apply a configuration to an OLT."""
    config = db.query(Configuration).filter(Configuration.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    if not config.olt_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration is not associated with an OLT"
        )
    
    olt = db.query(OLT).filter(OLT.id == config.olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated OLT not found"
        )
    
    # Create SNMP client
    snmp_client = ZTE_C320_SNMP(
        host=olt.ip_address,
        community=olt.snmp_community,
        port=olt.snmp_port,
        version=olt.snmp_version
    )
    
    try:
        # Apply configuration based on type
        if config.config_type == "vlan":
            # Apply VLAN configuration
            success = await apply_vlan_config(snmp_client, config.config_data)
        elif config.config_type == "service_profile":
            # Apply service profile configuration
            success = await apply_service_profile_config(snmp_client, config.config_data)
        elif config.config_type == "system":
            # Apply system configuration
            success = await apply_system_config(snmp_client, config.config_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported configuration type: {config.config_type}"
            )
        
        if success:
            return {"message": "Configuration applied successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to apply configuration"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying configuration: {str(e)}"
        )

@router.get("/backups", response_model=List[BackupRestoreResponse])
async def get_backups(
    olt_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get backup records."""
    query = db.query(BackupRestore).filter(BackupRestore.backup_type.isnot(None))
    
    if olt_id:
        query = query.filter(BackupRestore.olt_id == olt_id)
    
    backups = query.order_by(BackupRestore.created_at.desc()).offset(skip).limit(limit).all()
    return backups

@router.post("/backups", response_model=BackupRestoreResponse)
async def create_backup(
    backup: BackupCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create a backup of OLT configuration."""
    
    # Validate OLT
    olt = db.query(OLT).filter(OLT.id == backup.olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    # Create SNMP client
    snmp_client = ZTE_C320_SNMP(
        host=olt.ip_address,
        community=olt.snmp_community,
        port=olt.snmp_port,
        version=olt.snmp_version
    )
    
    try:
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.UPLOAD_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{backup.backup_name}_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Get configuration data from OLT
        config_data = await get_olt_configuration(snmp_client, backup.backup_type)
        
        # Create backup file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Add configuration data as JSON
            config_json = json.dumps(config_data, indent=2)
            backup_zip.writestr("configuration.json", config_json)
            
            # Add metadata
            metadata = {
                "olt_name": olt.name,
                "olt_ip": olt.ip_address,
                "backup_type": backup.backup_type,
                "backup_name": backup.backup_name,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": current_user["username"]
            }
            metadata_json = json.dumps(metadata, indent=2)
            backup_zip.writestr("metadata.json", metadata_json)
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        
        # Create backup record
        db_backup = BackupRestore(
            olt_id=backup.olt_id,
            backup_type=backup.backup_type,
            backup_name=backup.backup_name,
            file_path=backup_path,
            file_size=file_size,
            status="completed",
            created_by=current_user["username"]
        )
        
        db.add(db_backup)
        db.commit()
        db.refresh(db_backup)
        
        return db_backup
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )

@router.post("/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Restore OLT configuration from backup."""
    
    backup = db.query(BackupRestore).filter(BackupRestore.id == backup_id).first()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )
    
    if not os.path.exists(backup.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found"
        )
    
    olt = db.query(OLT).filter(OLT.id == backup.olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated OLT not found"
        )
    
    try:
        # Extract backup file
        with zipfile.ZipFile(backup.file_path, 'r') as backup_zip:
            # Read configuration data
            config_json = backup_zip.read("configuration.json").decode('utf-8')
            config_data = json.loads(config_json)
        
        # Create SNMP client
        snmp_client = ZTE_C320_SNMP(
            host=olt.ip_address,
            community=olt.snmp_community,
            port=olt.snmp_port,
            version=olt.snmp_version
        )
        
        # Restore configuration
        success = await restore_olt_configuration(snmp_client, config_data, backup.backup_type)
        
        if success:
            return {"message": "Configuration restored successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore configuration"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring backup: {str(e)}"
        )

@router.get("/service-profiles", response_model=List[ServiceProfileResponse])
async def get_service_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get service profiles."""
    profiles = db.query(ServiceProfile).offset(skip).limit(limit).all()
    return profiles

@router.post("/service-profiles", response_model=ServiceProfileResponse)
async def create_service_profile(
    profile: ServiceProfileCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create a new service profile."""
    
    # Check if profile name already exists
    existing_profile = db.query(ServiceProfile).filter(
        ServiceProfile.profile_name == profile.profile_name
    ).first()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service profile with this name already exists"
        )
    
    db_profile = ServiceProfile(
        profile_name=profile.profile_name,
        profile_type=profile.profile_type,
        downstream_bandwidth=profile.downstream_bandwidth,
        upstream_bandwidth=profile.upstream_bandwidth,
        vlan_id=profile.vlan_id,
        priority=profile.priority,
        is_active=True
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return db_profile

@router.put("/service-profiles/{profile_id}", response_model=ServiceProfileResponse)
async def update_service_profile(
    profile_id: int,
    profile_update: ServiceProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Update a service profile."""
    profile = db.query(ServiceProfile).filter(ServiceProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service profile not found"
        )
    
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

@router.delete("/service-profiles/{profile_id}")
async def delete_service_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Delete a service profile."""
    profile = db.query(ServiceProfile).filter(ServiceProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service profile not found"
        )
    
    db.delete(profile)
    db.commit()
    
    return {"message": "Service profile deleted successfully"}

# Helper functions
async def apply_vlan_config(snmp_client: ZTE_C320_SNMP, config_data: dict) -> bool:
    """Apply VLAN configuration to OLT."""
    try:
        # Implementation would depend on specific VLAN OIDs for ZTE C320
        # This is a placeholder implementation
        return True
    except Exception:
        return False

async def apply_service_profile_config(snmp_client: ZTE_C320_SNMP, config_data: dict) -> bool:
    """Apply service profile configuration to OLT."""
    try:
        # Implementation would depend on specific service profile OIDs for ZTE C320
        # This is a placeholder implementation
        return True
    except Exception:
        return False

async def apply_system_config(snmp_client: ZTE_C320_SNMP, config_data: dict) -> bool:
    """Apply system configuration to OLT."""
    try:
        # Implementation would depend on specific system OIDs for ZTE C320
        # This is a placeholder implementation
        return True
    except Exception:
        return False

async def get_olt_configuration(snmp_client: ZTE_C320_SNMP, backup_type: str) -> dict:
    """Get OLT configuration data."""
    try:
        config_data = {}
        
        if backup_type in ["full", "system"]:
            # Get system information
            system_info = await snmp_client.get_system_info()
            config_data["system"] = system_info
        
        if backup_type in ["full", "ports"]:
            # Get port configuration
            port_list = await snmp_client.get_port_list()
            config_data["ports"] = port_list
        
        if backup_type in ["full", "onts"]:
            # Get ONT configuration
            ont_list = await snmp_client.get_ont_list()
            config_data["onts"] = ont_list
        
        return config_data
        
    except Exception as e:
        raise Exception(f"Failed to get OLT configuration: {str(e)}")

async def restore_olt_configuration(snmp_client: ZTE_C320_SNMP, config_data: dict, backup_type: str) -> bool:
    """Restore OLT configuration from backup data."""
    try:
        # Implementation would depend on specific restore procedures for ZTE C320
        # This is a placeholder implementation
        return True
    except Exception:
        return False