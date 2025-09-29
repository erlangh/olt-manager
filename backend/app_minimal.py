"""
Minimal version of the OLT Manager API for testing without database dependencies.
This version includes basic routes and can be used to verify the application structure.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OLT Manager API (Minimal)",
    description="Optical Line Terminal Management System - Minimal Version",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic models for testing
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str

class APIInfo(BaseModel):
    title: str
    version: str
    description: str
    endpoints: int
    status: str

class MockOLT(BaseModel):
    id: int
    name: str
    ip_address: str
    location: Optional[str] = None
    status: str = "online"

class MockONT(BaseModel):
    id: int
    serial_number: str
    olt_id: int
    status: str = "online"

# Mock data
mock_olts = [
    MockOLT(id=1, name="OLT-001", ip_address="192.168.1.100", location="Building A", status="online"),
    MockOLT(id=2, name="OLT-002", ip_address="192.168.1.101", location="Building B", status="online"),
]

mock_onts = [
    MockONT(id=1, serial_number="ONT001", olt_id=1, status="online"),
    MockONT(id=2, serial_number="ONT002", olt_id=1, status="offline"),
    MockONT(id=3, serial_number="ONT003", olt_id=2, status="online"),
]

# Root endpoint
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "OLT Manager API (Minimal Version)",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        service="olt-manager-minimal",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

# API info endpoint
@app.get("/api/v1/info", response_model=APIInfo)
async def api_info():
    """Get API information."""
    return APIInfo(
        title=app.title,
        version=app.version,
        description=app.description,
        endpoints=len(app.routes),
        status="running"
    )

# Mock OLT endpoints
@app.get("/api/v1/olts", response_model=List[MockOLT])
async def get_olts():
    """Get all OLTs (mock data)."""
    return mock_olts

@app.get("/api/v1/olts/{olt_id}", response_model=MockOLT)
async def get_olt(olt_id: int):
    """Get specific OLT by ID (mock data)."""
    for olt in mock_olts:
        if olt.id == olt_id:
            return olt
    raise HTTPException(status_code=404, detail="OLT not found")

# Mock ONT endpoints
@app.get("/api/v1/onts", response_model=List[MockONT])
async def get_onts():
    """Get all ONTs (mock data)."""
    return mock_onts

@app.get("/api/v1/onts/{ont_id}", response_model=MockONT)
async def get_ont(ont_id: int):
    """Get specific ONT by ID (mock data)."""
    for ont in mock_onts:
        if ont.id == ont_id:
            return ont
    raise HTTPException(status_code=404, detail="ONT not found")

# Mock authentication endpoint
@app.post("/api/v1/auth/login")
async def login():
    """Mock login endpoint."""
    return {
        "access_token": "mock_token_12345",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
    }

# Mock monitoring endpoint
@app.get("/api/v1/monitoring/status")
async def monitoring_status():
    """Mock monitoring status endpoint."""
    return {
        "total_olts": len(mock_olts),
        "online_olts": len([olt for olt in mock_olts if olt.status == "online"]),
        "total_onts": len(mock_onts),
        "online_onts": len([ont for ont in mock_onts if ont.status == "online"]),
        "system_status": "healthy",
        "last_update": "2024-01-15T10:30:00Z"
    }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )

if __name__ == "__main__":
    print("🚀 Starting OLT Manager API (Minimal Version)")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("ℹ️  API Info: http://localhost:8000/api/v1/info")
    
    uvicorn.run(
        "app_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )