# Auto Deploy Guide - OLT Manager ke Server Localhost

## 📋 Overview

Panduan ini menjelaskan cara melakukan auto deploy aplikasi OLT Manager ke server localhost `10.88.8.5` menggunakan script otomatis yang telah disediakan.

## 🎯 Target Deployment

- **Server Target**: `10.88.8.5` (Server Localhost)
- **Port Aplikasi**: `8000`
- **Domain**: `https://olt.remoteapps.my.id` (via Cloudflare Tunnel)
- **Service Name**: `olt-manager`
- **Install Directory**: `/opt/olt-manager`

## 📁 File Auto Deploy

| File | Deskripsi |
|------|-----------|
| `auto-deploy-localhost.sh` | Script utama auto deploy (Linux/WSL) |
| `quick-deploy.bat` | Script Windows untuk menjalankan auto deploy |
| `deployment/init_database.py` | Script inisialisasi database |
| `CLOUDFLARE_SETUP.md` | Dokumentasi setup Cloudflare tunnel |

## 🚀 Cara Menggunakan Auto Deploy

### Metode 1: Windows (Recommended)

1. **Buka Command Prompt atau PowerShell**
2. **Navigate ke folder project**:
   ```cmd
   cd C:\home\oltmgmt\Documents\trae_projects\olt_manager
   ```
3. **Jalankan script auto deploy**:
   ```cmd
   quick-deploy.bat
   ```

### Metode 2: WSL/Linux

1. **Buka WSL atau Linux terminal**
2. **Navigate ke folder project**:
   ```bash
   cd /mnt/c/home/oltmgmt/Documents/trae_projects/olt_manager
   ```
3. **Berikan permission execute**:
   ```bash
   chmod +x auto-deploy-localhost.sh
   ```
4. **Jalankan script**:
   ```bash
   ./auto-deploy-localhost.sh
   ```

### Metode 3: PowerShell dengan WSL

```powershell
# Navigate ke folder project
cd C:\home\oltmgmt\Documents\trae_projects\olt_manager

# Jalankan via WSL
wsl bash -c "chmod +x auto-deploy-localhost.sh && ./auto-deploy-localhost.sh"
```

## 🔧 Prasyarat

### 1. SSH Access ke Server Localhost
```bash
# Test koneksi SSH
ssh oltmgmt@10.88.8.5

# Jika belum ada SSH key, generate dulu:
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
ssh-copy-id oltmgmt@10.88.8.5
```

### 2. WSL (untuk Windows)
Jika menggunakan Windows, pastikan WSL sudah terinstall:
```powershell
# Install WSL (run as Administrator)
wsl --install

# Atau install Ubuntu specifically
wsl --install -d Ubuntu
```

### 3. Dependencies di Server Target
Server `10.88.8.5` harus memiliki:
- Ubuntu/Debian Linux
- sudo access untuk user `oltmgmt`
- Internet connection untuk download packages

## 📝 Apa yang Dilakukan Script Auto Deploy

### 1. **Pre-deployment Checks**
- ✅ Test koneksi SSH ke server target
- ✅ Backup aplikasi lama (jika ada)
- ✅ Stop service yang sedang berjalan

### 2. **Application Deployment**
- 📦 Upload package aplikasi
- 📁 Extract dan setup file aplikasi
- 🔧 Install system dependencies (Python, PostgreSQL)
- 🐍 Setup Python virtual environment
- 📚 Install Python packages

### 3. **Database Setup**
- 🗄️ Create PostgreSQL database `olt_manager`
- 👤 Create database user `oltmanager`
- 🔑 Set database permissions
- 📊 Initialize database dengan user admin

### 4. **Service Configuration**
- ⚙️ Create systemd service file
- 🔄 Enable auto-start service
- ▶️ Start aplikasi service
- 🔍 Verify deployment

### 5. **Post-deployment Verification**
- 🌐 Test HTTP response
- 📊 Check service status
- 🔌 Verify port binding
- 📋 Display access information

## 🎛️ Konfigurasi Script

Edit file `auto-deploy-localhost.sh` untuk menyesuaikan konfigurasi:

```bash
# Konfigurasi Server
LOCALHOST_SERVER="10.88.8.5"        # IP server target
LOCALHOST_USER="oltmgmt"             # Username SSH
LOCALHOST_PORT="22"                  # SSH port
APP_DIR="/opt/olt-manager"           # Directory aplikasi
SERVICE_NAME="olt-manager"           # Nama systemd service
```

## 📊 Monitoring dan Troubleshooting

### Check Service Status
```bash
# Via SSH
ssh oltmgmt@10.88.8.5 'sudo systemctl status olt-manager'

# Atau langsung di server
sudo systemctl status olt-manager
```

