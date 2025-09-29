from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import ONT, OLT, OLTPort, ONTService, ServiceProfile
from core.snmp_client import ZTE_C320_SNMP
from core.security import SecurityUtils

router = APIRouter()

# Pydantic models
class ONTCreate(BaseModel):
    olt_id: int
    port_id: int
    ont_id: int
    serial_number: str
    description: Optional[str] = None
    service_profile: Optional[str] = "default"

class ONTUpdate(BaseModel):
    description: Optional[str] = None
    admin_status: Optional[str] = None
    service_profile: Optional[str] = None

class ONTResponse(BaseModel):
    id: int
    olt_id: int
    port_id: int
    ont_id: int
    serial_number: Optional[str]
    mac_address: Optional[str]
    model: Optional[str]
    vendor: Optional[str]
    firmware_version: Optional[str]
    status: str
    admin_status: str
    signal_rx: Optional[float]
    signal_tx: Optional[float]
    distance: Optional[float]
    last_seen: Optional[datetime]
    description: Optional[str]
    service_profile: Optional[str]
    
    class Config:
        from_attributes = True

class ONTServiceCreate(BaseModel):
    ont_id: int
    service_type: str  # internet, voip, iptv
    vlan_id: Optional[int] = None
    bandwidth_up: Optional[int] = None
    bandwidth_down: Optional[int] = None
    priority: int = 0

class ONTServiceResponse(BaseModel):
    id: int
    ont_id: int
    service_type: str
    vlan_id: Optional[int]
    bandwidth_up: Optional[int]
    bandwidth_down: Optional[int]
    priority: int
    status: str
    
    class Config:
        from_attributes = True

class ONTProvision(BaseModel):
    olt_id: int
    port_number: int
    ont_id: int
    serial_number: str
    profile: str = "default"
    description: Optional[str] = None

class ONTBulkOperation(BaseModel):
    ont_ids: List[int]
    operation: str  # activate, deactivate, delete
    
class SignalInfo(BaseModel):
    ont_id: int
    serial_number: str
    rx_power: Optional[float]
    tx_power: Optional[float]
    distance: Optional[float]
    status: str

def get_ont_by_id(db: Session, ont_id: int) -> Optional[ONT]:
    """Get ONT by ID."""
    return db.query(ONT).filter(ONT.id == ont_id).first()

def create_snmp_client(olt: OLT) -> ZTE_C320_SNMP:
    """Create SNMP client for OLT."""
    return ZTE_C320_SNMP(
        host=olt.ip_address,
        community=olt.snmp_community,
        port=olt.snmp_port,
        version=olt.snmp_version
    )

