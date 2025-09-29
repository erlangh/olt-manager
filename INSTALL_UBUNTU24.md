# OLT Manager ZTE C320 - Ubuntu 24.04 Installation Guide

## 📋 Overview

This guide provides comprehensive instructions for installing the OLT Manager ZTE C320 system on Ubuntu 24.04 LTS. The system includes a FastAPI backend, React frontend, PostgreSQL database, and monitoring capabilities.

## 🔧 System Requirements

### Minimum Hardware Requirements
- **CPU**: 2 cores @ 2.0GHz (4 cores @ 2.5GHz recommended)
- **RAM**: 4GB (8GB recommended for production)
- **Storage**: 25GB free space (100GB recommended for production)
- **Network**: Internet connection for package downloads (minimum 10Mbps)

### Software Requirements
- **OS**: Ubuntu 24.04 LTS (Fresh installation recommended)
- **User**: Root access or sudo privileges
- **Network**: Open ports 80, 443, 8000, 3000, 5432 (PostgreSQL), 6379 (Redis)
- **Dependencies**: 
  - Python 3.12+
  - Node.js 20.x LTS
  - PostgreSQL 16+
  - Redis 7.x
  - Nginx 1.24+

## 🚀 Quick Installation

### Option 1: Automated Installation (Recommended)

```bash
# Download and run the installation script
curl -fsSL https://raw.githubusercontent.com/your-repo/olt-manager/main/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh

# Or one-liner installation
curl -fsSL https://raw.githubusercontent.com/your-repo/olt-manager/main/install.sh | sudo bash
```

### Option 2: Docker Installation (Alternative)

```bash
# Clone repository
git clone https://github.com/your-repo/olt-manager.git
cd olt-manager

# Start with Docker Compose
docker-compose up -d

# Access application at http://localhost
```

### Option 3: Manual Installation

Follow the detailed steps below for manual installation.

## 📦 Manual Installation Steps

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools and dependencies
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    vim \
    htop \
    net-tools

# Install additional development tools
sudo apt install -y \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    python3-dev \
    gcc \
    g++ \
    make
```

### 2. Install Python 3.12

```bash
# Add deadsnakes PPA for Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.12 and related packages
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3.12-distutils \
    python3-pip \
    python3-setuptools

# Set Python 3.12 as default python3
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Verify installation
python3 --version  # Should show Python 3.12.x
pip3 --version

# Install pipx for global Python tools
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### 3. Install Node.js 20 LTS

```bash
# Install Node.js 20 LTS from NodeSource
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Alternative: Install using snap (if preferred)
# sudo snap install node --classic

# Install global npm packages
sudo npm install -g npm@latest
sudo npm install -g pm2 serve

# Verify installation
node --version   # Should show v20.x.x
npm --version    # Should show 10.x.x or higher
pm2 --version    # Should show PM2 version
```

### 4. Install PostgreSQL 16

```bash
# Install PostgreSQL 16 from official repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL 16 and additional tools
sudo apt install -y \
    postgresql-16 \
    postgresql-client-16 \
    postgresql-contrib-16 \
    libpq-dev \
    postgresql-16-postgis-3

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure PostgreSQL
sudo -u postgres psql << EOF
-- Create database and user
CREATE USER oltmanager WITH PASSWORD 'oltmanager123!@#';
CREATE DATABASE oltmanager_db OWNER oltmanager;
GRANT ALL PRIVILEGES ON DATABASE oltmanager_db TO oltmanager;
ALTER USER oltmanager CREATEDB;

-- Configure connection settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
\q
EOF

# Test connection
sudo -u postgres psql -c "SELECT version();"
```

### 5. Install Redis 7.x

```bash
# Install Redis from official repository
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update

# Install Redis server and tools
sudo apt install -y redis-server redis-tools

# Configure Redis
sudo tee /etc/redis/redis.conf.d/olt-manager.conf > /dev/null << EOF
# OLT Manager Redis Configuration
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
EOF

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping  # Should return PONG
redis-cli info server | grep redis_version
```

### 6. Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 7. Install SNMP Tools

```bash
# Install SNMP packages
sudo apt install -y snmp snmp-mibs-downloader

# Download MIBs
sudo download-mibs
```

### 8. Setup Application

```bash
# Create application user and group
sudo groupadd --system oltmanager
sudo useradd --system --gid oltmanager --shell /bin/bash --home /opt/olt-manager --create-home oltmanager

# Create application directories
sudo mkdir -p /opt/olt-manager/{backend,frontend,logs,backups}
sudo chown -R oltmanager:oltmanager /opt/olt-manager

# Clone or copy application files
cd /opt/olt-manager
# If using git:
# sudo -u oltmanager git clone https://github.com/your-repo/olt-manager.git .
# Or copy your application files here

# Setup backend environment
cd backend
sudo -u oltmanager python3 -m venv venv
sudo -u oltmanager bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"
sudo -u oltmanager bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Create environment configuration
sudo -u oltmanager tee .env > /dev/null << EOF
# Database Configuration
DATABASE_URL=postgresql://oltmanager:oltmanager123!@#@localhost:5432/oltmanager_db
POSTGRES_USER=oltmanager
POSTGRES_PASSWORD=oltmanager123!@#
POSTGRES_DB=oltmanager_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000","http://localhost"]

# SNMP Configuration
SNMP_TIMEOUT=5
SNMP_RETRIES=3

# Monitoring Configuration
MONITORING_INTERVAL=60
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_SMTP_SERVER=
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=
ALERT_EMAIL_PASSWORD=
EOF

# Initialize database
sudo -u oltmanager bash -c "source venv/bin/activate && python init_db.py"

# Setup frontend
cd ../frontend
sudo -u oltmanager npm ci --production
sudo -u oltmanager npm run build

# Set proper permissions
sudo chown -R oltmanager:oltmanager /opt/olt-manager
sudo chmod -R 755 /opt/olt-manager
sudo chmod 600 /opt/olt-manager/backend/.env
```

### 9. Create Systemd Services

#### Backend Service
```bash
sudo tee /etc/systemd/system/olt-manager-backend.service > /dev/null << EOF
[Unit]
Description=OLT Manager Backend API
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=oltmanager
Group=oltmanager
WorkingDirectory=/opt/olt-manager/backend
Environment=PATH=/opt/olt-manager/backend/venv/bin
ExecStart=/opt/olt-manager/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=olt-manager-backend

[Install]
WantedBy=multi-user.target
EOF
```

#### Frontend Service
```bash
sudo tee /etc/systemd/system/olt-manager-frontend.service > /dev/null << EOF
[Unit]
Description=OLT Manager Frontend
After=network.target

[Service]
Type=simple
User=oltmanager
Group=oltmanager
WorkingDirectory=/opt/olt-manager/frontend
ExecStart=/usr/bin/npx serve -s build -l 3000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=olt-manager-frontend

[Install]
WantedBy=multi-user.target
EOF
```

### 10. Configure Nginx

```bash
sudo tee /etc/nginx/sites-available/olt-manager > /dev/null << EOF
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/olt-manager /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 11. Configure Firewall

```bash
# Enable UFW
sudo ufw --force enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow backend API (optional, for direct access)
sudo ufw allow 8000/tcp

# Reload firewall
sudo ufw reload
```

### 12. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable olt-manager-backend
sudo systemctl enable olt-manager-frontend
sudo systemctl start olt-manager-backend
sudo systemctl start olt-manager-frontend

# Check service status
sudo systemctl status olt-manager-backend
sudo systemctl status olt-manager-frontend
```

## 🔍 Verification

### Check Services
```bash
# Check all services
sudo systemctl status olt-manager-backend olt-manager-frontend nginx postgresql redis-server

# Check logs
sudo journalctl -u olt-manager-backend -f
sudo journalctl -u olt-manager-frontend -f
```

### Test Access
```bash
# Test backend API
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Test through Nginx
curl http://localhost/api/health
```

## 🌐 Access Information

After successful installation:

- **Web Interface**: `http://your-server-ip` or `http://localhost`
- **API Documentation**: `http://your-server-ip/api/docs`
- **Direct Backend**: `http://your-server-ip:8000/docs`
- **Default Login**: `admin` / `admin123`

## 🔧 Service Management

```bash
# Start services
sudo systemctl start olt-manager-{backend,frontend}

# Stop services
sudo systemctl stop olt-manager-{backend,frontend}

# Restart services
sudo systemctl restart olt-manager-{backend,frontend}

# Check status
sudo systemctl status olt-manager-{backend,frontend}

# View logs
sudo journalctl -u olt-manager-backend -f
sudo journalctl -u olt-manager-frontend -f
```

## 📁 Important Directories

- **Application**: `/opt/olt-manager/`
- **Backend**: `/opt/olt-manager/backend/`
- **Frontend**: `/opt/olt-manager/frontend/`
- **Configuration**: `/opt/olt-manager/backend/.env`
- **Logs**: `/var/log/olt-manager/` (if configured)
- **Nginx Config**: `/etc/nginx/sites-available/olt-manager`
- **Systemd Services**: `/etc/systemd/system/olt-manager-*`

