#!/bin/bash

# Fixed Server Setup Script for OLT Manager
# Run this script on the server after transferring the deployment package

set -e

echo "=== OLT Manager Server Setup (Fixed) ==="
echo "Starting deployment process..."

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib unzip curl

# Start PostgreSQL
echo "Starting PostgreSQL service..."
systemctl start postgresql
systemctl enable postgresql

# Setup database
echo "Setting up database..."
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'olt_manager'" | grep -q 1 || sudo -u postgres createdb olt_manager
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'oltmanager'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER oltmanager WITH PASSWORD 'oltmanager123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE olt_manager TO oltmanager;"

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/olt-manager
cd /opt/olt-manager

# Extract deployment package
echo "Extracting deployment package..."
if [ -f "/tmp/olt-manager-deploy.zip" ]; then
    cd /tmp
    unzip -o olt-manager-deploy.zip
    
    # List extracted files for debugging
    echo "Extracted files:"
    ls -la
    
    # Copy files directly (the zip contains files in deployment/ folder)
    if [ -d "deployment" ]; then
        echo "Copying from deployment directory..."
        cp deployment/main_simple.py /opt/olt-manager/
        cp deployment/olt-manager-dashboard.html /opt/olt-manager/
        cp deployment/requirements.txt /opt/olt-manager/
        cp deployment/.env.production /opt/olt-manager/.env
        cp deployment/init_database.py /opt/olt-manager/
    else
        echo "Deployment directory not found, checking for direct files..."
        # If files are extracted directly
        if [ -f "main_simple.py" ]; then
            cp main_simple.py /opt/olt-manager/
        fi
        if [ -f "olt-manager-dashboard.html" ]; then
            cp olt-manager-dashboard.html /opt/olt-manager/
        fi
        if [ -f "requirements.txt" ]; then
            cp requirements.txt /opt/olt-manager/
        fi
        if [ -f ".env.production" ]; then
            cp .env.production /opt/olt-manager/.env
        fi
        if [ -f "init_database.py" ]; then
            cp init_database.py /opt/olt-manager/
        fi
    fi
    
    echo "Files copied successfully"
    echo "Files in /opt/olt-manager:"
    ls -la /opt/olt-manager/
else
    echo "Error: Deployment package not found at /tmp/olt-manager-deploy.zip"
    exit 1
fi

# Create init_database.py if it doesn't exist
if [ ! -f "/opt/olt-manager/init_database.py" ]; then
    echo "Creating init_database.py..."
    cat > /opt/olt-manager/init_database.py << 'EOF'
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from dotenv import load_dotenv

load_dotenv()

def init_database():
    try:
        # Database connection
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'olt_manager'),
            user=os.getenv('DB_USER', 'oltmanager'),
            password=os.getenv('DB_PASSWORD', 'oltmanager123'),
            port=os.getenv('DB_PORT', '5432')
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if admin user exists
        cursor.execute('SELECT id FROM users WHERE username = %s', ('admin',))
        if not cursor.fetchone():
            # Create admin user
            password = 'admin123'
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
            ''', ('admin', 'admin@oltmanager.com', password_hash, 'admin', True))
            
            print('Admin user created successfully')
        else:
            print('Admin user already exists')
        
        conn.commit()
        cursor.close()
        conn.close()
        print('Database initialization completed')
        
    except Exception as e:
        print(f'Database initialization error: {e}')

if __name__ == '__main__':
    init_database()
EOF
fi

# Setup Python environment
echo "Setting up Python environment..."
cd /opt/olt-manager
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python init_database.py

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/olt-manager.service << EOF
[Unit]
Description=OLT Manager Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/olt-manager
Environment=PATH=/opt/olt-manager/venv/bin
ExecStart=/opt/olt-manager/venv/bin/python main_simple.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "Starting OLT Manager service..."
systemctl daemon-reload
systemctl enable olt-manager
systemctl start olt-manager

# Wait for service to start
sleep 5

# Verify deployment
echo "Verifying deployment..."
echo "Service Status:"
systemctl status olt-manager --no-pager

echo -e "\nPort Status:"
netstat -tlnp | grep 8000 || echo "Port 8000 not found"

echo -e "\nHTTP Test:"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ || echo "failed")
echo "HTTP Status: $HTTP_STATUS"

# Configure firewall if ufw is available
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    ufw allow 8000
fi

echo ""
echo "=== Deployment Complete ==="
echo "Application Access:"
echo "- Server: http://41.216.186.253:8000"
echo "- Domain: https://olt.remoteapps.my.id"
echo ""
echo "Login Credentials:"
echo "- Username: admin"
echo "- Password: admin123"
echo ""
echo "Management Commands:"
echo "- Check status: systemctl status olt-manager"
echo "- View logs: journalctl -u olt-manager -f"
echo "- Restart: systemctl restart olt-manager"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Deployment successful! Application is running."
else
    echo "⚠️  Deployment completed but application may not be responding correctly."
    echo "Check logs: journalctl -u olt-manager -f"
fi