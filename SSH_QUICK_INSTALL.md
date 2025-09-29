# 🚀 OLT Manager ZTE C320 - Instalasi Cepat via SSH

## 📋 Instalasi One-Liner

### Metode 1: Download dan Jalankan (Recommended)
```bash
# Login ke server Ubuntu 24.04 via SSH
ssh username@server-ip

# Jalankan instalasi otomatis
curl -fsSL https://raw.githubusercontent.com/your-repo/olt-manager/main/install-remote.sh | sudo bash
```

### Metode 2: Download Manual
```bash
# Download script instalasi
wget https://raw.githubusercontent.com/your-repo/olt-manager/main/install-remote.sh

# Berikan permission execute
chmod +x install-remote.sh

# Jalankan instalasi
sudo ./install-remote.sh
```

### Metode 3: Copy-Paste Script
Jika tidak bisa download, copy script dari file `install-remote.sh` dan paste ke server:

```bash
# Buat file script
sudo nano install-remote.sh

# Paste script content, save (Ctrl+X, Y, Enter)

# Berikan permission dan jalankan
chmod +x install-remote.sh
sudo ./install-remote.sh
```

## 🔧 Persiapan Server SSH

### 1. Koneksi SSH
```bash
# Koneksi SSH basic
ssh username@server-ip

# Koneksi SSH dengan port custom
ssh -p 2222 username@server-ip

# Koneksi SSH dengan key
ssh -i ~/.ssh/private_key username@server-ip
```

### 2. Update Sistem (Opsional)
```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Install Curl/Wget (jika belum ada)
```bash
sudo apt install -y curl wget
```

## 📊 Monitoring Instalasi

### Real-time Log Monitoring
```bash
# Monitor log instalasi (buka terminal baru)
tail -f /tmp/olt-manager-install.log
```

### Check Status Layanan
```bash
# Status semua layanan
sudo systemctl status postgresql redis-server nginx

# Status aplikasi (setelah instalasi selesai)
sudo systemctl status olt-manager-backend olt-manager-frontend
```

## 🌐 Akses Setelah Instalasi

### Web Interface
- **URL**: `http://SERVER-IP`
- **Login**: `admin` / `admin123`

### API Documentation
- **URL**: `http://SERVER-IP/api/docs`

### SSH Tunnel (jika diperlukan)
```bash
# Forward port untuk akses lokal
ssh -L 8080:localhost:80 username@server-ip

# Akses via browser lokal: http://localhost:8080
```

## 🔒 Keamanan SSH

### 1. Konfigurasi SSH Key (Recommended)
```bash
# Di komputer lokal, generate SSH key
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# Copy public key ke server
ssh-copy-id username@server-ip

# Test koneksi tanpa password
ssh username@server-ip
```

### 2. Hardening SSH (Opsional)
```bash
# Edit konfigurasi SSH
sudo nano /etc/ssh/sshd_config

# Tambahkan/ubah:
# Port 2222                    # Ganti port default
# PermitRootLogin no           # Disable root login
# PasswordAuthentication no    # Hanya SSH key
# AllowUsers username          # Hanya user tertentu

# Restart SSH service
sudo systemctl restart ssh
```

### 3. Firewall Configuration
```bash
# Allow SSH port baru (jika diubah)
sudo ufw allow 2222/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

## 🛠️ Troubleshooting

### 1. Koneksi SSH Gagal
```bash
# Check SSH service
sudo systemctl status ssh

# Check port yang digunakan
sudo netstat -tlnp | grep :22

# Reset SSH config (hati-hati!)
sudo systemctl restart ssh
```

### 2. Instalasi Gagal
```bash
# Check log error
cat /tmp/olt-manager-install.log

# Check disk space
df -h

# Check memory
free -h

# Manual cleanup
sudo rm -rf /tmp/olt-manager-install
```

### 3. Service Tidak Jalan
```bash
# Restart semua service
sudo systemctl restart postgresql redis-server nginx

# Check error logs
sudo journalctl -u postgresql -f
sudo journalctl -u redis-server -f
sudo journalctl -u nginx -f
```

## 📱 Remote Management

### 1. Screen/Tmux untuk Session Persistent
```bash
# Install screen
sudo apt install -y screen

# Mulai session
screen -S olt-install

# Jalankan instalasi
sudo ./install-remote.sh

# Detach: Ctrl+A, D
# Reattach: screen -r olt-install
```

### 2. Monitoring Resource
```bash
# Monitor CPU/Memory
htop

# Monitor disk usage
watch df -h

# Monitor network
sudo netstat -tlnp
```

### 3. Log Management
```bash
# View application logs
sudo tail -f /opt/olt-manager/logs/app.log

# View system logs
sudo journalctl -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🔄 Update dan Maintenance

### 1. Update Aplikasi
```bash
# Masuk ke direktori aplikasi
cd /opt/olt-manager

# Pull update (jika menggunakan git)
sudo -u oltmanager git pull

# Restart services
sudo systemctl restart olt-manager-backend olt-manager-frontend
```

### 2. Backup Database
```bash
# Backup PostgreSQL
sudo -u postgres pg_dump oltmanager_db > backup_$(date +%Y%m%d).sql

# Restore backup
sudo -u postgres psql oltmanager_db < backup_20241201.sql
```

### 3. System Maintenance
```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Clean package cache
sudo apt autoremove -y
sudo apt autoclean

# Check disk usage
sudo du -sh /opt/olt-manager/*
```

## 📞 Support

Jika mengalami masalah:

1. **Check log instalasi**: `/tmp/olt-manager-install.log`
2. **Check system logs**: `sudo journalctl -xe`
3. **Check service status**: `sudo systemctl status service-name`
4. **Restart services**: `sudo systemctl restart service-name`

---

**🎯 Tips**: Gunakan `screen` atau `tmux` untuk instalasi yang memakan waktu lama agar tidak terputus jika koneksi SSH terputus.

**⚠️ Peringatan**: Pastikan backup data penting sebelum instalasi dan gunakan user non-root untuk keamanan yang lebih baik.