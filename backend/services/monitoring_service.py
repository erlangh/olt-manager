"""
Monitoring service for background data collection and performance monitoring.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..database.connection import get_db_session
from ..models.olt import OLT, OLTPort
from ..models.ont import ONT
from ..models.performance_data import PerformanceData, MetricType, DataSource, AggregationType
from ..models.alarm import Alarm, AlarmSeverity, AlarmStatus
from .snmp_service import ZTEOLTService, SNMPConfig
from .websocket_service import notification_service

logger = logging.getLogger(__name__)


class MonitoringTaskType(str, Enum):
    """Types of monitoring tasks."""
    DEVICE_DISCOVERY = "device_discovery"
    PERFORMANCE_COLLECTION = "performance_collection"
    HEALTH_CHECK = "health_check"
    ALARM_MONITORING = "alarm_monitoring"
    THRESHOLD_CHECK = "threshold_check"


@dataclass
class MonitoringTask:
    """Monitoring task definition."""
    task_id: str
    task_type: MonitoringTaskType
    target_device_id: Optional[str] = None
    target_device_type: Optional[str] = None
    interval_seconds: int = 300  # 5 minutes default
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 5
    callback: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.next_run is None:
            self.next_run = datetime.utcnow()
    
    @property
    def is_due(self) -> bool:
        """Check if task is due to run."""
        return self.enabled and self.next_run <= datetime.utcnow()
    
    @property
    def is_healthy(self) -> bool:
        """Check if task is healthy (not too many errors)."""
        return self.error_count < self.max_errors
    
    def schedule_next_run(self):
        """Schedule next run based on interval."""
        self.next_run = datetime.utcnow() + timedelta(seconds=self.interval_seconds)
    
    def mark_success(self):
        """Mark task as successfully completed."""
        self.last_run = datetime.utcnow()
        self.error_count = 0
        self.schedule_next_run()
    
    def mark_error(self):
        """Mark task as failed."""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self.enabled = False
            logger.error(f"Task {self.task_id} disabled due to too many errors")
        else:
            self.schedule_next_run()


class MonitoringService:
    """Background monitoring service."""
    
    def __init__(self):
        self.tasks: Dict[str, MonitoringTask] = {}
        self.running = False
        self.main_task = None
        self.snmp_services: Dict[str, ZTEOLTService] = {}
        
        # Performance thresholds
        self.thresholds = {
            "cpu_usage": {"warning": 80.0, "critical": 95.0},
            "memory_usage": {"warning": 85.0, "critical": 95.0},
            "temperature": {"warning": 70.0, "critical": 85.0},
            "optical_power_rx": {"warning": -25.0, "critical": -30.0},
            "optical_power_tx": {"warning": -3.0, "critical": -5.0},
            "ont_offline_ratio": {"warning": 0.1, "critical": 0.2}
        }
    
    async def start(self):
        """Start monitoring service."""
        if self.running:
            return
        
        self.running = True
        self.main_task = asyncio.create_task(self._monitoring_loop())
        
        # Initialize default monitoring tasks
        await self._initialize_default_tasks()
        
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service."""
        self.running = False
        
        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Process due tasks
                due_tasks = [task for task in self.tasks.values() if task.is_due and task.is_healthy]
                
                if due_tasks:
                    # Run tasks concurrently
                    await asyncio.gather(
                        *[self._execute_task(task) for task in due_tasks],
                        return_exceptions=True
                    )
                
                # Sleep for a short interval
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _execute_task(self, task: MonitoringTask):
        """Execute a monitoring task."""
        try:
            logger.debug(f"Executing task: {task.task_id}")
            
            if task.task_type == MonitoringTaskType.DEVICE_DISCOVERY:
                await self._discover_devices(task)
            elif task.task_type == MonitoringTaskType.PERFORMANCE_COLLECTION:
                await self._collect_performance_data(task)
            elif task.task_type == MonitoringTaskType.HEALTH_CHECK:
                await self._perform_health_check(task)
            elif task.task_type == MonitoringTaskType.ALARM_MONITORING:
                await self._monitor_alarms(task)
            elif task.task_type == MonitoringTaskType.THRESHOLD_CHECK:
                await self._check_thresholds(task)
            
            task.mark_success()
            
            # Execute callback if provided
            if task.callback:
                await task.callback(task, success=True)
            
        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {e}")
            task.mark_error()
            
            # Execute callback if provided
            if task.callback:
                await task.callback(task, success=False, error=str(e))
    
    async def _initialize_default_tasks(self):
        """Initialize default monitoring tasks."""
        # Device discovery task
        self.add_task(MonitoringTask(
            task_id="global_device_discovery",
            task_type=MonitoringTaskType.DEVICE_DISCOVERY,
            interval_seconds=600,  # 10 minutes
            parameters={"discover_all": True}
        ))
        
        # Global health check task
        self.add_task(MonitoringTask(
            task_id="global_health_check",
            task_type=MonitoringTaskType.HEALTH_CHECK,
            interval_seconds=300,  # 5 minutes
            parameters={"check_all": True}
        ))
        
        # Threshold monitoring task
        self.add_task(MonitoringTask(
            task_id="global_threshold_check",
            task_type=MonitoringTaskType.THRESHOLD_CHECK,
            interval_seconds=120,  # 2 minutes
            parameters={"check_all": True}
        ))
        
        # Alarm monitoring task
        self.add_task(MonitoringTask(
            task_id="global_alarm_monitoring",
            task_type=MonitoringTaskType.ALARM_MONITORING,
            interval_seconds=60,  # 1 minute
            parameters={"monitor_all": True}
        ))
    
    def add_task(self, task: MonitoringTask):
        """Add monitoring task."""
        self.tasks[task.task_id] = task
        logger.info(f"Added monitoring task: {task.task_id}")
    
    def remove_task(self, task_id: str):
        """Remove monitoring task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed monitoring task: {task_id}")
    
    def get_task(self, task_id: str) -> Optional[MonitoringTask]:
        """Get monitoring task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[MonitoringTask]:
        """List all monitoring tasks."""
        return list(self.tasks.values())
    
    async def _get_snmp_service(self, olt_id: str) -> Optional[ZTEOLTService]:
        """Get or create SNMP service for OLT."""
        if olt_id in self.snmp_services:
            return self.snmp_services[olt_id]
        
        # Get OLT from database
        async with get_db_session() as db:
            olt = db.query(OLT).filter(OLT.id == olt_id).first()
            if not olt:
                return None
            
            # Create SNMP service
            config = SNMPConfig(
                host=olt.ip_address,
                community=olt.snmp_community or "public",
                timeout=olt.snmp_timeout or 5,
                retries=3
            )
            
            service = ZTEOLTService(config)
            
            # Test connection
            if await service.test_connection():
                self.snmp_services[olt_id] = service
                return service
            else:
                logger.error(f"Failed to connect to OLT {olt_id} at {olt.ip_address}")
                return None
    
    async def _discover_devices(self, task: MonitoringTask):
        """Discover devices on the network."""
        async with get_db_session() as db:
            if task.parameters.get("discover_all"):
                # Discover all configured OLTs
                olts = db.query(OLT).filter(OLT.status == "active").all()
            else:
                # Discover specific OLT
                olts = db.query(OLT).filter(
                    and_(OLT.id == task.target_device_id, OLT.status == "active")
                ).all()
            
            for olt in olts:
                try:
                    snmp_service = await self._get_snmp_service(olt.id)
                    if not snmp_service:
                        continue
                    
                    # Discover OLT info
                    olt_info = await snmp_service.discover_olt()
                    if olt_info:
                        # Update OLT information
                        olt.system_name = olt_info.system_name
                        olt.firmware_version = olt_info.firmware_version
                        olt.hardware_version = olt_info.hardware_version
                        olt.serial_number = olt_info.serial_number
                        olt.mac_address = olt_info.mac_address
                        olt.last_seen = datetime.utcnow()
                        
                        # Send discovery notification
                        await notification_service.send_device_discovery({
                            "device_id": olt.id,
                            "device_type": "olt",
                            "device_name": olt.name,
                            "status": "discovered",
                            "info": {
                                "system_name": olt_info.system_name,
                                "firmware_version": olt_info.firmware_version,
                                "serial_number": olt_info.serial_number
                            }
                        })
                    
                    # Discover ports
                    ports = await snmp_service.discover_all_ports()
                    for port_info in ports:
                        # Update or create port
                        port = db.query(OLTPort).filter(
                            and_(
                                OLTPort.olt_id == olt.id,
                                OLTPort.slot_number == port_info.slot,
                                OLTPort.port_number == port_info.port
                            )
                        ).first()
                        
                        if not port:
                            port = OLTPort(
                                olt_id=olt.id,
                                slot_number=port_info.slot,
                                port_number=port_info.port,
                                name=f"Slot{port_info.slot}/Port{port_info.port}"
                            )
                            db.add(port)
                        
                        port.admin_status = "enabled" if port_info.admin_status else "disabled"
                        port.oper_status = port_info.oper_status
                        port.ont_count = port_info.ont_count
                        port.max_ont_count = port_info.max_ont_count
                        port.last_seen = datetime.utcnow()
                        
                        # Discover ONTs on this port
                        onts = await snmp_service.discover_all_onts(port_info.slot, port_info.port)
                        for ont_info in onts:
                            # Update or create ONT
                            ont = db.query(ONT).filter(
                                and_(
                                    ONT.olt_port_id == port.id,
                                    ONT.ont_id == ont_info.ont_id
                                )
                            ).first()
                            
                            if not ont:
                                ont = ONT(
                                    olt_port_id=port.id,
                                    ont_id=ont_info.ont_id,
                                    serial_number=ont_info.serial_number
                                )
                                db.add(ont)
                            
                            ont.status = ont_info.status
                            ont.distance = ont_info.distance
                            ont.rx_power = ont_info.rx_power
                            ont.tx_power = ont_info.tx_power
                            ont.firmware_version = ont_info.firmware_version
                            ont.hardware_version = ont_info.hardware_version
                            ont.mac_address = ont_info.mac_address
                            ont.last_seen = datetime.utcnow()
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Error discovering OLT {olt.id}: {e}")
                    db.rollback()
    
    async def _collect_performance_data(self, task: MonitoringTask):
        """Collect performance data from devices."""
        async with get_db_session() as db:
            if task.parameters.get("collect_all"):
                # Collect from all active OLTs
                olts = db.query(OLT).filter(OLT.status == "active").all()
            else:
                # Collect from specific OLT
                olts = db.query(OLT).filter(
                    and_(OLT.id == task.target_device_id, OLT.status == "active")
                ).all()
            
            for olt in olts:
                try:
                    snmp_service = await self._get_snmp_service(olt.id)
                    if not snmp_service:
                        continue
                    
                    # Collect OLT performance data
                    olt_info = await snmp_service.discover_olt()
                    if olt_info:
                        # Store CPU usage
                        cpu_data = PerformanceData(
                            device_id=olt.id,
                            device_type="olt",
                            metric_type=MetricType.CPU_USAGE,
                            data_source=DataSource.SNMP,
                            value=olt_info.cpu_usage,
                            unit="percent",
                            timestamp=datetime.utcnow()
                        )
                        db.add(cpu_data)
                        
                        # Store memory usage
                        memory_data = PerformanceData(
                            device_id=olt.id,
                            device_type="olt",
                            metric_type=MetricType.MEMORY_USAGE,
                            data_source=DataSource.SNMP,
                            value=olt_info.memory_usage,
                            unit="percent",
                            timestamp=datetime.utcnow()
                        )
                        db.add(memory_data)
                        
                        # Store temperature
                        temp_data = PerformanceData(
                            device_id=olt.id,
                            device_type="olt",
                            metric_type=MetricType.TEMPERATURE,
                            data_source=DataSource.SNMP,
                            value=olt_info.temperature,
                            unit="celsius",
                            timestamp=datetime.utcnow()
                        )
                        db.add(temp_data)
                        
                        # Send performance data notification
                        await notification_service.send_performance_data(
                            olt.id, "olt", {
                                "cpu_usage": olt_info.cpu_usage,
                                "memory_usage": olt_info.memory_usage,
                                "temperature": olt_info.temperature,
                                "power_consumption": olt_info.power_consumption
                            }
                        )
                    
                    # Collect port performance data
                    ports = db.query(OLTPort).filter(OLTPort.olt_id == olt.id).all()
                    for port in ports:
                        port_info = await snmp_service.get_port_info(port.slot_number, port.port_number)
                        if port_info:
                            # Store optical power data
                            rx_power_data = PerformanceData(
                                device_id=port.id,
                                device_type="olt_port",
                                metric_type=MetricType.OPTICAL_POWER_RX,
                                data_source=DataSource.SNMP,
                                value=port_info.optical_power_rx,
                                unit="dbm",
                                timestamp=datetime.utcnow()
                            )
                            db.add(rx_power_data)
                            
                            tx_power_data = PerformanceData(
                                device_id=port.id,
                                device_type="olt_port",
                                metric_type=MetricType.OPTICAL_POWER_TX,
                                data_source=DataSource.SNMP,
                                value=port_info.optical_power_tx,
                                unit="dbm",
                                timestamp=datetime.utcnow()
                            )
                            db.add(tx_power_data)
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Error collecting performance data from OLT {olt.id}: {e}")
                    db.rollback()
    
    async def _perform_health_check(self, task: MonitoringTask):
        """Perform health checks on devices."""
        async with get_db_session() as db:
            if task.parameters.get("check_all"):
                # Check all active OLTs
                olts = db.query(OLT).filter(OLT.status == "active").all()
            else:
                # Check specific OLT
                olts = db.query(OLT).filter(
                    and_(OLT.id == task.target_device_id, OLT.status == "active")
                ).all()
            
            for olt in olts:
                try:
                    snmp_service = await self._get_snmp_service(olt.id)
                    if not snmp_service:
                        # Mark OLT as unreachable
                        olt.status = "unreachable"
                        continue
                    
                    # Test SNMP connection
                    if await snmp_service.test_connection():
                        olt.status = "active"
                        olt.last_seen = datetime.utcnow()
                        
                        # Send status update
                        await notification_service.send_olt_status_update(olt.id, {
                            "status": "active",
                            "last_seen": olt.last_seen.isoformat()
                        })
                    else:
                        olt.status = "unreachable"
                        
                        # Send status update
                        await notification_service.send_olt_status_update(olt.id, {
                            "status": "unreachable",
                            "last_seen": olt.last_seen.isoformat() if olt.last_seen else None
                        })
                    
                except Exception as e:
                    logger.error(f"Error performing health check on OLT {olt.id}: {e}")
                    olt.status = "error"
            
            db.commit()
    
    async def _monitor_alarms(self, task: MonitoringTask):
        """Monitor and process alarms."""
        async with get_db_session() as db:
            # Get active alarms that need attention
            active_alarms = db.query(Alarm).filter(
                Alarm.status == AlarmStatus.ACTIVE
            ).all()
            
            for alarm in active_alarms:
                # Send alarm notification if not already sent recently
                if not alarm.last_notification or \
                   (datetime.utcnow() - alarm.last_notification).total_seconds() > 3600:  # 1 hour
                    
                    await notification_service.send_alarm({
                        "alarm_id": alarm.id,
                        "device_id": alarm.device_id,
                        "device_type": alarm.device_type,
                        "severity": alarm.severity.value,
                        "message": alarm.message,
                        "timestamp": alarm.timestamp.isoformat()
                    })
                    
                    alarm.last_notification = datetime.utcnow()
            
            db.commit()
    
    async def _check_thresholds(self, task: MonitoringTask):
        """Check performance thresholds and generate alarms."""
        async with get_db_session() as db:
            # Get recent performance data
            recent_data = db.query(PerformanceData).filter(
                PerformanceData.timestamp >= datetime.utcnow() - timedelta(minutes=10)
            ).all()
            
            for data in recent_data:
                metric_name = data.metric_type.value
                if metric_name not in self.thresholds:
                    continue
                
                thresholds = self.thresholds[metric_name]
                value = data.value
                
                # Check critical threshold
                if value >= thresholds.get("critical", float('inf')) or \
                   value <= thresholds.get("critical_low", float('-inf')):
                    
                    await self._create_threshold_alarm(
                        db, data, AlarmSeverity.CRITICAL, "critical", value, thresholds["critical"]
                    )
                
                # Check warning threshold
                elif value >= thresholds.get("warning", float('inf')) or \
                     value <= thresholds.get("warning_low", float('-inf')):
                    
                    await self._create_threshold_alarm(
                        db, data, AlarmSeverity.WARNING, "warning", value, thresholds["warning"]
                    )
            
            db.commit()
    
    async def _create_threshold_alarm(self, db: Session, data: PerformanceData, 
                                    severity: AlarmSeverity, threshold_type: str, 
                                    value: float, threshold: float):
        """Create threshold-based alarm."""
        # Check if similar alarm already exists
        existing_alarm = db.query(Alarm).filter(
            and_(
                Alarm.device_id == data.device_id,
                Alarm.device_type == data.device_type,
                Alarm.alarm_type == f"threshold_{data.metric_type.value}",
                Alarm.status == AlarmStatus.ACTIVE
            )
        ).first()
        
        if existing_alarm:
            # Update existing alarm
            existing_alarm.severity = severity
            existing_alarm.message = f"{data.metric_type.value} {threshold_type} threshold exceeded: {value} {data.unit}"
            existing_alarm.timestamp = datetime.utcnow()
        else:
            # Create new alarm
            alarm = Alarm(
                device_id=data.device_id,
                device_type=data.device_type,
                alarm_type=f"threshold_{data.metric_type.value}",
                severity=severity,
                status=AlarmStatus.ACTIVE,
                message=f"{data.metric_type.value} {threshold_type} threshold exceeded: {value} {data.unit}",
                timestamp=datetime.utcnow(),
                additional_data={
                    "metric_type": data.metric_type.value,
                    "value": value,
                    "threshold": threshold,
                    "threshold_type": threshold_type,
                    "unit": data.unit
                }
            )
            db.add(alarm)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get monitoring service statistics."""
        total_tasks = len(self.tasks)
        enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
        healthy_tasks = sum(1 for task in self.tasks.values() if task.is_healthy)
        due_tasks = sum(1 for task in self.tasks.values() if task.is_due)
        
        return {
            "running": self.running,
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "healthy_tasks": healthy_tasks,
            "due_tasks": due_tasks,
            "snmp_connections": len(self.snmp_services),
            "task_types": list(set(task.task_type.value for task in self.tasks.values()))
        }


# Global monitoring service instance
monitoring_service = MonitoringService()