#!/bin/bash

# Auto Deploy Script untuk OLT Manager ke Server Localhost 10.88.8.5
# Author: OLT Manager Team
# Version: 1.0

set -e  # Exit on any error

# Konfigurasi
LOCALHOST_SERVER="41.216.186.253"
LOCALHOST_USER="root"  # Sesuaikan dengan username server localhost
LOCALHOST_PORT="2225"
APP_DIR="/opt/olt-manager"
BACKUP_DIR="/opt/olt-manager-backup"
SERVICE_NAME="olt-manager"

# Warna untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fungsi logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fungsi untuk mengecek koneksi SSH
check_ssh_connection() {
    log_info "Mengecek koneksi SSH ke $LOCALHOST_SERVER..."
    if ssh -o ConnectTimeout=10 -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "echo 'SSH connection successful'" > /dev/null 2>&1; then
        log_success "Koneksi SSH berhasil"
        return 0
    else
        log_error "Koneksi SSH gagal ke $LOCALHOST_SERVER"
        log_info "Pastikan:"
        log_info "1. Server $LOCALHOST_SERVER dapat diakses"
        log_info "2. SSH service berjalan di server"
        log_info "3. Username dan SSH key sudah dikonfigurasi"
        return 1
    fi
}

# Fungsi untuk backup aplikasi lama
backup_old_app() {
    log_info "Membuat backup aplikasi lama..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        if [ -d '$APP_DIR' ]; then
            sudo mkdir -p $BACKUP_DIR
            sudo cp -r $APP_DIR $BACKUP_DIR/olt-manager-\$(date +%Y%m%d_%H%M%S)
            echo 'Backup created successfully'
        else
            echo 'No existing application to backup'
        fi
    "
}

# Fungsi untuk stop service
stop_service() {
    log_info "Menghentikan service $SERVICE_NAME..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        if sudo systemctl is-active --quiet $SERVICE_NAME; then
            sudo systemctl stop $SERVICE_NAME
            echo 'Service stopped'
        else
            echo 'Service not running'
        fi
    "
}

# Fungsi untuk upload aplikasi
upload_application() {
    log_info "Mengupload aplikasi ke server localhost..."
    
    # Buat package deployment
    if [ ! -f "olt-manager-production-v1.0.zip" ]; then
        log_info "Membuat package deployment..."
        zip -r olt-manager-production-v1.0.zip \
            deployment/main_simple.py \
            deployment/olt-manager-dashboard.html \
            deployment/requirements.txt \
            deployment/.env.production \
            deployment/init_database.py 2>/dev/null || true
    fi
    
    # Upload package
    scp -P $LOCALHOST_PORT olt-manager-production-v1.0.zip $LOCALHOST_USER@$LOCALHOST_SERVER:/tmp/
    log_success "Package berhasil diupload"
}

# Fungsi untuk extract dan setup aplikasi
setup_application() {
    log_info "Setup aplikasi di server localhost..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        # Extract package
        cd /tmp
        unzip -o olt-manager-production-v1.0.zip
        
        # Setup directory
        sudo mkdir -p $APP_DIR
        sudo cp deployment/main_simple.py $APP_DIR/
        sudo cp deployment/olt-manager-dashboard.html $APP_DIR/
        sudo cp deployment/requirements.txt $APP_DIR/
        sudo cp deployment/.env.production $APP_DIR/.env
        
        # Create init_database.py if not exists
        if [ ! -f '$APP_DIR/init_database.py' ]; then
            sudo tee $APP_DIR/init_database.py > /dev/null << 'EOF'
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
        
        # Set permissions
        sudo chown -R root:root $APP_DIR
        sudo chmod +x $APP_DIR/main_simple.py
        
        echo 'Application setup completed'
    "
}

# Fungsi untuk install dependencies
install_dependencies() {
    log_info "Install dependencies..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        cd $APP_DIR
        
        # Install system packages
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib
        
        # Setup virtual environment
        if [ ! -d 'venv' ]; then
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install --upgrade pip
        pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv bcrypt python-jose[cryptography] PyJWT passlib[bcrypt] python-multipart
        
        echo 'Dependencies installed successfully'
    "
}

# Fungsi untuk setup database
setup_database() {
    log_info "Setup database..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        # Setup PostgreSQL database
        sudo -u postgres psql -c \"SELECT 1 FROM pg_database WHERE datname = 'olt_manager'\" | grep -q 1 || sudo -u postgres createdb olt_manager
        sudo -u postgres psql -c \"SELECT 1 FROM pg_roles WHERE rolname = 'oltmanager'\" | grep -q 1 || sudo -u postgres psql -c \"CREATE USER oltmanager WITH PASSWORD 'oltmanager123';\"
        sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE olt_manager TO oltmanager;\"
        
        # Initialize database
        cd $APP_DIR
        source venv/bin/activate
        python init_database.py
        
        echo 'Database setup completed'
    "
}

# Fungsi untuk create systemd service
create_systemd_service() {
    log_info "Membuat systemd service..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=OLT Manager Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python main_simple.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        echo 'Systemd service created'
    "
}

# Fungsi untuk start service
start_service() {
    log_info "Memulai service $SERVICE_NAME..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        sudo systemctl start $SERVICE_NAME
        sleep 3
        
        if sudo systemctl is-active --quiet $SERVICE_NAME; then
            echo 'Service started successfully'
            sudo systemctl status $SERVICE_NAME --no-pager -l
        else
            echo 'Failed to start service'
            sudo journalctl -u $SERVICE_NAME --no-pager -l -n 20
            exit 1
        fi
    "
}

# Fungsi untuk verify deployment
verify_deployment() {
    log_info "Verifikasi deployment..."
    ssh -p $LOCALHOST_PORT $LOCALHOST_USER@$LOCALHOST_SERVER "
        # Check service status
        echo 'Service Status:'
        sudo systemctl status $SERVICE_NAME --no-pager
        
        # Check port
        echo -e '\nPort Status:'
        netstat -tlnp | grep 8000 || echo 'Port 8000 not found'
        
        # Test HTTP response
        echo -e '\nHTTP Test:'
        curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ || echo 'HTTP test failed'
        
        echo -e '\nDeployment verification completed'
    "
}

# Main deployment function
main() {
    log_info "=== Auto Deploy OLT Manager ke Server Localhost ==="
    log_info "Target Server: $LOCALHOST_SERVER"
    log_info "Deployment Directory: $APP_DIR"
    echo ""
    
    # Check SSH connection
    if ! check_ssh_connection; then
        exit 1
    fi
    
    # Backup old application
    backup_old_app
    
    # Stop service
    stop_service
    
    # Upload application
    upload_application
    
    # Setup application
    setup_application
    
    # Install dependencies
    install_dependencies
    
    # Setup database
    setup_database
    
    # Create systemd service
    create_systemd_service
    
    # Start service
    start_service
    
    # Verify deployment
    verify_deployment
    
    log_success "=== Deployment Selesai ==="
    log_info "Aplikasi dapat diakses di:"
    log_info "- Local: http://$LOCALHOST_SERVER:8000"
    log_info "- Domain: https://olt.remoteapps.my.id"
    log_info "- Credentials: admin / admin123"
    echo ""
    log_info "Untuk monitoring:"
    log_info "- Status service: ssh $LOCALHOST_USER@$LOCALHOST_SERVER 'sudo systemctl status $SERVICE_NAME'"
    log_info "- Log service: ssh $LOCALHOST_USER@$LOCALHOST_SERVER 'sudo journalctl -u $SERVICE_NAME -f'"
}

# Run main function
main "$@"