from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json

from database import get_db
from models import Alarm, PerformanceData, OLT, ONT
from core.snmp_client import ZTE_C320_SNMP

router = APIRouter()

# Pydantic models
class AlarmResponse(BaseModel):
    id: int
    olt_id: Optional[int]
    ont_id: Optional[int]
    alarm_type: str
    severity: str
    status: str
    message: str
    additional_info: Optional[dict]
    raised_at: datetime
    cleared_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    
    class Config:
        from_attributes = True

class PerformanceDataResponse(BaseModel):
    id: int
    olt_id: Optional[int]
    ont_id: Optional[int]
    port_id: Optional[int]
    metric_type: str
    metric_name: str
    value: float
    unit: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class AlarmAcknowledge(BaseModel):
    alarm_ids: List[int]
    acknowledged_by: str

class DashboardStats(BaseModel):
    total_olts: int
    active_olts: int
    total_onts: int
    online_onts: int
    active_alarms: int
    critical_alarms: int

class PerformanceMetrics(BaseModel):
    cpu_utilization: Optional[float]
    memory_utilization: Optional[float]
    temperature: Optional[float]
    total_traffic_in: Optional[float]
    total_traffic_out: Optional[float]
    timestamp: datetime

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get dashboard statistics."""
    
    # Count OLTs
    total_olts = db.query(OLT).count()
    active_olts = db.query(OLT).filter(OLT.is_active == True).count()
    
    # Count ONTs
    total_onts = db.query(ONT).count()
    online_onts = db.query(ONT).filter(ONT.status == "online").count()
    
    # Count alarms
    active_alarms = db.query(Alarm).filter(Alarm.status == "active").count()
    critical_alarms = db.query(Alarm).filter(
        Alarm.status == "active",
        Alarm.severity == "critical"
    ).count()
    
    return DashboardStats(
        total_olts=total_olts,
        active_olts=active_olts,
        total_onts=total_onts,
        online_onts=online_onts,
        active_alarms=active_alarms,
        critical_alarms=critical_alarms
    )

@router.get("/alarms", response_model=List[AlarmResponse])
async def get_alarms(
    olt_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get alarms with optional filtering."""
    query = db.query(Alarm)
    
    if olt_id:
        query = query.filter(Alarm.olt_id == olt_id)
    if severity:
        query = query.filter(Alarm.severity == severity)
    if status:
        query = query.filter(Alarm.status == status)
    
    alarms = query.order_by(Alarm.raised_at.desc()).offset(skip).limit(limit).all()
    return alarms

