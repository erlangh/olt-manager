"""
ONT management API endpoints.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models.ont import ONT, ONTService, ONTStatus, ONTType, ServiceStatus
from ..models.olt import OLT, OLTPort
from ..models.service_profile import ServiceProfile
from ..models.alarm import Alarm
from ..models.performance_data import PerformanceData
from ..auth.dependencies import get_current_active_user, require_operator_or_admin, require_admin
from ..models.user import User
from .schemas.ont import (
    ONTCreate, ONTUpdate, ONTResponse, ONTListResponse,
    ONTServiceCreate, ONTServiceUpdate, ONTServiceResponse,
    ONTStatsResponse, ONTSignalResponse, ONTProvisionRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onts", tags=["ONT Management"])


@router.get("/", response_model=ONTListResponse)
async def list_onts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by serial number, customer name, or location"),
    status: Optional[ONTStatus] = Query(None, description="Filter by status"),
    olt_id: Optional[int] = Query(None, description="Filter by OLT ID"),
    port_id: Optional[int] = Query(None, description="Filter by OLT port ID"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of ONTs with filtering and pagination."""
    try:
        query = db.query(ONT)
        
        # Apply filters
        if search:
            search_filter = or_(
                ONT.serial_number.ilike(f"%{search}%"),
                ONT.customer_name.ilike(f"%{search}%"),
                ONT.installation_address.ilike(f"%{search}%"),
                ONT.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if status:
            query = query.filter(ONT.status == status)
        
        if olt_id:
            query = query.filter(ONT.olt_id == olt_id)
        
        if port_id:
            query = query.filter(ONT.olt_port_id == port_id)
        
        if customer_name:
            query = query.filter(ONT.customer_name.ilike(f"%{customer_name}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        onts = query.offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(onts)} ONTs for user {current_user.username}")
        
        return ONTListResponse(
            onts=[ONTResponse.from_orm(ont) for ont in onts],
            total=total,
            page=skip // limit + 1,
            per_page=limit,
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error listing ONTs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ONTs"
        )


@router.post("/", response_model=ONTResponse, status_code=status.HTTP_201_CREATED)
async def create_ont(
    ont_data: ONTCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Create a new ONT."""
    try:
        # Check if ONT with same serial number already exists
        existing_ont = db.query(ONT).filter(ONT.serial_number == ont_data.serial_number).first()
        if existing_ont:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ONT with serial number {ont_data.serial_number} already exists"
            )
        
        # Verify OLT exists
        olt = db.query(OLT).filter(OLT.id == ont_data.olt_id).first()
        if not olt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OLT not found"
            )
        
        # Verify OLT port exists if specified
        if ont_data.olt_port_id:
            port = db.query(OLTPort).filter(
                and_(OLTPort.id == ont_data.olt_port_id, OLTPort.olt_id == ont_data.olt_id)
            ).first()
            if not port:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OLT port not found or doesn't belong to specified OLT"
                )
        
        # Create new ONT
        ont = ONT(**ont_data.dict())
        db.add(ont)
        db.commit()
        db.refresh(ont)
        
        # Schedule background task to provision ONT
        background_tasks.add_task(provision_ont, ont.id)
        
        logger.info(f"Created ONT {ont.serial_number} by user {current_user.username}")
        
        return ONTResponse.from_orm(ont)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating ONT: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ONT"
        )


@router.get("/{ont_id}", response_model=ONTResponse)
async def get_ont(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get ONT by ID."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        logger.debug(f"Retrieved ONT {ont.serial_number} for user {current_user.username}")
        return ONTResponse.from_orm(ont)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ONT"
        )


@router.put("/{ont_id}", response_model=ONTResponse)
async def update_ont(
    ont_id: int,
    ont_data: ONTUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Update ONT."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Check if serial number is being changed and if it conflicts
        if ont_data.serial_number and ont_data.serial_number != ont.serial_number:
            existing_ont = db.query(ONT).filter(
                and_(ONT.serial_number == ont_data.serial_number, ONT.id != ont_id)
            ).first()
            if existing_ont:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ONT with serial number {ont_data.serial_number} already exists"
                )
        
        # Update ONT fields
        update_data = ont_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ont, field, value)
        
        db.commit()
        db.refresh(ont)
        
        logger.info(f"Updated ONT {ont.serial_number} by user {current_user.username}")
        
        return ONTResponse.from_orm(ont)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ONT"
        )


@router.delete("/{ont_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ont(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete ONT."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Check if ONT has active services
        active_services = db.query(ONTService).filter(
            and_(ONTService.ont_id == ont_id, ONTService.status == ServiceStatus.ACTIVE)
        ).count()
        
        if active_services > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete ONT with {active_services} active services"
            )
        
        db.delete(ont)
        db.commit()
        
        logger.info(f"Deleted ONT {ont.serial_number} by user {current_user.username}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete ONT"
        )


@router.get("/{ont_id}/services", response_model=List[ONTServiceResponse])
async def get_ont_services(
    ont_id: int,
    status: Optional[ServiceStatus] = Query(None, description="Filter by service status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get ONT services."""
    try:
        # Verify ONT exists
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        query = db.query(ONTService).filter(ONTService.ont_id == ont_id)
        
        if status:
            query = query.filter(ONTService.status == status)
        
        services = query.all()
        
        logger.debug(f"Retrieved {len(services)} services for ONT {ont_id}")
        
        return [ONTServiceResponse.from_orm(service) for service in services]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving services for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ONT services"
        )


@router.post("/{ont_id}/services", response_model=ONTServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_ont_service(
    ont_id: int,
    service_data: ONTServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Create ONT service."""
    try:
        # Verify ONT exists
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Verify service profile exists
        if service_data.service_profile_id:
            profile = db.query(ServiceProfile).filter(
                ServiceProfile.id == service_data.service_profile_id
            ).first()
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Service profile not found"
                )
        
        # Create service
        service = ONTService(ont_id=ont_id, **service_data.dict())
        db.add(service)
        db.commit()
        db.refresh(service)
        
        logger.info(f"Created service for ONT {ont_id}")
        
        return ONTServiceResponse.from_orm(service)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating service for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ONT service"
        )


@router.get("/{ont_id}/stats", response_model=ONTStatsResponse)
async def get_ont_stats(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get ONT statistics."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Get service statistics
        total_services = db.query(ONTService).filter(ONTService.ont_id == ont_id).count()
        active_services = db.query(ONTService).filter(
            and_(ONTService.ont_id == ont_id, ONTService.status == ServiceStatus.ACTIVE)
        ).count()
        
        # Get alarm statistics
        active_alarms = db.query(Alarm).filter(
            and_(Alarm.ont_id == ont_id, Alarm.status == "active")
        ).count()
        
        stats = ONTStatsResponse(
            ont_id=ont_id,
            total_services=total_services,
            active_services=active_services,
            active_alarms=active_alarms,
            rx_power=ont.rx_power or 0.0,
            tx_power=ont.tx_power or 0.0,
            distance=ont.distance or 0,
            uptime_seconds=ont.uptime_seconds or 0,
            rx_bytes=ont.rx_bytes or 0,
            tx_bytes=ont.tx_bytes or 0
        )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ONT statistics"
        )


@router.get("/{ont_id}/signal", response_model=ONTSignalResponse)
async def get_ont_signal(
    ont_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get ONT signal information."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Determine signal quality based on power levels
        signal_quality = "unknown"
        if ont.rx_power is not None:
            if ont.rx_power >= -20:
                signal_quality = "excellent"
            elif ont.rx_power >= -25:
                signal_quality = "good"
            elif ont.rx_power >= -28:
                signal_quality = "fair"
            else:
                signal_quality = "poor"
        
        signal = ONTSignalResponse(
            ont_id=ont_id,
            rx_power=ont.rx_power,
            tx_power=ont.tx_power,
            voltage=ont.voltage,
            temperature=ont.temperature,
            distance=ont.distance,
            signal_quality=signal_quality,
            last_update=ont.updated_at
        )
        
        return signal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ONT signal information"
        )


@router.post("/{ont_id}/provision", status_code=status.HTTP_202_ACCEPTED)
async def provision_ont_endpoint(
    ont_id: int,
    provision_data: ONTProvisionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Provision ONT with services."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Schedule background provisioning task
        background_tasks.add_task(
            provision_ont_with_services, 
            ont_id, 
            provision_data.service_profile_ids,
            provision_data.force_reprovision
        )
        
        logger.info(f"Triggered provisioning for ONT {ont_id} by user {current_user.username}")
        
        return {"message": "ONT provisioning started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering provisioning for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger ONT provisioning"
        )


@router.post("/{ont_id}/reboot", status_code=status.HTTP_202_ACCEPTED)
async def reboot_ont(
    ont_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)
):
    """Reboot ONT."""
    try:
        ont = db.query(ONT).filter(ONT.id == ont_id).first()
        if not ont:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ONT not found"
            )
        
        # Schedule background reboot task
        background_tasks.add_task(reboot_ont_task, ont_id)
        
        logger.info(f"Triggered reboot for ONT {ont_id} by user {current_user.username}")
        
        return {"message": "ONT reboot initiated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering reboot for ONT {ont_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger ONT reboot"
        )


async def provision_ont(ont_id: int):
    """Background task to provision ONT via SNMP."""
    logger.info(f"Starting provisioning for ONT {ont_id}")
    # Implementation would go here with actual SNMP provisioning logic
    pass


async def provision_ont_with_services(ont_id: int, service_profile_ids: List[int], force_reprovision: bool = False):
    """Background task to provision ONT with specific services."""
    logger.info(f"Starting service provisioning for ONT {ont_id} with profiles {service_profile_ids}")
    # Implementation would go here
    pass


async def reboot_ont_task(ont_id: int):
    """Background task to reboot ONT via SNMP."""
    logger.info(f"Rebooting ONT {ont_id}")
    # Implementation would go here with actual SNMP reboot command
    pass