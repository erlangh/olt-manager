from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, IPvAnyAddress
from datetime import datetime

from database import get_db
from models import OLT, OLTPort
from core.snmp_client import ZTE_C320_SNMP
from core.security import SecurityUtils

router = APIRouter()

# Pydantic models
class OLTCreate(BaseModel):
    name: str
    ip_address: str
    snmp_community: str = "public"
    snmp_version: str = "2c"
    snmp_port: int = 161
    location: Optional[str] = None
    description: Optional[str] = None

class OLTUpdate(BaseModel):
    name: Optional[str] = None
    snmp_community: Optional[str] = None
    snmp_version: Optional[str] = None
    snmp_port: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class OLTResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    model: str
    location: Optional[str]
    description: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class OLTPortResponse(BaseModel):
    id: int
    port_number: int
    port_type: str
    status: str
    admin_status: str
    description: Optional[str]
    max_onts: int
    current_onts: int
    
    class Config:
        from_attributes = True

class SystemInfo(BaseModel):
    sysDescr: Optional[str]
    sysUpTime: Optional[str]
    sysName: Optional[str]
    sysLocation: Optional[str]

class PerformanceData(BaseModel):
    cpuUtilization: Optional[str]
    memoryUtilization: Optional[str]
    temperature: Optional[str]
    fanStatus: Optional[str]

class ConnectionTest(BaseModel):
    ip_address: str
    snmp_community: str = "public"
    snmp_version: str = "2c"
    snmp_port: int = 161

def get_olt_by_id(db: Session, olt_id: int) -> Optional[OLT]:
    """Get OLT by ID."""
    return db.query(OLT).filter(OLT.id == olt_id).first()

def create_snmp_client(olt: OLT) -> ZTE_C320_SNMP:
    """Create SNMP client for OLT."""
    return ZTE_C320_SNMP(
        host=olt.ip_address,
        community=olt.snmp_community,
        port=olt.snmp_port,
        version=olt.snmp_version
    )

@router.get("/", response_model=List[OLTResponse])
async def get_olts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get list of all OLTs."""
    olts = db.query(OLT).offset(skip).limit(limit).all()
    return olts

@router.post("/", response_model=OLTResponse)
async def create_olt(
    olt: OLTCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create a new OLT."""
    # Check permissions
    if not SecurityUtils.check_permissions(current_user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Check if IP already exists
    existing_olt = db.query(OLT).filter(OLT.ip_address == olt.ip_address).first()
    if existing_olt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OLT with this IP address already exists"
        )
    
    # Test connection before creating
    snmp_client = ZTE_C320_SNMP(
        host=olt.ip_address,
        community=olt.snmp_community,
        port=olt.snmp_port,
        version=olt.snmp_version
    )
    
    if not await snmp_client.test_connection():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot connect to OLT with provided SNMP settings"
        )
    
    db_olt = OLT(**olt.dict())
    db_olt.last_seen = datetime.utcnow()
    db.add(db_olt)
    db.commit()
    db.refresh(db_olt)
    
    # Discover ports
    await discover_ports(db_olt.id, db)
    
    return db_olt

@router.get("/{olt_id}", response_model=OLTResponse)
async def get_olt(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get OLT by ID."""
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    return olt

@router.put("/{olt_id}", response_model=OLTResponse)
async def update_olt(
    olt_id: int,
    olt_update: OLTUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Update OLT."""
    if not SecurityUtils.check_permissions(current_user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    update_data = olt_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(olt, field, value)
    
    db.commit()
    db.refresh(olt)
    return olt

@router.delete("/{olt_id}")
async def delete_olt(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Delete OLT."""
    if not SecurityUtils.check_permissions(current_user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    db.delete(olt)
    db.commit()
    return {"message": "OLT deleted successfully"}

@router.get("/{olt_id}/system-info", response_model=SystemInfo)
async def get_system_info(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get OLT system information via SNMP."""
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    snmp_client = create_snmp_client(olt)
    try:
        system_info = await snmp_client.get_system_info()
        
        # Update last seen
        olt.last_seen = datetime.utcnow()
        db.commit()
        
        return SystemInfo(**system_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        )

@router.get("/{olt_id}/performance", response_model=PerformanceData)
async def get_performance_data(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get OLT performance data via SNMP."""
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    snmp_client = create_snmp_client(olt)
    try:
        performance_data = await snmp_client.get_performance_data()
        
        # Update last seen
        olt.last_seen = datetime.utcnow()
        db.commit()
        
        return PerformanceData(**performance_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance data: {str(e)}"
        )

@router.get("/{olt_id}/ports", response_model=List[OLTPortResponse])
async def get_olt_ports(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get OLT ports."""
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    ports = db.query(OLTPort).filter(OLTPort.olt_id == olt_id).all()
    return ports

@router.post("/{olt_id}/discover-ports")
async def discover_olt_ports(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Discover OLT ports via SNMP."""
    if not SecurityUtils.check_permissions(current_user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    try:
        await discover_ports(olt_id, db)
        return {"message": "Port discovery completed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Port discovery failed: {str(e)}"
        )

@router.post("/test-connection")
async def test_connection(
    connection_data: ConnectionTest,
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Test SNMP connection to OLT."""
    snmp_client = ZTE_C320_SNMP(
        host=connection_data.ip_address,
        community=connection_data.snmp_community,
        port=connection_data.snmp_port,
        version=connection_data.snmp_version
    )
    
    try:
        is_connected = await snmp_client.test_connection()
        if is_connected:
            system_info = await snmp_client.get_system_info()
            return {
                "success": True,
                "message": "Connection successful",
                "system_info": system_info
            }
        else:
            return {
                "success": False,
                "message": "Connection failed"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }

async def discover_ports(olt_id: int, db: Session):
    """Discover and update OLT ports."""
    olt = get_olt_by_id(db, olt_id)
    if not olt:
        return
    
    snmp_client = create_snmp_client(olt)
    ports_data = await snmp_client.get_port_list()
    
    for port_data in ports_data:
        # Check if port already exists
        existing_port = db.query(OLTPort).filter(
            OLTPort.olt_id == olt_id,
            OLTPort.port_number == int(port_data['index'])
        ).first()
        
        if not existing_port:
            # Create new port
            new_port = OLTPort(
                olt_id=olt_id,
                port_number=int(port_data['index']),
                port_type="GPON",
                status=port_data.get('ifOperStatus', 'unknown'),
                admin_status=port_data.get('ifAdminStatus', 'unknown'),
                description=port_data.get('description', f"Port {port_data['index']}")
            )
            db.add(new_port)
        else:
            # Update existing port
            existing_port.status = port_data.get('ifOperStatus', existing_port.status)
            existing_port.admin_status = port_data.get('ifAdminStatus', existing_port.admin_status)
    
    db.commit()