@router.post("/alarms/acknowledge")
async def acknowledge_alarms(
    acknowledge_data: AlarmAcknowledge,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Acknowledge multiple alarms."""
    
    updated_count = 0
    for alarm_id in acknowledge_data.alarm_ids:
        alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
        if alarm and alarm.status == "active":
            alarm.status = "acknowledged"
            alarm.acknowledged_at = datetime.utcnow()
            alarm.acknowledged_by = acknowledge_data.acknowledged_by
            updated_count += 1
    
    db.commit()
    return {"message": f"Acknowledged {updated_count} alarms"}

@router.get("/performance", response_model=List[PerformanceDataResponse])
async def get_performance_data(
    olt_id: Optional[int] = None,
    ont_id: Optional[int] = None,
    metric_type: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get performance data for specified time period."""
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    query = db.query(PerformanceData).filter(
        PerformanceData.timestamp >= start_time,
        PerformanceData.timestamp <= end_time
    )
    
    if olt_id:
        query = query.filter(PerformanceData.olt_id == olt_id)
    if ont_id:
        query = query.filter(PerformanceData.ont_id == ont_id)
    if metric_type:
        query = query.filter(PerformanceData.metric_type == metric_type)
    
    performance_data = query.order_by(PerformanceData.timestamp.desc()).all()
    return performance_data

@router.get("/performance/realtime/{olt_id}", response_model=PerformanceMetrics)
async def get_realtime_performance(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get real-time performance metrics for OLT."""
    
    olt = db.query(OLT).filter(OLT.id == olt_id).first()
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
        # Get performance data via SNMP
        performance_data = await snmp_client.get_performance_data()
        
        # Parse and convert data
        cpu_util = None
        memory_util = None
        temperature = None
        
        if 'cpuUtilization' in performance_data:
            try:
                cpu_util = float(performance_data['cpuUtilization'])
            except (ValueError, TypeError):
                pass
        
        if 'memoryUtilization' in performance_data:
            try:
                memory_util = float(performance_data['memoryUtilization'])
            except (ValueError, TypeError):
                pass
        
        if 'temperature' in performance_data:
            try:
                temperature = float(performance_data['temperature'])
            except (ValueError, TypeError):
                pass
        
        # Store performance data in database
        metrics_to_store = [
            ("cpu", "cpu_utilization", cpu_util, "%"),
            ("memory", "memory_utilization", memory_util, "%"),
            ("temperature", "temperature", temperature, "°C")
        ]
        
        for metric_type, metric_name, value, unit in metrics_to_store:
            if value is not None:
                perf_data = PerformanceData(
                    olt_id=olt_id,
                    metric_type=metric_type,
                    metric_name=metric_name,
                    value=value,
                    unit=unit,
                    timestamp=datetime.utcnow()
                )
                db.add(perf_data)
        
        db.commit()
        
        return PerformanceMetrics(
            cpu_utilization=cpu_util,
            memory_utilization=memory_util,
            temperature=temperature,
            total_traffic_in=0.0,  # Would need additional SNMP queries
            total_traffic_out=0.0,  # Would need additional SNMP queries
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance data: {str(e)}"
        )

@router.get("/performance/chart/{olt_id}")
async def get_performance_chart_data(
    olt_id: int,
    metric_type: str = "cpu",
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get performance data formatted for charts."""
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Query performance data
    performance_data = db.query(PerformanceData).filter(
        PerformanceData.olt_id == olt_id,
        PerformanceData.metric_type == metric_type,
        PerformanceData.timestamp >= start_time,
        PerformanceData.timestamp <= end_time
    ).order_by(PerformanceData.timestamp).all()
    
    # Format data for charts
    chart_data = {
        "labels": [],
        "datasets": {}
    }
    
    for data_point in performance_data:
        timestamp_str = data_point.timestamp.strftime("%H:%M")
        if timestamp_str not in chart_data["labels"]:
            chart_data["labels"].append(timestamp_str)
        
        metric_name = data_point.metric_name
        if metric_name not in chart_data["datasets"]:
            chart_data["datasets"][metric_name] = {
                "label": metric_name.replace("_", " ").title(),
                "data": [],
                "unit": data_point.unit or ""
            }
        
        chart_data["datasets"][metric_name]["data"].append({
            "x": timestamp_str,
            "y": data_point.value
        })
    
    return chart_data

@router.post("/alarms/test/{olt_id}")
async def create_test_alarm(
    olt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Create a test alarm for testing purposes."""
    
    olt = db.query(OLT).filter(OLT.id == olt_id).first()
    if not olt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OLT not found"
        )
    
    test_alarm = Alarm(
        olt_id=olt_id,
        alarm_type="test_alarm",
        severity="warning",
        status="active",
        message=f"Test alarm for OLT {olt.name}",
        additional_info={"test": True, "created_by": current_user["username"]},
        raised_at=datetime.utcnow()
    )
    
    db.add(test_alarm)
    db.commit()
    db.refresh(test_alarm)
    
    return {"message": "Test alarm created", "alarm_id": test_alarm.id}

@router.get("/health-check")
async def monitoring_health_check(
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Check monitoring system health."""
    
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        
        # Get recent performance data count
        recent_data_count = db.query(PerformanceData).filter(
            PerformanceData.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        # Get active alarms count
        active_alarms_count = db.query(Alarm).filter(Alarm.status == "active").count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "recent_performance_data": recent_data_count,
            "active_alarms": active_alarms_count,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

@router.delete("/performance/cleanup")
async def cleanup_old_performance_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Clean up old performance data."""
    
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete old performance data
    deleted_count = db.query(PerformanceData).filter(
        PerformanceData.timestamp < cutoff_date
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Cleaned up {deleted_count} old performance records",
        "cutoff_date": cutoff_date
    }