### View Service Logs
```bash
# Real-time logs
ssh oltmgmt@10.88.8.5 'sudo journalctl -u olt-manager -f'

# Last 50 lines
ssh oltmgmt@10.88.8.5 'sudo journalctl -u olt-manager -n 50'
```

### Check Port Status
```bash
ssh oltmgmt@10.88.8.5 'netstat -tlnp | grep 8000'
```

### Test HTTP Response
```bash
ssh oltmgmt@10.88.8.5 'curl -I http://localhost:8000'
```

## 🔄 Re-deployment

Untuk melakukan re-deployment (update aplikasi):

1. **Update kode aplikasi** di folder `deployment/`
2. **Jalankan ulang script auto deploy**:
   ```cmd
   quick-deploy.bat
   ```

Script akan otomatis:
- Backup aplikasi lama
- Stop service
- Deploy versi baru
- Restart service

## 🌐 Akses Aplikasi

Setelah deployment berhasil, aplikasi dapat diakses melalui:

### 1. Domain Cloudflare (Recommended)
- **URL**: `https://olt.remoteapps.my.id`
- **SSL**: ✅ Otomatis via Cloudflare
- **CDN**: ✅ Global performance

### 2. IP Localhost
- **URL**: `http://10.88.8.5:8000`
- **Direct**: ✅ Akses langsung ke server

### 3. IP Publik (Backup)
- **URL**: `http://41.216.186.253:8000`
- **Fallback**: ✅ Jika localhost tidak accessible

## 🔐 Login Credentials

```
Username: admin
Password: admin123
Role: Administrator
```

## 🛠️ Troubleshooting Common Issues

### 1. SSH Connection Failed
```bash
# Check SSH service
ssh -v oltmgmt@10.88.8.5

# Generate new SSH key if needed
ssh-keygen -t rsa -b 4096
ssh-copy-id oltmgmt@10.88.8.5
```

### 2. Permission Denied
```bash
# Ensure user has sudo access
ssh oltmgmt@10.88.8.5 'sudo -l'
```

### 3. Service Failed to Start
```bash
# Check detailed logs
ssh oltmgmt@10.88.8.5 'sudo journalctl -u olt-manager --no-pager -l'

# Check Python environment
ssh oltmgmt@10.88.8.5 'cd /opt/olt-manager && source venv/bin/activate && python --version'
```

### 4. Database Connection Error
```bash
# Test database connection
ssh oltmgmt@10.88.8.5 'sudo -u postgres psql -c "\l" | grep olt_manager'

# Reset database user password
ssh oltmgmt@10.88.8.5 'sudo -u postgres psql -c "ALTER USER oltmanager PASSWORD '\''oltmanager123'\'';"'
```

### 5. Port Already in Use
```bash
# Find process using port 8000
ssh oltmgmt@10.88.8.5 'sudo lsof -i :8000'

# Kill process if needed
ssh oltmgmt@10.88.8.5 'sudo pkill -f "python.*main_simple.py"'
```

## 📈 Performance Optimization

### 1. Enable Firewall (Optional)
```bash
ssh oltmgmt@10.88.8.5 '
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw status
'
```

### 2. Setup Log Rotation
```bash
ssh oltmgmt@10.88.8.5 '
sudo tee /etc/logrotate.d/olt-manager << EOF
/var/log/olt-manager/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
'
```

### 3. Database Backup Script
```bash
ssh oltmgmt@10.88.8.5 '
sudo tee /opt/olt-manager/backup-db.sh << EOF
#!/bin/bash
BACKUP_DIR="/opt/olt-manager-backup/db"
mkdir -p \$BACKUP_DIR
pg_dump -h localhost -U oltmanager -d olt_manager > \$BACKUP_DIR/olt_manager_\$(date +%Y%m%d_%H%M%S).sql
find \$BACKUP_DIR -name "*.sql" -mtime +7 -delete
EOF

sudo chmod +x /opt/olt-manager/backup-db.sh
'
```

## 🔄 Automated Deployment dengan Cron

Untuk setup auto-deployment berkala:

```bash
# Edit crontab
crontab -e

# Add line untuk deploy setiap hari jam 2 pagi
0 2 * * * /home/oltmgmt/Documents/trae_projects/olt_manager/auto-deploy-localhost.sh >> /var/log/auto-deploy.log 2>&1
```

## 📞 Support

Jika mengalami masalah:

1. **Check logs** dengan command di atas
2. **Verify network connectivity** ke server target
3. **Ensure SSH access** dan permissions
4. **Review error messages** dari script output

---

**Happy Deploying! 🚀**