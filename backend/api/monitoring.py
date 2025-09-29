"""
Monitoring API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..database.connection import get_db
from ..auth.dependencies import get_current_active_user, require_permissions
from ..models.user import User
from ..models.performance_data import PerformanceData, MetricType, DataSource, AggregationType
from ..models.alarm import Alarm, AlarmSeverity, AlarmStatus
from ..models.olt import OLT
from ..models.ont import ONT
from ..services.monitoring_service import monitoring_service
from ..services.websocket_service import notification_service
from .schemas.monitoring import (
    PerformanceDataResponse, PerformanceDataListResponse, PerformanceDataCreate,
    AlarmResponse, AlarmListResponse, AlarmCreate, AlarmUpdate, AlarmStatsResponse,
    MetricSummaryResponse, DeviceMetricsResponse, SystemHealthResponse,
    NetworkTopologyNode, NetworkTopologyEdge
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/performance-data", response_model=PerformanceDataListResponse)
async def get_performance_data(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    metric_type: Optional[MetricType] = Query(None, description="Filter by metric type"),
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get performance data with filtering options."""
    
    query = db.query(PerformanceData)
    
    # Apply filters
    if device_id:
        query = query.filter(PerformanceData.device_id == device_id)
    
    if device_type:
        query = query.filter(PerformanceData.device_type == device_type)
    
    if metric_type:
        query = query.filter(PerformanceData.metric_type == metric_type)
    
    if start_time:
        query = query.filter(PerformanceData.timestamp >= start_time)
    
    if end_time:
        query = query.filter(PerformanceData.timestamp <= end_time)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    performance_data = query.order_by(desc(PerformanceData.timestamp)).offset(offset).limit(limit).all()
    
    return PerformanceDataListResponse(
        items=performance_data,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/performance-data", response_model=PerformanceDataResponse)
async def create_performance_data(
    data: PerformanceDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["monitoring:write"]))
):
    """Create new performance data entry."""
    
    performance_data = PerformanceData(
        device_id=data.device_id,
        device_type=data.device_type,
        metric_type=data.metric_type,
        data_source=data.data_source,
        value=data.value,
        unit=data.unit,
        timestamp=data.timestamp or datetime.utcnow(),
        quality_score=data.quality_score,
        aggregation_type=data.aggregation_type,
        aggregation_window=data.aggregation_window,
        tags=data.tags,
        additional_data=data.additional_data
    )
    
    db.add(performance_data)
    db.commit()
    db.refresh(performance_data)
    
    return performance_data


