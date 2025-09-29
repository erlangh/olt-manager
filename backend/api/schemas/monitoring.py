"""
Monitoring and performance data API schemas.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ...models.alarm import AlarmSeverity, AlarmType, AlarmStatus, AlarmCategory
from ...models.performance_data import MetricType, DataSource, AggregationType


class AlarmBase(BaseModel):
    """Base alarm schema."""
    title: str = Field(..., min_length=1, max_length=200, description="Alarm title")
    description: Optional[str] = Field(None, max_length=1000, description="Alarm description")
    severity: AlarmSeverity = Field(..., description="Alarm severity")
    alarm_type: AlarmType = Field(..., description="Alarm type")
    category: AlarmCategory = Field(..., description="Alarm category")
    olt_id: Optional[int] = Field(None, description="Source OLT ID")
    ont_id: Optional[int] = Field(None, description="Source ONT ID")
    olt_port_id: Optional[int] = Field(None, description="Source OLT port ID")


class AlarmCreate(AlarmBase):
    """Schema for creating alarm."""
    pass


class AlarmUpdate(BaseModel):
    """Schema for updating alarm."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    severity: Optional[AlarmSeverity] = Field(None)
    status: Optional[AlarmStatus] = Field(None)
    acknowledged_by: Optional[str] = Field(None, max_length=50)
    resolution_notes: Optional[str] = Field(None, max_length=1000)


class AlarmResponse(AlarmBase):
    """Schema for alarm response."""
    id: int
    alarm_id: str
    status: AlarmStatus
    source_component: Optional[str]
    source_ip: Optional[str]
    event_time: datetime
    clear_time: Optional[datetime]
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    escalated: bool
    escalated_at: Optional[datetime]
    escalated_to: Optional[str]
    resolution_notes: Optional[str]
    additional_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlarmListResponse(BaseModel):
    """Schema for alarm list response."""
    alarms: List[AlarmResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AlarmStatsResponse(BaseModel):
    """Schema for alarm statistics response."""
    total_alarms: int
    active_alarms: int
    acknowledged_alarms: int
    critical_alarms: int
    major_alarms: int
    minor_alarms: int
    warning_alarms: int
    info_alarms: int
    alarms_by_category: Dict[str, int]
    alarms_by_source: Dict[str, int]


class PerformanceDataBase(BaseModel):
    """Base performance data schema."""
    metric_name: str = Field(..., min_length=1, max_length=100, description="Metric name")
    metric_type: MetricType = Field(..., description="Metric type")
    data_source: DataSource = Field(..., description="Data source")
    olt_id: Optional[int] = Field(None, description="Source OLT ID")
    ont_id: Optional[int] = Field(None, description="Source ONT ID")
    olt_port_id: Optional[int] = Field(None, description="Source OLT port ID")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, max_length=20, description="Value unit")


class PerformanceDataCreate(PerformanceDataBase):
    """Schema for creating performance data."""
    pass


class PerformanceDataResponse(PerformanceDataBase):
    """Schema for performance data response."""
    id: int
    timestamp: datetime
    aggregation_type: Optional[AggregationType]
    aggregation_period: Optional[int]
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    sample_count: Optional[int]
    quality_score: Optional[float]
    tags: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PerformanceDataListResponse(BaseModel):
    """Schema for performance data list response."""
    data: List[PerformanceDataResponse]
    total: int
    page: int
    per_page: int
    pages: int


class MetricSummaryResponse(BaseModel):
    """Schema for metric summary response."""
    metric_name: str
    metric_type: MetricType
    unit: Optional[str]
    current_value: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    sample_count: int
    last_update: Optional[datetime]
    trend: Optional[str]  # "up", "down", "stable"


class DeviceMetricsResponse(BaseModel):
    """Schema for device metrics response."""
    device_id: int
    device_type: str  # "olt", "ont", "port"
    device_name: Optional[str]
    metrics: List[MetricSummaryResponse]
    health_score: Optional[float]
    last_update: datetime


class SystemHealthResponse(BaseModel):
    """Schema for system health response."""
    overall_health: str  # "excellent", "good", "fair", "poor", "critical"
    health_score: float  # 0-100
    total_devices: int
    online_devices: int
    offline_devices: int
    devices_with_alarms: int
    critical_alarms: int
    major_alarms: int
    system_uptime: int  # seconds
    last_update: datetime


class NetworkTopologyNode(BaseModel):
    """Schema for network topology node."""
    id: str
    type: str  # "olt", "ont", "port"
    name: str
    status: str
    properties: Dict[str, Any]
    position: Optional[Dict[str, float]]  # x, y coordinates


class NetworkTopologyEdge(BaseModel):
    """Schema for network topology edge."""
    source: str
    target: str
    type: str  # "fiber", "ethernet"
    properties: Dict[str, Any]


class NetworkTopologyResponse(BaseModel):
    """Schema for network topology response."""
    nodes: List[NetworkTopologyNode]
    edges: List[NetworkTopologyEdge]
    last_update: datetime