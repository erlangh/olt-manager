#!/bin/bash

# Server Setup Script for OLT Manager
# Run this script on the server after transferring the deployment package

set -e

echo "=== OLT Manager Server Setup ==="
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
    cp deployment/* /opt/olt-manager/
    mv /opt/olt-manager/.env.production /opt/olt-manager/.env
    echo "Deployment package extracted successfully"
else
    echo "Error: Deployment package not found at /tmp/olt-manager-deploy.zip"
    exit 1
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