@router.get("/performance-data/{data_id}", response_model=PerformanceDataResponse)
async def get_performance_data_by_id(
    data_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific performance data entry."""
    
    performance_data = db.query(PerformanceData).filter(PerformanceData.id == data_id).first()
    if not performance_data:
        raise HTTPException(status_code=404, detail="Performance data not found")
    
    return performance_data


@router.get("/metrics/summary", response_model=List[MetricSummaryResponse])
async def get_metrics_summary(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    time_range: int = Query(3600, description="Time range in seconds (default: 1 hour)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get metrics summary with aggregated statistics."""
    
    start_time = datetime.utcnow() - timedelta(seconds=time_range)
    
    query = db.query(
        PerformanceData.metric_type,
        PerformanceData.unit,
        func.count(PerformanceData.id).label('count'),
        func.avg(PerformanceData.value).label('avg_value'),
        func.min(PerformanceData.value).label('min_value'),
        func.max(PerformanceData.value).label('max_value'),
        func.stddev(PerformanceData.value).label('stddev_value')
    ).filter(PerformanceData.timestamp >= start_time)
    
    if device_id:
        query = query.filter(PerformanceData.device_id == device_id)
    
    if device_type:
        query = query.filter(PerformanceData.device_type == device_type)
    
    results = query.group_by(PerformanceData.metric_type, PerformanceData.unit).all()
    
    summaries = []
    for result in results:
        summaries.append(MetricSummaryResponse(
            metric_type=result.metric_type,
            unit=result.unit,
            count=result.count,
            avg_value=float(result.avg_value) if result.avg_value else 0.0,
            min_value=float(result.min_value) if result.min_value else 0.0,
            max_value=float(result.max_value) if result.max_value else 0.0,
            stddev_value=float(result.stddev_value) if result.stddev_value else 0.0
        ))
    
    return summaries


@router.get("/devices/{device_id}/metrics", response_model=DeviceMetricsResponse)
async def get_device_metrics(
    device_id: str,
    device_type: str = Query(..., description="Device type (olt, ont, olt_port)"),
    time_range: int = Query(3600, description="Time range in seconds"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive metrics for a specific device."""
    
    start_time = datetime.utcnow() - timedelta(seconds=time_range)
    
    # Get recent performance data
    performance_data = db.query(PerformanceData).filter(
        and_(
            PerformanceData.device_id == device_id,
            PerformanceData.device_type == device_type,
            PerformanceData.timestamp >= start_time
        )
    ).order_by(desc(PerformanceData.timestamp)).all()
    
    # Get active alarms
    active_alarms = db.query(Alarm).filter(
        and_(
            Alarm.device_id == device_id,
            Alarm.device_type == device_type,
            Alarm.status == AlarmStatus.ACTIVE
        )
    ).all()
    
    # Organize metrics by type
    metrics_by_type = {}
    for data in performance_data:
        metric_type = data.metric_type.value
        if metric_type not in metrics_by_type:
            metrics_by_type[metric_type] = []
        
        metrics_by_type[metric_type].append({
            "timestamp": data.timestamp,
            "value": data.value,
            "unit": data.unit,
            "quality_score": data.quality_score
        })
    
    # Calculate health score based on recent data and alarms
    health_score = 100.0
    if active_alarms:
        critical_alarms = sum(1 for alarm in active_alarms if alarm.severity == AlarmSeverity.CRITICAL)
        warning_alarms = sum(1 for alarm in active_alarms if alarm.severity == AlarmSeverity.WARNING)
        health_score -= (critical_alarms * 30) + (warning_alarms * 10)
        health_score = max(0.0, health_score)
    
    return DeviceMetricsResponse(
        device_id=device_id,
        device_type=device_type,
        metrics=metrics_by_type,
        health_score=health_score,
        active_alarms_count=len(active_alarms),
        last_update=performance_data[0].timestamp if performance_data else None
    )


@router.get("/alarms", response_model=AlarmListResponse)
async def get_alarms(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    severity: Optional[AlarmSeverity] = Query(None, description="Filter by severity"),
    status: Optional[AlarmStatus] = Query(None, description="Filter by status"),
    start_time: Optional[datetime] = Query(None, description="Start time for alarm range"),
    end_time: Optional[datetime] = Query(None, description="End time for alarm range"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get alarms with filtering options."""
    
    query = db.query(Alarm)
    
    # Apply filters
    if device_id:
        query = query.filter(Alarm.device_id == device_id)
    
    if device_type:
        query = query.filter(Alarm.device_type == device_type)
    
    if severity:
        query = query.filter(Alarm.severity == severity)
    
    if status:
        query = query.filter(Alarm.status == status)
    
    if start_time:
        query = query.filter(Alarm.timestamp >= start_time)
    
    if end_time:
        query = query.filter(Alarm.timestamp <= end_time)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    alarms = query.order_by(desc(Alarm.timestamp)).offset(offset).limit(limit).all()
    
    return AlarmListResponse(
        items=alarms,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/alarms", response_model=AlarmResponse)
async def create_alarm(
    alarm_data: AlarmCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["monitoring:write"]))
):
    """Create new alarm."""
    
    alarm = Alarm(
        device_id=alarm_data.device_id,
        device_type=alarm_data.device_type,
        alarm_type=alarm_data.alarm_type,
        severity=alarm_data.severity,
        status=AlarmStatus.ACTIVE,
        message=alarm_data.message,
        timestamp=datetime.utcnow(),
        additional_data=alarm_data.additional_data
    )
    
    db.add(alarm)
    db.commit()
    db.refresh(alarm)
    
    # Send alarm notification in background
    background_tasks.add_task(
        notification_service.send_alarm,
        {
            "alarm_id": alarm.id,
            "device_id": alarm.device_id,
            "device_type": alarm.device_type,
            "severity": alarm.severity.value,
            "message": alarm.message,
            "timestamp": alarm.timestamp.isoformat()
        }
    )
    
    return alarm


@router.get("/alarms/{alarm_id}", response_model=AlarmResponse)
async def get_alarm(
    alarm_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific alarm."""
    
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    return alarm


@router.put("/alarms/{alarm_id}", response_model=AlarmResponse)
async def update_alarm(
    alarm_id: str,
    alarm_update: AlarmUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["monitoring:write"]))
):
    """Update alarm status or details."""
    
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    # Update fields
    if alarm_update.status is not None:
        alarm.status = alarm_update.status
    
    if alarm_update.severity is not None:
        alarm.severity = alarm_update.severity
    
    if alarm_update.message is not None:
        alarm.message = alarm_update.message
    
    if alarm_update.acknowledged_by is not None:
        alarm.acknowledged_by = alarm_update.acknowledged_by
        alarm.acknowledged_at = datetime.utcnow()
    
    if alarm_update.resolved_by is not None:
        alarm.resolved_by = alarm_update.resolved_by
        alarm.resolved_at = datetime.utcnow()
        alarm.status = AlarmStatus.RESOLVED
    
    if alarm_update.additional_data is not None:
        alarm.additional_data = alarm_update.additional_data
    
    alarm.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alarm)
    
    # Send notification for status changes
    if alarm_update.status or alarm_update.acknowledged_by or alarm_update.resolved_by:
        background_tasks.add_task(
            notification_service.send_alarm,
            {
                "alarm_id": alarm.id,
                "device_id": alarm.device_id,
                "device_type": alarm.device_type,
                "severity": alarm.severity.value,
                "status": alarm.status.value,
                "message": alarm.message,
                "timestamp": alarm.timestamp.isoformat(),
                "action": "updated"
            }
        )
    
    return alarm


@router.get("/alarms/stats", response_model=AlarmStatsResponse)
async def get_alarm_stats(
    time_range: int = Query(86400, description="Time range in seconds (default: 24 hours)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get alarm statistics."""
    
    start_time = datetime.utcnow() - timedelta(seconds=time_range)
    
    # Get alarm counts by severity
    severity_stats = db.query(
        Alarm.severity,
        func.count(Alarm.id).label('count')
    ).filter(
        and_(
            Alarm.timestamp >= start_time,
            Alarm.status == AlarmStatus.ACTIVE
        )
    ).group_by(Alarm.severity).all()
    
    # Get alarm counts by device type
    device_type_stats = db.query(
        Alarm.device_type,
        func.count(Alarm.id).label('count')
    ).filter(
        and_(
            Alarm.timestamp >= start_time,
            Alarm.status == AlarmStatus.ACTIVE
        )
    ).group_by(Alarm.device_type).all()
    
    # Get total counts
    total_active = db.query(Alarm).filter(Alarm.status == AlarmStatus.ACTIVE).count()
    total_in_period = db.query(Alarm).filter(Alarm.timestamp >= start_time).count()
    
    return AlarmStatsResponse(
        total_active=total_active,
        total_in_period=total_in_period,
        by_severity={str(stat.severity.value): stat.count for stat in severity_stats},
        by_device_type={stat.device_type: stat.count for stat in device_type_stats}
    )


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get overall system health status."""
    
    # Get device counts
    total_olts = db.query(OLT).count()
    active_olts = db.query(OLT).filter(OLT.status == "active").count()
    total_onts = db.query(ONT).count()
    online_onts = db.query(ONT).filter(ONT.status == "online").count()
    
    # Get recent alarm counts
    recent_time = datetime.utcnow() - timedelta(hours=24)
    critical_alarms = db.query(Alarm).filter(
        and_(
            Alarm.severity == AlarmSeverity.CRITICAL,
            Alarm.status == AlarmStatus.ACTIVE,
            Alarm.timestamp >= recent_time
        )
    ).count()
    
    warning_alarms = db.query(Alarm).filter(
        and_(
            Alarm.severity == AlarmSeverity.WARNING,
            Alarm.status == AlarmStatus.ACTIVE,
            Alarm.timestamp >= recent_time
        )
    ).count()
    
    # Calculate overall health score
    health_score = 100.0
    
    # Reduce score based on offline devices
    if total_olts > 0:
        olt_availability = active_olts / total_olts
        health_score *= olt_availability
    
    if total_onts > 0:
        ont_availability = online_onts / total_onts
        health_score *= (0.7 + 0.3 * ont_availability)  # ONTs have less impact
    
    # Reduce score based on alarms
    health_score -= (critical_alarms * 10) + (warning_alarms * 2)
    health_score = max(0.0, health_score)
    
    # Determine status
    if health_score >= 90:
        status = "healthy"
    elif health_score >= 70:
        status = "warning"
    else:
        status = "critical"
    
    # Get monitoring service stats
    monitoring_stats = monitoring_service.get_service_stats()
    
    return SystemHealthResponse(
        status=status,
        health_score=health_score,
        total_olts=total_olts,
        active_olts=active_olts,
        total_onts=total_onts,
        online_onts=online_onts,
        critical_alarms=critical_alarms,
        warning_alarms=warning_alarms,
        monitoring_service_running=monitoring_stats["running"],
        last_update=datetime.utcnow()
    )


@router.get("/topology", response_model=Dict[str, Any])
async def get_network_topology(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get network topology data."""
    
    nodes = []
    edges = []
    
    # Get OLTs as nodes
    olts = db.query(OLT).all()
    for olt in olts:
        nodes.append(NetworkTopologyNode(
            id=olt.id,
            type="olt",
            name=olt.name,
            status=olt.status,
            ip_address=olt.ip_address,
            location=olt.location,
            metadata={
                "model": olt.model,
                "firmware_version": olt.firmware_version,
                "serial_number": olt.serial_number
            }
        ))
        
        # Get ONTs connected to this OLT
        onts = db.query(ONT).join(ONT.olt_port).filter(ONT.olt_port.has(olt_id=olt.id)).all()
        for ont in onts:
            nodes.append(NetworkTopologyNode(
                id=ont.id,
                type="ont",
                name=ont.serial_number,
                status=ont.status,
                metadata={
                    "ont_id": ont.ont_id,
                    "distance": ont.distance,
                    "rx_power": ont.rx_power,
                    "tx_power": ont.tx_power
                }
            ))
            
            # Create edge between OLT and ONT
            edges.append(NetworkTopologyEdge(
                source=olt.id,
                target=ont.id,
                type="fiber",
                status="active" if ont.status == "online" else "inactive",
                metadata={
                    "port": f"{ont.olt_port.slot_number}/{ont.olt_port.port_number}",
                    "distance": ont.distance
                }
            ))
    
    return {
        "nodes": [node.dict() for node in nodes],
        "edges": [edge.dict() for edge in edges],
        "last_update": datetime.utcnow().isoformat()
    }


@router.post("/monitoring/start")
async def start_monitoring_service(
    current_user: User = Depends(require_permissions(["admin"]))
):
    """Start the monitoring service."""
    
    if monitoring_service.running:
        raise HTTPException(status_code=400, detail="Monitoring service is already running")
    
    await monitoring_service.start()
    
    return {"message": "Monitoring service started successfully"}


@router.post("/monitoring/stop")
async def stop_monitoring_service(
    current_user: User = Depends(require_permissions(["admin"]))
):
    """Stop the monitoring service."""
    
    if not monitoring_service.running:
        raise HTTPException(status_code=400, detail="Monitoring service is not running")
    
    await monitoring_service.stop()
    
    return {"message": "Monitoring service stopped successfully"}


@router.get("/monitoring/status")
async def get_monitoring_service_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get monitoring service status and statistics."""
    
    stats = monitoring_service.get_service_stats()
    
    return {
        "service_status": "running" if stats["running"] else "stopped",
        "statistics": stats
    }