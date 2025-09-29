# Manual Deployment Steps for OLT Manager

Since the auto-deploy scripts require SSH key authentication, here are the manual steps to deploy the OLT Manager application to the server `41.216.186.253:2225`.

## Prerequisites
- SSH access to server: `ssh -p 2225 root@41.216.186.253`
- Server password for root user

## Step 1: Connect to Server
```bash
ssh -p 2225 root@41.216.186.253
```

## Step 2: Install Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install Python and PostgreSQL
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib unzip

# Start PostgreSQL service
systemctl start postgresql
systemctl enable postgresql
```

## Step 3: Setup Database
```bash
# Switch to postgres user and create database
sudo -u postgres psql -c "CREATE DATABASE olt_manager;"
sudo -u postgres psql -c "CREATE USER oltmanager WITH PASSWORD 'oltmanager123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE olt_manager TO oltmanager;"
```

## Step 4: Create Application Directory
```bash
# Create app directory
mkdir -p /opt/olt-manager
cd /opt/olt-manager
```

## Step 5: Upload Application Files
You need to manually copy these files from your local machine to the server:

### Files to copy:
1. `deployment/main_simple.py` → `/opt/olt-manager/main_simple.py`
2. `deployment/olt-manager-dashboard.html` → `/opt/olt-manager/olt-manager-dashboard.html`
3. `deployment/requirements.txt` → `/opt/olt-manager/requirements.txt`
4. `deployment/.env.production` → `/opt/olt-manager/.env`
5. `deployment/init_database.py` → `/opt/olt-manager/init_database.py`

### Using SCP to copy files:
```bash
# From your local machine (Windows PowerShell):
scp -P 2225 deployment/main_simple.py root@41.216.186.253:/opt/olt-manager/
scp -P 2225 deployment/olt-manager-dashboard.html root@41.216.186.253:/opt/olt-manager/
scp -P 2225 deployment/requirements.txt root@41.216.186.253:/opt/olt-manager/
scp -P 2225 deployment/.env.production root@41.216.186.253:/opt/olt-manager/.env
scp -P 2225 deployment/init_database.py root@41.216.186.253:/opt/olt-manager/
```

## Step 6: Setup Python Environment (On Server)
```bash
cd /opt/olt-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 7: Initialize Database (On Server)
```bash
cd /opt/olt-manager
source venv/bin/activate
python init_database.py
```

## Step 8: Create Systemd Service (On Server)
```bash
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

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable olt-manager
systemctl start olt-manager
```

## Step 9: Verify Deployment (On Server)
```bash
# Check service status
systemctl status olt-manager

# Check if port 8000 is listening
netstat -tlnp | grep 8000

# Test HTTP response
curl -I http://localhost:8000
```

## Step 10: Configure Firewall (If needed)
```bash
# Allow port 8000 through firewall
ufw allow 8000
```

## Access Information
After successful deployment, the application will be accessible at:

- **Server Direct**: `http://41.216.186.253:8000`
- **Cloudflare Domain**: `https://olt.remoteapps.my.id` (if tunnel is configured)

### Login Credentials:
- **Username**: `admin`
- **Password**: `admin123`

## Troubleshooting
- **Check logs**: `journalctl -u olt-manager -f`
- **Restart service**: `systemctl restart olt-manager`
- **Check database**: `sudo -u postgres psql -d olt_manager -c "SELECT * FROM users;"`

## Quick Commands for File Transfer
If you prefer to create a package and transfer it:

```bash
# On local machine - create deployment package
zip -r olt-manager-deploy.zip deployment/

# Transfer to server
scp -P 2225 olt-manager-deploy.zip root@41.216.186.253:/tmp/

# On server - extract and setup
cd /tmp
unzip olt-manager-deploy.zip
cp deployment/* /opt/olt-manager/
```