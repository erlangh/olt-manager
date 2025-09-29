#!/bin/bash

# OLT Manager - Automated Installation Script for Ubuntu Server
# Compatible with Ubuntu 22.04 and 24.04 LTS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/olt-manager"
SERVICE_NAME="olt-manager-backend"
NGINX_SITE="olt-manager"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_status() {
    echo -e "${PURPLE}➤ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    print_status "Checking Ubuntu version..."
    
    if ! grep -q "Ubuntu" /etc/os-release; then
        print_error "This script is designed for Ubuntu systems"
        exit 1
    fi
    
    VERSION=$(lsb_release -rs)
    MAJOR_VERSION=$(echo $VERSION | cut -d. -f1)
    
    if [[ $MAJOR_VERSION -lt 22 ]]; then
        print_error "This script requires Ubuntu 22.04 or newer. Current version: $VERSION"
        exit 1
    fi
    
    if [[ $MAJOR_VERSION -eq 24 ]]; then
        print_success "Ubuntu 24.04 detected - perfect!"
    else
        print_warning "Ubuntu $VERSION detected. Optimized for 24.04 but should work."
    fi
}

update_system() {
    print_header "Updating System Packages"
    
    print_status "Updating package lists..."
    apt update -qq
    
    print_status "Upgrading existing packages..."
    apt upgrade -y -qq
    
    print_status "Installing essential build tools..."
    apt install -y -qq \
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
        tree \
        net-tools \
        pkg-config \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        python3-dev \
        gcc \
        g++ \
        make
    
    print_success "System updated and essential tools installed"
}

install_python() {
    print_header "Installing Python $PYTHON_VERSION"
    
    print_status "Adding deadsnakes PPA for latest Python versions..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update -qq
    
    print_status "Installing Python $PYTHON_VERSION and development tools..."
    apt install -y -qq \
        python$PYTHON_VERSION \
        python$PYTHON_VERSION-dev \
        python$PYTHON_VERSION-venv \
        python$PYTHON_VERSION-distutils \
        python3-setuptools \
        python3-pip
    
    # Install pip for Python 3.12
    curl -sS https://bootstrap.pypa.io/get-pip.py | python$PYTHON_VERSION
    
    # Install pipx
    python$PYTHON_VERSION -m pip install --user pipx
    python$PYTHON_VERSION -m pipx ensurepath
    
    print_success "Python $PYTHON_VERSION installed and configured"
}

install_nodejs() {
    print_header "Installing Node.js $NODE_VERSION"
    
    print_status "Adding NodeSource repository..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    
    print_status "Installing Node.js and npm..."
    apt install -y -qq nodejs
    
    print_status "Installing global npm packages..."
    npm install -g npm@latest pm2 serve
    
    NODE_ACTUAL_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    
    print_success "Node.js $NODE_ACTUAL_VERSION and npm $NPM_VERSION installed"
}

install_postgresql() {
    print_header "Installing PostgreSQL 16"
    
    print_status "Adding PostgreSQL official repository..."
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    apt update -qq
    
    print_status "Installing PostgreSQL 16 and extensions..."
    apt install -y -qq \
        postgresql-16 \
        postgresql-client-16 \
        postgresql-contrib-16 \
        postgresql-16-postgis-3
    
    print_status "Configuring PostgreSQL..."
    systemctl enable postgresql
    systemctl start postgresql
    
    # Configure PostgreSQL settings
    PG_CONFIG="/etc/postgresql/16/main/postgresql.conf"
    sed -i "s/#max_connections = 100/max_connections = 200/" $PG_CONFIG
    sed -i "s/#shared_buffers = 128MB/shared_buffers = 256MB/" $PG_CONFIG
    sed -i "s/#wal_buffers = -1/wal_buffers = 16MB/" $PG_CONFIG
    
    systemctl restart postgresql
    
    print_success "PostgreSQL 16 installed and configured"
}

install_redis() {
    print_header "Installing Redis 7.x"
    
    print_status "Adding Redis official repository..."
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" > /etc/apt/sources.list.d/redis.list
    apt update -qq
    
    print_status "Installing Redis..."
    apt install -y -qq redis
    
    print_status "Configuring Redis..."
    REDIS_CONFIG="/etc/redis/redis.conf"
    sed -i "s/# maxmemory <bytes>/maxmemory 512mb/" $REDIS_CONFIG
    sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" $REDIS_CONFIG
    sed -i "s/save 900 1/save 300 10/" $REDIS_CONFIG
    
    systemctl enable redis-server
    systemctl start redis-server
    
    print_success "Redis 7.x installed and configured"
}

