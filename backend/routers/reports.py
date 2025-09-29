from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import seaborn as sns
import base64

from database import get_db
from models import OLT, ONT, Alarm, PerformanceData, User, AuditLog

router = APIRouter()

# Pydantic models
class ReportRequest(BaseModel):
    report_type: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    olt_ids: Optional[List[int]] = None
    format: str = "json"  # json, csv, pdf, excel

class OLTSummaryReport(BaseModel):
    olt_id: int
    olt_name: str
    ip_address: str
    total_ports: int
    active_ports: int
    total_onts: int
    online_onts: int
    offline_onts: int
    active_alarms: int

class ONTStatusReport(BaseModel):
    ont_id: int
    ont_serial: str
    olt_name: str
    port_id: int
    status: str
    signal_level: Optional[float]
    last_seen: Optional[datetime]

class AlarmReport(BaseModel):
    alarm_id: int
    olt_name: str
    ont_serial: Optional[str]
    alarm_type: str
    severity: str
    status: str
    message: str
    raised_at: datetime
    cleared_at: Optional[datetime]

class PerformanceReport(BaseModel):
    timestamp: datetime
    olt_name: str
    metric_type: str
    metric_name: str
    value: float
    unit: Optional[str]

class UserActivityReport(BaseModel):
    user_id: int
    username: str
    action: str
    resource_type: str
    resource_id: Optional[int]
    timestamp: datetime
    ip_address: Optional[str]

@router.post("/reports/olt-summary")
async def generate_olt_summary_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Generate OLT summary report."""
    
    # Build query
    query = db.query(OLT)
    if request.olt_ids:
        query = query.filter(OLT.id.in_(request.olt_ids))
    
    olts = query.all()
    
    report_data = []
    for olt in olts:
        # Count ports
        total_ports = len(olt.ports) if olt.ports else 0
        active_ports = len([p for p in olt.ports if p.is_active]) if olt.ports else 0
        
        # Count ONTs
        total_onts = db.query(ONT).filter(ONT.olt_id == olt.id).count()
        online_onts = db.query(ONT).filter(
            ONT.olt_id == olt.id,
            ONT.status == "online"
        ).count()
        offline_onts = total_onts - online_onts
        
        # Count active alarms
        active_alarms = db.query(Alarm).filter(
            Alarm.olt_id == olt.id,
            Alarm.status == "active"
        ).count()
        
        report_data.append(OLTSummaryReport(
            olt_id=olt.id,
            olt_name=olt.name,
            ip_address=olt.ip_address,
            total_ports=total_ports,
            active_ports=active_ports,
            total_onts=total_onts,
            online_onts=online_onts,
            offline_onts=offline_onts,
            active_alarms=active_alarms
        ))
    
    return await format_report_output(report_data, request.format, "OLT Summary Report")

@router.post("/reports/ont-status")
async def generate_ont_status_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Generate ONT status report."""
    
    # Build query
    query = db.query(ONT).join(OLT)
    
    if request.olt_ids:
        query = query.filter(ONT.olt_id.in_(request.olt_ids))
    
    if request.start_date:
        query = query.filter(ONT.created_at >= request.start_date)
    if request.end_date:
        query = query.filter(ONT.created_at <= request.end_date)
    
    onts = query.all()
    
    report_data = []
    for ont in onts:
        report_data.append(ONTStatusReport(
            ont_id=ont.id,
            ont_serial=ont.serial_number,
            olt_name=ont.olt.name,
            port_id=ont.port_id,
            status=ont.status,
            signal_level=ont.signal_level,
            last_seen=ont.last_seen
        ))
    
    return await format_report_output(report_data, request.format, "ONT Status Report")