## 🔐 Security Considerations

### 1. System Security

```bash
# Configure automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Install and configure fail2ban
sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Database Security

```bash
# Secure PostgreSQL installation
sudo -u postgres psql << EOF
-- Remove default postgres user password (if not needed)
-- ALTER USER postgres PASSWORD NULL;

-- Create read-only user for monitoring
CREATE USER oltmonitor WITH PASSWORD 'monitor_$(openssl rand -hex 16)';
GRANT CONNECT ON DATABASE oltmanager_db TO oltmonitor;
GRANT USAGE ON SCHEMA public TO oltmonitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO oltmonitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO oltmonitor;

-- Configure connection limits
ALTER USER oltmanager CONNECTION LIMIT 50;
ALTER USER oltmonitor CONNECTION LIMIT 10;
\q
EOF

# Configure PostgreSQL security
sudo tee -a /etc/postgresql/16/main/postgresql.conf > /dev/null << EOF
# Security settings
ssl = on
ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key'
password_encryption = scram-sha-256
log_connections = on
log_disconnections = on
log_failed_connections = on
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. Application Security

```bash
# Set secure file permissions
sudo chmod 700 /opt/olt-manager/backend/.env
sudo chmod 750 /opt/olt-manager/logs
sudo chmod 755 /opt/olt-manager/backups

# Create log rotation configuration
sudo tee /etc/logrotate.d/olt-manager > /dev/null << EOF
/opt/olt-manager/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 oltmanager oltmanager
    postrotate
        systemctl reload olt-manager-backend olt-manager-frontend
    endscript
}
EOF
```

### 4. Network Security

```bash
# Configure UFW with specific rules
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if needed)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific IPs for management (replace with your IPs)
# sudo ufw allow from 192.168.1.0/24 to any port 8000
# sudo ufw allow from 192.168.1.0/24 to any port 5432

# Enable firewall
sudo ufw --force enable
sudo ufw status verbose
```

### 5. SSL/TLS Configuration (Production)

```bash
# Install Certbot for Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (replace with your domain)
# sudo certbot --nginx -d your-domain.com

# Configure automatic renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
sudo certbot renew --dry-run
```

### 6. Security Checklist

- [ ] **Change Default Passwords**: Update all default credentials immediately
- [ ] **Enable SSL/TLS**: Configure HTTPS for production environments
- [ ] **Firewall Configuration**: Restrict access to necessary ports only
- [ ] **Database Security**: Use strong passwords and limit connections
- [ ] **Regular Updates**: Keep system and dependencies updated
- [ ] **Backup Strategy**: Implement automated backup procedures
- [ ] **Monitoring**: Set up log monitoring and alerting
- [ ] **Access Control**: Implement proper user roles and permissions
- [ ] **Network Segmentation**: Isolate database and application servers
- [ ] **Security Scanning**: Regular vulnerability assessments

## 🐛 Troubleshooting

### Common Installation Issues

#### 1. Python Installation Issues

**Problem**: Python 3.12 not found or pip installation fails
```bash
# Solution: Install Python 3.12 from deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3.12-distutils
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
```

**Problem**: Virtual environment creation fails
```bash
# Solution: Ensure python3.12-venv is installed
sudo apt install -y python3.12-venv
python3.12 -m venv /opt/olt-manager/backend/venv --clear
```

#### 2. Node.js and npm Issues

**Problem**: Node.js version conflicts or npm permission errors
```bash
# Solution: Clean npm cache and reinstall
sudo rm -rf /usr/local/lib/node_modules
sudo rm -rf ~/.npm
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Fix npm permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

**Problem**: Frontend build fails with memory issues
```bash
# Solution: Increase Node.js memory limit
export NODE_OPTIONS="--max-old-space-size=4096"
cd /opt/olt-manager/frontend
npm run build
```

#### 3. Database Connection Issues

**Problem**: PostgreSQL connection refused
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check PostgreSQL configuration
sudo -u postgres psql -c "SELECT version();"

# Verify database exists
sudo -u postgres psql -l | grep oltmanager_db

# Test connection with credentials
psql -h localhost -U oltmanager -d oltmanager_db -c "SELECT 1;"
```

**Problem**: Database authentication failed
```bash
# Reset database password
sudo -u postgres psql << EOF
ALTER USER oltmanager WITH PASSWORD 'your_new_password';
\q
EOF

# Update .env file with new password
sudo nano /opt/olt-manager/backend/.env
```

#### 4. Redis Connection Issues