install_nginx() {
    print_header "Installing Nginx"
    
    print_status "Installing Nginx..."
    apt install -y -qq nginx
    
    print_status "Configuring Nginx..."
    systemctl enable nginx
    systemctl start nginx
    
    print_success "Nginx installed and configured"
}

setup_user() {
    print_header "Setting up Application User"
    
    print_status "Creating user and group..."
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d /opt/olt-manager -m $SERVICE_USER
        print_success "User $SERVICE_USER created"
    else
        print_info "User $SERVICE_USER already exists"
    fi
}

setup_database() {
    print_header "Setting up Database"
    
    print_status "Creating database and user..."
    sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\q
EOF
    
    print_success "Database $DB_NAME and user $DB_USER created"
    print_info "Database password: $DB_PASSWORD"
}

setup_application() {
    print_header "Setting up Application"
    
    print_status "Creating application directories..."
    mkdir -p $APP_DIR/{backend,frontend,logs,backups}
    chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
    
    print_status "Setting up backend environment..."
    sudo -u $SERVICE_USER python$PYTHON_VERSION -m venv $APP_DIR/backend/venv
    
    print_status "Creating environment file..."
    cat > $APP_DIR/backend/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security Configuration
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Application Configuration
APP_NAME=OLT Manager ZTE C320
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# SNMP Configuration
SNMP_COMMUNITY=public
SNMP_VERSION=2c
SNMP_TIMEOUT=5
SNMP_RETRIES=3

# Monitoring Configuration
MONITORING_INTERVAL=60
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_SMTP_HOST=localhost
ALERT_EMAIL_SMTP_PORT=587
EOF
    
    chown $SERVICE_USER:$SERVICE_USER $APP_DIR/backend/.env
    chmod 600 $APP_DIR/backend/.env
    
    print_success "Application directories and environment configured"
}

create_services() {
    print_header "Creating System Services"
    
    print_status "Creating backend service..."
    cat > /etc/systemd/system/olt-manager-backend.service << EOF
[Unit]
Description=OLT Manager Backend
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin
ExecStart=$APP_DIR/backend/venv/bin/python run.py
Restart=always
RestartSec=3
StandardOutput=append:$APP_DIR/logs/backend.log
StandardError=append:$APP_DIR/logs/backend.log

[Install]
WantedBy=multi-user.target
EOF
    
    print_status "Creating frontend service..."
    cat > /etc/systemd/system/olt-manager-frontend.service << EOF
[Unit]
Description=OLT Manager Frontend
After=network.target

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR/frontend
ExecStart=/usr/bin/npx serve -s build -l 3000
Restart=always
RestartSec=3
StandardOutput=append:$APP_DIR/logs/frontend.log
StandardError=append:$APP_DIR/logs/frontend.log

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    print_success "System services created"
}

configure_nginx() {
    print_header "Configuring Nginx"
    
    print_status "Creating Nginx configuration..."
    cat > /etc/nginx/sites-available/olt-manager << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/olt-manager /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    nginx -t
    systemctl reload nginx
    
    print_success "Nginx configured"
}

configure_firewall() {
    print_header "Configuring Firewall"
    
    print_status "Setting up UFW firewall..."
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    ufw --force enable
    
    print_success "Firewall configured"
}

main() {
    print_header "OLT Manager Installation Starting"
    
    check_root
    check_ubuntu
    update_system
    install_python
    install_nodejs
    install_postgresql
    install_redis
    install_nginx
    setup_user
    setup_database
    setup_application
    create_services
    configure_nginx
    configure_firewall
    
    print_header "Installation Complete!"
    print_success "OLT Manager has been installed successfully"
    print_info "Database: $DB_NAME"
    print_info "Database User: $DB_USER"
    print_info "Database Password: $DB_PASSWORD"
    print_info "Application Directory: $APP_DIR"
    print_info "Service User: $SERVICE_USER"
    print_warning "Please save the database password in a secure location"
    print_info "Access the application at: http://your-server-ip"
    
    print_header "Next Steps"
    echo "1. Deploy your application code to $APP_DIR"
    echo "2. Install backend dependencies: sudo -u $SERVICE_USER $APP_DIR/backend/venv/bin/pip install -r requirements.txt"
    echo "3. Run database migrations: sudo -u $SERVICE_USER $APP_DIR/backend/venv/bin/python init_db.py"
    echo "4. Build frontend: cd $APP_DIR/frontend && sudo -u $SERVICE_USER npm install && sudo -u $SERVICE_USER npm run build"
    echo "5. Start services: systemctl enable --now olt-manager-backend olt-manager-frontend"
}

# Run main function
main "$@"