@router.post("/reports/alarms")
async def generate_alarm_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Generate alarm report."""
    
    # Build query
    query = db.query(Alarm).join(OLT, Alarm.olt_id == OLT.id, isouter=True)
    
    if request.olt_ids:
        query = query.filter(Alarm.olt_id.in_(request.olt_ids))
    
    if request.start_date:
        query = query.filter(Alarm.raised_at >= request.start_date)
    if request.end_date:
        query = query.filter(Alarm.raised_at <= request.end_date)
    
    alarms = query.order_by(Alarm.raised_at.desc()).all()
    
    report_data = []
    for alarm in alarms:
        ont_serial = None
        if alarm.ont_id:
            ont = db.query(ONT).filter(ONT.id == alarm.ont_id).first()
            if ont:
                ont_serial = ont.serial_number
        
        report_data.append(AlarmReport(
            alarm_id=alarm.id,
            olt_name=alarm.olt.name if alarm.olt else "Unknown",
            ont_serial=ont_serial,
            alarm_type=alarm.alarm_type,
            severity=alarm.severity,
            status=alarm.status,
            message=alarm.message,
            raised_at=alarm.raised_at,
            cleared_at=alarm.cleared_at
        ))
    
    return await format_report_output(report_data, request.format, "Alarm Report")

@router.post("/reports/performance")
async def generate_performance_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Generate performance report."""
    
    # Default to last 24 hours if no dates specified
    if not request.start_date:
        request.start_date = datetime.utcnow() - timedelta(hours=24)
    if not request.end_date:
        request.end_date = datetime.utcnow()
    
    # Build query
    query = db.query(PerformanceData).join(OLT, PerformanceData.olt_id == OLT.id, isouter=True)
    
    query = query.filter(
        PerformanceData.timestamp >= request.start_date,
        PerformanceData.timestamp <= request.end_date
    )
    
    if request.olt_ids:
        query = query.filter(PerformanceData.olt_id.in_(request.olt_ids))
    
    performance_data = query.order_by(PerformanceData.timestamp.desc()).all()
    
    report_data = []
    for data in performance_data:
        report_data.append(PerformanceReport(
            timestamp=data.timestamp,
            olt_name=data.olt.name if data.olt else "Unknown",
            metric_type=data.metric_type,
            metric_name=data.metric_name,
            value=data.value,
            unit=data.unit
        ))
    
    return await format_report_output(report_data, request.format, "Performance Report")

@router.post("/reports/user-activity")
async def generate_user_activity_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Generate user activity report (admin only)."""
    
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Default to last 7 days if no dates specified
    if not request.start_date:
        request.start_date = datetime.utcnow() - timedelta(days=7)
    if not request.end_date:
        request.end_date = datetime.utcnow()
    
    # Build query
    query = db.query(AuditLog).filter(
        AuditLog.timestamp >= request.start_date,
        AuditLog.timestamp <= request.end_date
    )
    
    audit_logs = query.order_by(AuditLog.timestamp.desc()).all()
    
    report_data = []
    for log in audit_logs:
        report_data.append(UserActivityReport(
            user_id=log.user_id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            timestamp=log.timestamp,
            ip_address=log.ip_address
        ))
    
    return await format_report_output(report_data, request.format, "User Activity Report")

@router.get("/reports/dashboard-analytics")
async def get_dashboard_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Get analytics data for dashboard charts."""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # ONT status distribution
    ont_status_data = db.query(
        ONT.status,
        func.count(ONT.id).label('count')
    ).group_by(ONT.status).all()
    
    # Alarm severity distribution
    alarm_severity_data = db.query(
        Alarm.severity,
        func.count(Alarm.id).label('count')
    ).filter(
        Alarm.status == 'active'
    ).group_by(Alarm.severity).all()
    
    # Daily alarm trends
    daily_alarms = db.query(
        func.date(Alarm.raised_at).label('date'),
        func.count(Alarm.id).label('count')
    ).filter(
        Alarm.raised_at >= start_date
    ).group_by(func.date(Alarm.raised_at)).all()
    
    # OLT performance trends (CPU utilization)
    cpu_performance = db.query(
        func.date(PerformanceData.timestamp).label('date'),
        func.avg(PerformanceData.value).label('avg_cpu')
    ).filter(
        PerformanceData.metric_type == 'cpu',
        PerformanceData.timestamp >= start_date
    ).group_by(func.date(PerformanceData.timestamp)).all()
    
    return {
        "ont_status_distribution": [
            {"status": item.status, "count": item.count}
            for item in ont_status_data
        ],
        "alarm_severity_distribution": [
            {"severity": item.severity, "count": item.count}
            for item in alarm_severity_data
        ],
        "daily_alarm_trends": [
            {"date": item.date.isoformat(), "count": item.count}
            for item in daily_alarms
        ],
        "cpu_performance_trends": [
            {"date": item.date.isoformat(), "avg_cpu": float(item.avg_cpu or 0)}
            for item in cpu_performance
        ]
    }