@router.get("/", response_model=List[ONTResponse])
async def get_onts(
    olt_id: Optional[int] = None,
    port_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get list of ONTs with optional filtering."""
    query = db.query(ONT)
    
    if olt_id:
        query = query.filter(ONT.olt_id == olt_id)
    if port_id:
        query = query.filter(ONT.port_id == port_id)
    if status:
        query = query.filter(ONT.status == status)
    
    onts = query.offset(skip).limit(limit).all()
    return onts

@router.post("/", response_model=ONTResponse)
async def create_ont(
    ont: ONTCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create/provision a new ONT."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Check if ONT already exists
    existing_ont = db.query(ONT).filter(
        ONT.olt_id == ont.olt_id,
        ONT.port_id == ont.port_id,
        ONT.ont_id == ont.ont_id
    ).first()
    
    if existing_ont:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ONT already exists at this position"
        )
    
    # Check serial number uniqueness
    if ont.serial_number:
        existing_sn = db.query(ONT).filter(ONT.serial_number == ont.serial_number).first()
        if existing_sn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ONT with this serial number already exists"
            )
    
    # Get OLT for SNMP operations
    olt = db.query(OLT).filter(OLT.id == ont.olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    # Get port info
    port = db.query(OLTPort).filter(OLTPort.id == ont.port_id).first()
    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Port not found"
        )
    
    # Provision ONT via SNMP
    snmp_client = create_snmp_client(olt)
    try:
        success = await snmp_client.provision_ont(
            port.port_number, 
            ont.ont_id, 
            ont.serial_number, 
            ont.service_profile or "default"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to provision ONT on OLT"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SNMP provisioning failed: {str(e)}"
        )
    
    # Create ONT record in database
    db_ont = ONT(**ont.dict())
    db_ont.status = "provisioned"
    db_ont.admin_status = "up"
    db.add(db_ont)
    db.commit()
    db.refresh(db_ont)
    
    return db_ont

@router.get("/{ont_id}", response_model=ONTResponse)
async def get_ont(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get ONT by ID."""
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    return ont

@router.put("/{ont_id}", response_model=ONTResponse)
async def update_ont(
    ont_id: int,
    ont_update: ONTUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Update ONT."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    
    update_data = ont_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ont, field, value)
    
    db.commit()
    db.refresh(ont)
    return ont

@router.delete("/{ont_id}")
async def delete_ont(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Delete ONT."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    
    # Get OLT and port info for SNMP operations
    olt = db.query(OLT).filter(OLT.id == ont.olt_id).first()
    port = db.query(OLTPort).filter(OLTPort.id == ont.port_id).first()
    
    if olt and port:
        # Delete ONT from OLT via SNMP
        snmp_client = create_snmp_client(olt)
        try:
            await snmp_client.delete_ont(port.port_number, ont.ont_id)
        except Exception as e:
            # Log error but continue with database deletion
            pass
    
    db.delete(ont)
    db.commit()
    return {"message": "ONT deleted successfully"}

@router.post("/provision", response_model=ONTResponse)
async def provision_ont(
    provision_data: ONTProvision,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Provision ONT with automatic port detection."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Get OLT
    olt = db.query(OLT).filter(OLT.id == provision_data.olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    # Get port by port number
    port = db.query(OLTPort).filter(
        OLTPort.olt_id == provision_data.olt_id,
        OLTPort.port_number == provision_data.port_number
    ).first()
    
    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Port not found"
        )
    
    # Create ONT
    ont_create = ONTCreate(
        olt_id=provision_data.olt_id,
        port_id=port.id,
        ont_id=provision_data.ont_id,
        serial_number=provision_data.serial_number,
        description=provision_data.description,
        service_profile=provision_data.profile
    )
    
    return await create_ont(ont_create, db, current_user)

@router.post("/bulk-operation")
async def bulk_ont_operation(
    operation_data: ONTBulkOperation,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Perform bulk operations on multiple ONTs."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    results = []
    for ont_id in operation_data.ont_ids:
        try:
            ont = get_ont_by_id(db, ont_id)
            if not ont:
                results.append({"ont_id": ont_id, "success": False, "error": "ONT not found"})
                continue
            
            if operation_data.operation == "activate":
                ont.admin_status = "up"
                db.commit()
                results.append({"ont_id": ont_id, "success": True, "message": "Activated"})
            
            elif operation_data.operation == "deactivate":
                ont.admin_status = "down"
                db.commit()
                results.append({"ont_id": ont_id, "success": True, "message": "Deactivated"})
            
            elif operation_data.operation == "delete":
                db.delete(ont)
                db.commit()
                results.append({"ont_id": ont_id, "success": True, "message": "Deleted"})
            
            else:
                results.append({"ont_id": ont_id, "success": False, "error": "Invalid operation"})
        
        except Exception as e:
            results.append({"ont_id": ont_id, "success": False, "error": str(e)})
    
    return {"results": results}

@router.get("/{ont_id}/services", response_model=List[ONTServiceResponse])
async def get_ont_services(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get ONT services."""
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    
    services = db.query(ONTService).filter(ONTService.ont_id == ont_id).all()
    return services

@router.post("/{ont_id}/services", response_model=ONTServiceResponse)
async def create_ont_service(
    ont_id: int,
    service: ONTServiceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create ONT service."""
    if not SecurityUtils.check_permissions(current_user["role"], "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    
    # Override ont_id from URL
    service.ont_id = ont_id
    
    db_service = ONTService(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    return db_service

@router.get("/discover/{olt_id}")
async def discover_onts(
    olt_id: int,
    port_number: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Discover ONTs on OLT via SNMP."""
    olt = db.query(OLT).filter(OLT.id == olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    snmp_client = create_snmp_client(olt)
    try:
        onts_data = await snmp_client.get_ont_list(port_number)
        
        discovered_onts = []
        for ont_data in onts_data:
            # Update or create ONT record
            port = db.query(OLTPort).filter(
                OLTPort.olt_id == olt_id,
                OLTPort.port_number == int(ont_data['port_id'])
            ).first()
            
            if port:
                existing_ont = db.query(ONT).filter(
                    ONT.olt_id == olt_id,
                    ONT.port_id == port.id,
                    ONT.ont_id == int(ont_data['ont_id'])
                ).first()
                
                if existing_ont:
                    # Update existing ONT
                    existing_ont.serial_number = ont_data.get('ontSerialNumber')
                    existing_ont.status = ont_data.get('ontStatus', 'unknown')
                    existing_ont.signal_rx = float(ont_data.get('ontRxPower', 0)) if ont_data.get('ontRxPower') else None
                    existing_ont.signal_tx = float(ont_data.get('ontTxPower', 0)) if ont_data.get('ontTxPower') else None
                    existing_ont.distance = float(ont_data.get('ontDistance', 0)) if ont_data.get('ontDistance') else None
                    existing_ont.model = ont_data.get('ontModel')
                    existing_ont.firmware_version = ont_data.get('ontVersion')
                    existing_ont.last_seen = datetime.utcnow()
                    db.commit()
                    discovered_onts.append(existing_ont)
                else:
                    # Create new ONT
                    new_ont = ONT(
                        olt_id=olt_id,
                        port_id=port.id,
                        ont_id=int(ont_data['ont_id']),
                        serial_number=ont_data.get('ontSerialNumber'),
                        status=ont_data.get('ontStatus', 'unknown'),
                        signal_rx=float(ont_data.get('ontRxPower', 0)) if ont_data.get('ontRxPower') else None,
                        signal_tx=float(ont_data.get('ontTxPower', 0)) if ont_data.get('ontTxPower') else None,
                        distance=float(ont_data.get('ontDistance', 0)) if ont_data.get('ontDistance') else None,
                        model=ont_data.get('ontModel'),
                        firmware_version=ont_data.get('ontVersion'),
                        last_seen=datetime.utcnow()
                    )
                    db.add(new_ont)
                    db.commit()
                    db.refresh(new_ont)
                    discovered_onts.append(new_ont)
        
        return {
            "message": f"Discovered {len(discovered_onts)} ONTs",
            "onts": [{"id": ont.id, "serial_number": ont.serial_number, "status": ont.status} for ont in discovered_onts]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ONT discovery failed: {str(e)}"
        )

@router.get("/{ont_id}/signal", response_model=SignalInfo)
async def get_ont_signal_info(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get real-time ONT signal information."""
    ont = get_ont_by_id(db, ont_id)
    if not ont:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ONT not found"
        )
    
    # Get fresh signal data via SNMP
    olt = db.query(OLT).filter(OLT.id == ont.olt_id).first()
    port = db.query(OLTPort).filter(OLTPort.id == ont.port_id).first()
    
    if olt and port:
        snmp_client = create_snmp_client(olt)
        try:
            onts_data = await snmp_client.get_ont_list(port.port_number)
            
            # Find our ONT in the results
            for ont_data in onts_data:
                if int(ont_data['ont_id']) == ont.ont_id:
                    return SignalInfo(
                        ont_id=ont.ont_id,
                        serial_number=ont.serial_number or "",
                        rx_power=float(ont_data.get('ontRxPower', 0)) if ont_data.get('ontRxPower') else None,
                        tx_power=float(ont_data.get('ontTxPower', 0)) if ont_data.get('ontTxPower') else None,
                        distance=float(ont_data.get('ontDistance', 0)) if ont_data.get('ontDistance') else None,
                        status=ont_data.get('ontStatus', 'unknown')
                    )
        except Exception:
            pass
    
    # Return cached data if SNMP fails
    return SignalInfo(
        ont_id=ont.ont_id,
        serial_number=ont.serial_number or "",
        rx_power=ont.signal_rx,
        tx_power=ont.signal_tx,
        distance=ont.distance,
        status=ont.status
    )