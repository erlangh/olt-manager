#!/bin/bash

# OLT Manager ZTE C320 - Remote Installation Script for Ubuntu 24.04
# This script can be executed directly via SSH for remote installation

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/your-repo/olt-manager"  # Update with your actual repo
INSTALL_DIR="/opt/olt-manager"
TEMP_DIR="/tmp/olt-manager-install"
LOG_FILE="/tmp/olt-manager-install.log"

# Utility functions
print_header() {
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_status() {
    echo -e "${BLUE}🔄 $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Script ini harus dijalankan sebagai root atau dengan sudo"
        print_info "Gunakan: sudo $0"
        exit 1
    fi
}

# Check Ubuntu version
check_ubuntu() {
    if ! command -v lsb_release &> /dev/null; then
        print_error "lsb_release tidak ditemukan. Pastikan ini adalah sistem Ubuntu."
        exit 1
    fi
    
    local version=$(lsb_release -rs)
    local codename=$(lsb_release -cs)
    
    print_info "Terdeteksi: Ubuntu $version ($codename)"
    
    if [[ "$version" != "24.04" ]]; then
        print_warning "Script ini dioptimalkan untuk Ubuntu 24.04 LTS"
        print_warning "Versi Anda: $version"
        read -p "Lanjutkan instalasi? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Instalasi dibatalkan"
            exit 0
        fi
    else
        print_success "Ubuntu 24.04 LTS terdeteksi - Kompatibel!"
    fi
}

# Create temporary directory
setup_temp_dir() {
    print_status "Menyiapkan direktori temporary..."
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    print_success "Direktori temporary dibuat: $TEMP_DIR"
}

# Download installation files
download_files() {
    print_status "Mengunduh file instalasi..."
    
    # Method 1: Try git clone
    if command -v git &> /dev/null; then
        print_info "Mencoba clone repository..."
        if git clone "$REPO_URL" . 2>/dev/null; then
            print_success "Repository berhasil di-clone"
            return 0
        else
            print_warning "Git clone gagal, mencoba metode alternatif..."
        fi
    fi
    
    # Method 2: Try wget/curl for zip download
    print_info "Mencoba download archive..."
    if command -v wget &> /dev/null; then
        if wget -q "${REPO_URL}/archive/main.zip" -O main.zip; then
            unzip -q main.zip
            mv olt-manager-main/* .
            rm -rf olt-manager-main main.zip
            print_success "Archive berhasil diunduh dan diekstrak"
            return 0
        fi
    elif command -v curl &> /dev/null; then
        if curl -sL "${REPO_URL}/archive/main.zip" -o main.zip; then
            unzip -q main.zip
            mv olt-manager-main/* .
            rm -rf olt-manager-main main.zip
            print_success "Archive berhasil diunduh dan diekstrak"
            return 0
        fi
    fi
    
    # Method 3: Create minimal installation files
    print_warning "Tidak dapat mengunduh dari repository"
    print_info "Membuat file instalasi minimal..."
    create_minimal_install
}

# Create minimal installation files if download fails
create_minimal_install() {
    print_status "Membuat script instalasi minimal..."
    
    # Create basic install script
    cat > install.sh << 'EOF'
#!/bin/bash
# Minimal OLT Manager Installation Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}🔄 $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Update system
print_status "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
print_status "Installing dependencies..."
apt install -y curl wget git build-essential software-properties-common

# Install Python 3.12
print_status "Installing Python 3.12..."
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install Node.js 20
print_status "Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Install PostgreSQL
print_status "Installing PostgreSQL..."
apt install -y postgresql postgresql-contrib libpq-dev
systemctl start postgresql
systemctl enable postgresql

# Install Redis
print_status "Installing Redis..."
apt install -y redis-server
systemctl start redis-server
systemctl enable redis-server

# Install Nginx
print_status "Installing Nginx..."
apt install -y nginx
systemctl start nginx
systemctl enable nginx

# Setup database
print_status "Setting up database..."
sudo -u postgres psql << EOSQL
CREATE USER oltmanager WITH PASSWORD 'oltmanager123';
CREATE DATABASE oltmanager_db OWNER oltmanager;
GRANT ALL PRIVILEGES ON DATABASE oltmanager_db TO oltmanager;
ALTER USER oltmanager CREATEDB;
\q
EOSQL

# Create application user
print_status "Creating application user..."
useradd -r -s /bin/bash -d /opt/olt-manager oltmanager || true

# Create application directory
print_status "Creating application directory..."
mkdir -p /opt/olt-manager
chown oltmanager:oltmanager /opt/olt-manager

print_success "Basic system setup completed!"
print_status "You need to deploy your application files to /opt/olt-manager"
print_status "Then configure services and start the application"

EOF

    chmod +x install.sh
    print_success "Script instalasi minimal dibuat"
}

# Execute installation
execute_installation() {
    print_status "Menjalankan instalasi..."
    
    if [[ -f "install.sh" ]]; then
        chmod +x install.sh
        print_info "Menjalankan script instalasi utama..."
        ./install.sh 2>&1 | tee -a "$LOG_FILE"
    else
        print_error "File install.sh tidak ditemukan"
        exit 1
    fi
}

# Setup firewall for SSH access
setup_ssh_firewall() {
    print_status "Mengkonfigurasi firewall untuk akses SSH..."
    
    # Ensure SSH is allowed before enabling firewall
    ufw allow ssh
    ufw allow 22/tcp
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow backend API (optional)
    ufw allow 8000/tcp
    
    # Enable firewall
    ufw --force enable
    
    print_success "Firewall dikonfigurasi dengan akses SSH tetap terbuka"
}

# Verify installation
verify_installation() {
    print_header "Verifikasi Instalasi"
    
    local errors=0
    
    # Check services
    services=("postgresql" "redis-server" "nginx")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_success "$service service berjalan"
        else
            print_error "$service service tidak berjalan"
            ((errors++))
        fi
    done
    
    # Check ports
    ports=("80" "5432" "6379")
    for port in "${ports[@]}"; do
        if netstat -tlnp | grep -q ":$port "; then
            print_success "Port $port terbuka"
        else
            print_warning "Port $port tidak terbuka"
        fi
    done
    
    # Check database connection
    if sudo -u postgres psql -d oltmanager_db -c "SELECT 1;" &>/dev/null; then
        print_success "Koneksi database berhasil"
    else
        print_error "Koneksi database gagal"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        print_success "Semua komponen dasar berhasil diinstal"
    else
        print_warning "$errors komponen memiliki masalah"
    fi
}

# Cleanup
cleanup() {
    print_status "Membersihkan file temporary..."
    cd /
    rm -rf "$TEMP_DIR"
    print_success "Cleanup selesai"
}

# Main installation function
main() {
    print_header "OLT Manager ZTE C320 - Remote Installation"
    print_info "Instalasi remote untuk Ubuntu 24.04 via SSH"
    echo
    
    # Log start time
    echo "Installation started at: $(date)" > "$LOG_FILE"
    
    # Pre-installation checks
    check_root
    check_ubuntu
    
    # Setup and download
    setup_temp_dir
    download_files
    
    # Execute installation
    execute_installation
    
    # Post-installation setup
    setup_ssh_firewall
    verify_installation
    
    # Cleanup
    cleanup
    
    # Final message
    print_header "Instalasi Selesai!"
    echo
    echo -e "${GREEN}🎉 OLT Manager ZTE C320 berhasil diinstal!${NC}"
    echo
    echo -e "${CYAN}📋 Informasi Akses:${NC}"
    echo -e "   🌍 Web Interface: ${YELLOW}http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "   📚 API Documentation: ${YELLOW}http://$(hostname -I | awk '{print $1}')/api/docs${NC}"
    echo -e "   👤 Default Login: ${YELLOW}admin${NC} / ${YELLOW}admin123${NC}"
    echo
    echo -e "${CYAN}📁 Direktori Penting:${NC}"
    echo -e "   📂 Aplikasi: ${YELLOW}/opt/olt-manager${NC}"
    echo -e "   📄 Log Instalasi: ${YELLOW}$LOG_FILE${NC}"
    echo
    echo -e "${CYAN}🔧 Manajemen Layanan:${NC}"
    echo -e "   ▶️  Start: ${YELLOW}sudo systemctl start olt-manager-{backend,frontend}${NC}"
    echo -e "   ⏹️  Stop: ${YELLOW}sudo systemctl stop olt-manager-{backend,frontend}${NC}"
    echo -e "   📊 Status: ${YELLOW}sudo systemctl status olt-manager-{backend,frontend}${NC}"
    echo
    echo -e "${GREEN}🚀 Instalasi berhasil! Akses aplikasi melalui browser.${NC}"
    echo
}

# Error handling
trap 'print_error "Instalasi gagal pada baris $LINENO. Cek log: $LOG_FILE"; exit 1' ERR

# Run main function
main "$@"