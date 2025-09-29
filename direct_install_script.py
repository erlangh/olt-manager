#!/usr/bin/env python3
"""
Direct Installation Script for OLT Manager
Installs OLT Manager directly on Linux server via SSH
"""

import os
import sys

def create_main_app():
    """Create the main application file"""
    main_content = '''#!/usr/bin/env python3
"""
OLT Manager - Simple FastAPI Application
Direct installation version
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import jwt
import datetime
from typing import Optional, List
import os

# Configuration
DATABASE_URL = "postgresql://oltmanager:oltmanager123@localhost/olt_manager"
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

app = FastAPI(title="OLT Manager", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Models
class User(BaseModel):
    username: str
    password: str

class OLT(BaseModel):
    name: str
    ip_address: str
    snmp_community: str = "public"
    location: Optional[str] = None

class ONT(BaseModel):
    olt_id: int
    ont_id: str
    serial_number: str
    status: str = "active"

# Authentication functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Initialize database
def init_database():
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create OLT table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS olts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                ip_address VARCHAR(15) NOT NULL,
                snmp_community VARCHAR(50) DEFAULT 'public',
                location VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create ONT table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS onts (
                id SERIAL PRIMARY KEY,
                olt_id INTEGER REFERENCES olts(id),
                ont_id VARCHAR(50) NOT NULL,
                serial_number VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default admin user
        admin_password = hash_password("admin123")
        cur.execute("""
            INSERT INTO users (username, password_hash) 
            VALUES (%s, %s) 
            ON CONFLICT (username) DO NOTHING
        """, ("admin", admin_password))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Routes
@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OLT Manager</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
            .content { padding: 20px; }
            .btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; }
            .status { background: #27ae60; color: white; padding: 10px; border-radius: 3px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 OLT Manager</h1>
                <p>Optical Line Terminal Management System</p>
            </div>
            <div class="content">
                <div class="status">✅ System is running successfully!</div>
                <h2>Features:</h2>
                <ul>
                    <li>OLT Device Management</li>
                    <li>ONT Monitoring</li>
                    <li>User Authentication</li>
                    <li>REST API</li>
                </ul>
                <h2>API Endpoints:</h2>
                <ul>
                    <li><a href="/docs" class="btn">📚 API Documentation</a></li>
                    <li><a href="/health" class="btn">🔍 Health Check</a></li>
                    <li><a href="/api/olts" class="btn">📡 OLT List</a></li>
                </ul>
                <h2>Default Login:</h2>
                <p><strong>Username:</strong> admin<br>
                <strong>Password:</strong> admin123</p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/api/login")
async def login(user: User):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (user.username,))
        db_user = cur.fetchone()
        
        if not db_user or not verify_password(user.password, db_user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    
    finally:
        conn.close()

@app.get("/api/olts")
async def get_olts(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM olts ORDER BY created_at DESC")
        olts = cur.fetchall()
        return {"olts": olts}
    
    finally:
        conn.close()

@app.post("/api/olts")
async def create_olt(olt: OLT, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO olts (name, ip_address, snmp_community, location)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (olt.name, olt.ip_address, olt.snmp_community, olt.location))
        
        new_olt = cur.fetchone()
        conn.commit()
        return {"message": "OLT created successfully", "olt": new_olt}
    
    finally:
        conn.close()

@app.get("/api/onts")
async def get_onts(current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT o.*, olt.name as olt_name 
            FROM onts o 
            LEFT JOIN olts olt ON o.olt_id = olt.id 
            ORDER BY o.created_at DESC
        """)
        onts = cur.fetchall()
        return {"onts": onts}
    
    finally:
        conn.close()

@app.post("/api/onts")
async def create_ont(ont: ONT, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO onts (olt_id, ont_id, serial_number, status)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (ont.olt_id, ont.ont_id, ont.serial_number, ont.status))
        
        new_ont = cur.fetchone()
        conn.commit()
        return {"message": "ONT created successfully", "ont": new_ont}
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting OLT Manager...")
    print("📊 Initializing database...")
    
    if init_database():
        print("✅ Database initialized successfully!")
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)
    
    print("🌐 Starting web server...")
    print("📍 Access: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔐 Login: admin / admin123")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open('/opt/olt-manager/main.py', 'w') as f:
        f.write(main_content)
    print("✅ Main application file created")

def create_requirements():
    """Create requirements.txt file"""
    requirements_content = '''fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
pyjwt==2.8.0
python-multipart==0.0.6
'''
    
    with open('/opt/olt-manager/requirements.txt', 'w') as f:
        f.write(requirements_content)
    print("✅ Requirements file created")

def create_systemd_service():
    """Create systemd service file"""
    service_content = '''[Unit]
Description=OLT Manager Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/olt-manager
Environment=PATH=/opt/olt-manager/venv/bin
ExecStart=/opt/olt-manager/venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
'''
    
    with open('/etc/systemd/system/olt-manager.service', 'w') as f:
        f.write(service_content)
    print("✅ Systemd service file created")

def main():
    """Main installation function"""
    print("🚀 OLT Manager Direct Installation")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('/opt/olt-manager'):
        print("❌ Please run this script from /opt/olt-manager directory")
        return False
    
    try:
        # Create application files
        create_main_app()
        create_requirements()
        
        # Create Python virtual environment
        print("📦 Creating Python virtual environment...")
        os.system("python3 -m venv venv")
        
        # Install dependencies
        print("📥 Installing Python dependencies...")
        os.system("./venv/bin/pip install --upgrade pip")
        os.system("./venv/bin/pip install -r requirements.txt")
        
        # Create systemd service
        create_systemd_service()
        
        # Enable and start service
        print("🔧 Setting up systemd service...")
        os.system("systemctl daemon-reload")
        os.system("systemctl enable olt-manager")
        os.system("systemctl start olt-manager")
        
        print("\n" + "=" * 50)
        print("✅ OLT Manager installation completed!")
        print("🌐 Access: http://your-server-ip:8000")
        print("📚 API Docs: http://your-server-ip:8000/docs")
        print("🔐 Default Login: admin / admin123")
        print("\n📋 Management Commands:")
        print("  systemctl status olt-manager    # Check status")
        print("  systemctl restart olt-manager   # Restart service")
        print("  systemctl logs olt-manager      # View logs")
        
        return True
        
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

if __name__ == "__main__":
    main()