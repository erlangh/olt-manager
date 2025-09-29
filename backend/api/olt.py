"""
OLT management API endpoints.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models.olt import OLT, OLTPort, OLTStatus, OLTType, PortStatus, PortType
from ..models.ont import ONT
from ..models.alarm import Alarm
from ..models.performance_data import PerformanceData
from ..auth.dependencies import get_current_active_user, require_operator_or_admin, require_admin
from ..models.user import User
from .schemas.olt import (
    OLTCreate, OLTUpdate, OLTResponse, OLTListResponse,
    OLTPortCreate, OLTPortUpdate, OLTPortResponse,
    OLTStatsResponse, OLTHealthResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/olts", tags=["OLT Management"])


@router.get("/", response_model=OLTListResponse)
async def list_olts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by name, IP, or location"),
    status: Optional[OLTStatus] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of OLTs with filtering and pagination."""
    try:
        query = db.query(OLT)
        
        # Apply filters
        if search:
            search_filter = or_(
                OLT.name.ilike(f"%{search}%"),
                OLT.ip_address.ilike(f"%{search}%"),
                OLT.location.ilike(f"%{search}%"),
                OLT.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if status:
            query = query.filter(OLT.status == status)
        
        if location:
            query = query.filter(OLT.location.ilike(f"%{location}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        olts = query.offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(olts)} OLTs for user {current_user.username}")
        
        return OLTListResponse(
            olts=[OLTResponse.from_orm(olt) for olt in olts],
            total=total,
            page=skip // limit + 1,
            per_page=limit,
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error listing OLTs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OLTs"
        )


@router.post("/", response_model=OLTResponse, status_code=status.HTTP_201_CREATED)
async def create_olt(
    olt_data: OLTCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Create a new OLT."""
    try:
        # Check if OLT with same IP already exists
        existing_olt = db.query(OLT).filter(OLT.ip_address == olt_data.ip_address).first()
        if existing_olt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OLT with IP address {olt_data.ip_address} already exists"
            )
        
        # Create new OLT
        olt = OLT(**olt_data.dict())
        db.add(olt)
        db.commit()
        db.refresh(olt)
        
        # Schedule background task to discover OLT configuration
        background_tasks.add_task(discover_olt_configuration, olt.id)
        
        logger.info(f"Created OLT {olt.name} by user {current_user.username}")
        
        return OLTResponse.from_orm(olt)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating OLT: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OLT"
        )


@router.get("/{olt_id}", response_model=OLTResponse)
async def get_olt(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get OLT by ID."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        logger.debug(f"Retrieved OLT {olt.name} for user {current_user.username}")
        return OLTResponse.from_orm(olt)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OLT"
        )


@router.put("/{olt_id}", response_model=OLTResponse)
async def update_olt(
    olt_id: int,
    olt_data: OLTUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Update OLT."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Check if IP address is being changed and if it conflicts
        if olt_data.ip_address and olt_data.ip_address != olt.ip_address:
            existing_olt = db.query(OLT).filter(
                and_(OLT.ip_address == olt_data.ip_address, OLT.id != olt_id)
            ).first()
            if existing_olt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"OLT with IP address {olt_data.ip_address} already exists"
                )
        
        # Update OLT fields
        update_data = olt_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(olt, field, value)
        
        db.commit()
        db.refresh(olt)
        
        logger.info(f"Updated OLT {olt.name} by user {current_user.username}")
        
        return OLTResponse.from_orm(olt)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update OLT"
        )


@router.delete("/{olt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_olt(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete OLT."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Check if OLT has active ONTs
        active_onts = db.query(ONT).filter(
            and_(ONT.olt_id == olt_id, ONT.status != "offline")
        ).count()
        
        if active_onts > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete OLT with {active_onts} active ONTs"
            )
        
        db.delete(olt)
        db.commit()
        
        logger.info(f"Deleted OLT {olt.name} by user {current_user.username}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete OLT"
        )


@router.get("/{olt_id}/ports", response_model=List[OLTPortResponse])
async def get_olt_ports(
    olt_id: int,
    port_type: Optional[PortType] = Query(None, description="Filter by port type"),
    status: Optional[PortStatus] = Query(None, description="Filter by port status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get OLT ports."""
    try:
        # Verify OLT exists
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        query = db.query(OLTPort).filter(OLTPort.olt_id == olt_id)
        
        if port_type:
            query = query.filter(OLTPort.port_type == port_type)
        
        if status:
            query = query.filter(OLTPort.status == status)
        
        ports = query.all()
        
        logger.debug(f"Retrieved {len(ports)} ports for OLT {olt_id}")
        
        return [OLTPortResponse.from_orm(port) for port in ports]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ports for OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OLT ports"
        )


@router.post("/{olt_id}/ports", response_model=OLTPortResponse, status_code=status.HTTP_201_CREATED)
async def create_olt_port(
    olt_id: int,
    port_data: OLTPortCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Create OLT port."""
    try:
        # Verify OLT exists
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Check if port already exists
        existing_port = db.query(OLTPort).filter(
            and_(
                OLTPort.olt_id == olt_id,
                OLTPort.slot_number == port_data.slot_number,
                OLTPort.port_number == port_data.port_number
            )
        ).first()
        
        if existing_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Port {port_data.slot_number}/{port_data.port_number} already exists"
            )
        
        # Create port
        port = OLTPort(olt_id=olt_id, **port_data.dict())
        db.add(port)
        db.commit()
        db.refresh(port)
        
        logger.info(f"Created port {port.slot_number}/{port.port_number} for OLT {olt_id}")
        
        return OLTPortResponse.from_orm(port)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating port for OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OLT port"
        )


@router.get("/{olt_id}/stats", response_model=OLTStatsResponse)
async def get_olt_stats(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get OLT statistics."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Get port statistics
        total_ports = db.query(OLTPort).filter(OLTPort.olt_id == olt_id).count()
        active_ports = db.query(OLTPort).filter(
            and_(OLTPort.olt_id == olt_id, OLTPort.status == PortStatus.UP)
        ).count()
        
        # Get ONT statistics
        total_onts = db.query(ONT).filter(ONT.olt_id == olt_id).count()
        online_onts = db.query(ONT).filter(
            and_(ONT.olt_id == olt_id, ONT.status == "online")
        ).count()
        
        # Get alarm statistics
        active_alarms = db.query(Alarm).filter(
            and_(Alarm.olt_id == olt_id, Alarm.status == "active")
        ).count()
        
        stats = OLTStatsResponse(
            olt_id=olt_id,
            total_ports=total_ports,
            active_ports=active_ports,
            total_onts=total_onts,
            online_onts=online_onts,
            active_alarms=active_alarms,
            cpu_usage=olt.cpu_usage or 0.0,
            memory_usage=olt.memory_usage or 0.0,
            temperature=olt.temperature or 0.0,
            uptime_seconds=olt.uptime_seconds or 0
        )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get OLT statistics"
        )


@router.get("/{olt_id}/health", response_model=OLTHealthResponse)
async def get_olt_health(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get OLT health status."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Determine health status based on various factors
        health_score = 100
        issues = []
        
        # Check connectivity
        if olt.status != OLTStatus.ONLINE:
            health_score -= 50
            issues.append(f"OLT is {olt.status}")
        
        # Check CPU usage
        if olt.cpu_usage and olt.cpu_usage > 80:
            health_score -= 20
            issues.append(f"High CPU usage: {olt.cpu_usage}%")
        
        # Check memory usage
        if olt.memory_usage and olt.memory_usage > 80:
            health_score -= 20
            issues.append(f"High memory usage: {olt.memory_usage}%")
        
        # Check temperature
        if olt.temperature and olt.temperature > 70:
            health_score -= 15
            issues.append(f"High temperature: {olt.temperature}°C")
        
        # Check for active alarms
        critical_alarms = db.query(Alarm).filter(
            and_(
                Alarm.olt_id == olt_id,
                Alarm.status == "active",
                Alarm.severity.in_(["critical", "major"])
            )
        ).count()
        
        if critical_alarms > 0:
            health_score -= 30
            issues.append(f"{critical_alarms} critical/major alarms")
        
        # Determine overall health
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 70:
            health_status = "good"
        elif health_score >= 50:
            health_status = "fair"
        elif health_score >= 30:
            health_status = "poor"
        else:
            health_status = "critical"
        
        health = OLTHealthResponse(
            olt_id=olt_id,
            health_status=health_status,
            health_score=max(0, health_score),
            issues=issues,
            last_check=olt.last_seen or olt.updated_at
        )
        
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health for OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get OLT health status"
        )


@router.post("/{olt_id}/discover", status_code=status.HTTP_202_ACCEPTED)
async def discover_olt(
    olt_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Trigger OLT discovery process."""
    try:
        olt = db.query(OLT).filter(OLT.id == olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OLT not found"
            )
        
        # Schedule background discovery task
        background_tasks.add_task(discover_olt_configuration, olt_id)
        
        logger.info(f"Triggered discovery for OLT {olt_id} by user {current_user.username}")
        
        return {"message": "OLT discovery started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering discovery for OLT {olt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger OLT discovery"
        )


async def discover_olt_configuration(olt_id: int):
    """Background task to discover OLT configuration via SNMP."""
    # This would be implemented with actual SNMP discovery logic
    logger.info(f"Starting discovery for OLT {olt_id}")
    # Implementation would go here
    pass