@router.get("/reports/export-chart/{chart_type}")
async def export_chart(
    chart_type: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: {"username": "admin", "role": "admin"})
):
    """Export chart as image."""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    plt.style.use('seaborn-v0_8')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    if chart_type == "ont_status":
        # ONT status pie chart
        ont_status_data = db.query(
            ONT.status,
            func.count(ONT.id).label('count')
        ).group_by(ONT.status).all()
        
        labels = [item.status for item in ont_status_data]
        sizes = [item.count for item in ont_status_data]
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title('ONT Status Distribution')
        
    elif chart_type == "alarm_trends":
        # Daily alarm trends line chart
        daily_alarms = db.query(
            func.date(Alarm.raised_at).label('date'),
            func.count(Alarm.id).label('count')
        ).filter(
            Alarm.raised_at >= start_date
        ).group_by(func.date(Alarm.raised_at)).order_by('date').all()
        
        dates = [item.date for item in daily_alarms]
        counts = [item.count for item in daily_alarms]
        
        ax.plot(dates, counts, marker='o', linewidth=2, markersize=6)
        ax.set_title('Daily Alarm Trends')
        ax.set_xlabel('Date')
        ax.set_ylabel('Number of Alarms')
        ax.grid(True, alpha=0.3)
        
    elif chart_type == "performance":
        # CPU performance trends
        cpu_performance = db.query(
            func.date(PerformanceData.timestamp).label('date'),
            func.avg(PerformanceData.value).label('avg_cpu')
        ).filter(
            PerformanceData.metric_type == 'cpu',
            PerformanceData.timestamp >= start_date
        ).group_by(func.date(PerformanceData.timestamp)).order_by('date').all()
        
        dates = [item.date for item in cpu_performance]
        cpu_values = [float(item.avg_cpu or 0) for item in cpu_performance]
        
        ax.plot(dates, cpu_values, marker='s', linewidth=2, markersize=6, color='#ff6b6b')
        ax.set_title('Average CPU Utilization Trends')
        ax.set_xlabel('Date')
        ax.set_ylabel('CPU Utilization (%)')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chart type"
        )
    
    plt.tight_layout()
    
    # Save to bytes
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    return Response(
        content=img_buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={chart_type}_chart.png"}
    )

# Helper functions
async def format_report_output(data: List[Any], format_type: str, title: str):
    """Format report data based on requested format."""
    
    if format_type == "json":
        return {
            "title": title,
            "generated_at": datetime.utcnow(),
            "data": [item.dict() if hasattr(item, 'dict') else item for item in data]
        }
    
    elif format_type == "csv":
        if not data:
            return Response(content="", media_type="text/csv")
        
        # Convert to DataFrame
        df_data = [item.dict() if hasattr(item, 'dict') else item for item in data]
        df = pd.DataFrame(df_data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={title.lower().replace(' ', '_')}.csv"}
        )
    
    elif format_type == "excel":
        if not data:
            return Response(content=b"", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Convert to DataFrame
        df_data = [item.dict() if hasattr(item, 'dict') else item for item in data]
        df = pd.DataFrame(df_data)
        
        # Convert to Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Report', index=False)
        
        excel_buffer.seek(0)
        
        return Response(
            content=excel_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={title.lower().replace(' ', '_')}.xlsx"}
        )
    
    elif format_type == "pdf":
        return await generate_pdf_report(data, title)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format type. Supported formats: json, csv, excel, pdf"
        )

async def generate_pdf_report(data: List[Any], title: str):
    """Generate PDF report."""
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Content
    content = []
    
    # Title
    content.append(Paragraph(title, title_style))
    content.append(Spacer(1, 20))
    
    # Generated timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    content.append(Paragraph(f"Generated: {timestamp}", styles['Normal']))
    content.append(Spacer(1, 20))
    
    if data:
        # Convert data to table format
        df_data = [item.dict() if hasattr(item, 'dict') else item for item in data]
        df = pd.DataFrame(df_data)
        
        # Create table data
        table_data = [list(df.columns)]  # Headers
        for _, row in df.iterrows():
            table_data.append([str(val) for val in row.values])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
    else:
        content.append(Paragraph("No data available for the selected criteria.", styles['Normal']))
    
    # Build PDF
    doc.build(content)
    pdf_buffer.seek(0)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={title.lower().replace(' ', '_')}.pdf"}
    )