**Problem**: Redis connection failed
```bash
# Check Redis status
sudo systemctl status redis-server
sudo systemctl start redis-server

# Test Redis connection
redis-cli ping

# Check Redis configuration
sudo nano /etc/redis/redis.conf
# Ensure: bind 127.0.0.1 ::1
# Ensure: port 6379
sudo systemctl restart redis-server
```

#### 5. Service Management Issues

**Problem**: Backend service fails to start
```bash
# Check service status and logs
sudo systemctl status olt-manager-backend
sudo journalctl -u olt-manager-backend -f

# Check application logs
sudo tail -f /opt/olt-manager/logs/backend.log

# Restart service with debug
sudo systemctl stop olt-manager-backend
sudo -u oltmanager /opt/olt-manager/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Problem**: Frontend service fails to start
```bash
# Check service status
sudo systemctl status olt-manager-frontend
sudo journalctl -u olt-manager-frontend -f

# Manual start for debugging
sudo -u oltmanager npx serve -s /opt/olt-manager/frontend/build -l 3000
```

#### 6. Nginx Configuration Issues

**Problem**: Nginx fails to start or proxy errors
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx

# Check if ports are in use
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

#### 7. Permission Issues

**Problem**: File permission errors
```bash
# Fix ownership and permissions
sudo chown -R oltmanager:oltmanager /opt/olt-manager/
sudo chmod -R 755 /opt/olt-manager/
sudo chmod 700 /opt/olt-manager/backend/.env
sudo chmod 750 /opt/olt-manager/logs/
```

#### 8. Firewall Issues

**Problem**: Services not accessible from external networks
```bash
# Check UFW status
sudo ufw status verbose

# Allow specific ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # For direct backend access (development only)

# Check iptables rules
sudo iptables -L -n
```

#### 9. Memory and Performance Issues

**Problem**: High memory usage or slow performance
```bash
# Check system resources
htop
free -h
df -h

# Optimize PostgreSQL
sudo nano /etc/postgresql/16/main/postgresql.conf
# Adjust: shared_buffers, effective_cache_size, work_mem

# Optimize Redis
sudo nano /etc/redis/redis.conf
# Adjust: maxmemory, maxmemory-policy

# Restart services
sudo systemctl restart postgresql redis-server
```

#### 10. SSL/TLS Certificate Issues

**Problem**: SSL certificate errors
```bash
# Check certificate status
sudo certbot certificates

# Renew certificates
sudo certbot renew --dry-run
sudo certbot renew

# Manual certificate generation
sudo certbot --nginx -d your-domain.com --email your-email@domain.com
```

### Diagnostic Commands

```bash
# System information
uname -a
lsb_release -a
free -h
df -h

# Service status check
sudo systemctl status postgresql redis-server nginx olt-manager-backend olt-manager-frontend

# Port usage check
sudo netstat -tlnp | grep -E ':(80|443|3000|5432|6379|8000)'

# Log monitoring
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
sudo tail -f /opt/olt-manager/logs/backend.log
sudo journalctl -u olt-manager-backend -f
sudo journalctl -u olt-manager-frontend -f

# Database connectivity test
psql -h localhost -U oltmanager -d oltmanager_db -c "SELECT current_timestamp;"

# Redis connectivity test
redis-cli ping
redis-cli info server

# Application health check
curl -I http://localhost:3000
curl -I http://localhost:8000/health
```

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Always start by examining the relevant log files
2. **Service Status**: Verify all required services are running
3. **Network Connectivity**: Test database and Redis connections
4. **Permissions**: Ensure proper file ownership and permissions
5. **Resources**: Monitor system resources (CPU, memory, disk)
6. **Documentation**: Refer to official documentation for each component
7. **Community**: Search for similar issues in project repositories or forums

### Log Locations

- **Backend**: `sudo journalctl -u olt-manager-backend`
- **Frontend**: `sudo journalctl -u olt-manager-frontend`
- **Nginx**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`
- **System**: `sudo journalctl -xe`

## 📞 Support

For issues and support:

1. Check the troubleshooting section above
2. Review service logs for error messages
3. Ensure all dependencies are properly installed
4. Verify network connectivity and firewall settings
5. Check system resources (CPU, memory, disk space)

## 🔄 Updates

To update the application:

```bash
# Stop services
sudo systemctl stop olt-manager-{backend,frontend}

# Backup current installation
sudo cp -r /opt/olt-manager /opt/olt-manager.backup.$(date +%Y%m%d)

# Update application files
cd /opt/olt-manager
# Update your code here

# Update dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
npm run build

# Start services
sudo systemctl start olt-manager-{backend,frontend}
```

---

**Note**: This installation guide assumes a fresh Ubuntu 24.04 LTS installation. Adapt the instructions as needed for your specific environment.