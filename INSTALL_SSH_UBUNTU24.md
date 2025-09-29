# Instalasi OLT Manager ZTE C320 di Ubuntu 24.04 via SSH

## 📋 Panduan Instalasi Remote

Panduan ini menjelaskan cara menginstal sistem OLT Manager ZTE C320 di server Ubuntu 24.04 melalui koneksi SSH dari komputer lokal Anda.

## 🔧 Persyaratan

### Server Target (Ubuntu 24.04)
- **OS**: Ubuntu 24.04 LTS (fresh installation)
- **CPU**: 2 cores minimum (4 cores direkomendasikan)
- **RAM**: 4GB minimum (8GB direkomendasikan)
- **Storage**: 20GB ruang kosong minimum
- **Network**: Koneksi internet untuk download paket
- **SSH**: SSH server aktif dan dapat diakses

### Komputer Lokal
- **SSH Client**: OpenSSH, PuTTY, atau terminal dengan SSH
- **Akses**: Username dan password atau SSH key ke server
- **Network**: Koneksi ke server target

## 🚀 Langkah-langkah Instalasi

### 1. Persiapan Koneksi SSH

#### Dari Linux/macOS/Windows (WSL):
```bash
# Koneksi ke server Ubuntu 24.04
ssh username@ip-server-anda

# Contoh:
ssh oltmgmt@192.168.1.100
ssh root@your-server.com
```

#### Dari Windows (PuTTY):
1. Buka PuTTY
2. Masukkan IP server di "Host Name"
3. Port: 22 (default SSH)
4. Connection type: SSH
5. Klik "Open"
6. Login dengan username dan password

### 2. Persiapan Server

Setelah terhubung via SSH, jalankan perintah berikut:

```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Install tools yang diperlukan
sudo apt install -y curl wget git unzip

# Buat direktori kerja
mkdir -p ~/olt-manager
cd ~/olt-manager
```

### 3. Transfer File Instalasi

#### Opsi A: Download Langsung (Jika ada repository)
```bash
# Clone repository (jika tersedia)
git clone https://github.com/your-repo/olt-manager.git
cd olt-manager

# Atau download release
wget https://github.com/your-repo/olt-manager/archive/main.zip
unzip main.zip
cd olt-manager-main
```

#### Opsi B: Transfer dari Komputer Lokal

**Dari komputer lokal** (terminal baru):
```bash
# Menggunakan SCP untuk transfer file
scp -r /path/to/olt-manager username@ip-server:~/

# Contoh:
scp -r ./olt-manager oltmgmt@192.168.1.100:~/

# Transfer file install.sh saja
scp install.sh oltmgmt@192.168.1.100:~/olt-manager/

# Menggunakan rsync (lebih efisien)
rsync -avz --progress ./olt-manager/ username@ip-server:~/olt-manager/
```

#### Opsi C: Copy-Paste Script

Jika file kecil, Anda bisa copy-paste langsung:

```bash
# Buat file install.sh
nano install.sh

# Copy-paste isi script install.sh, lalu save (Ctrl+X, Y, Enter)

# Buat executable
chmod +x install.sh
```

### 4. Eksekusi Instalasi

```bash
# Masuk ke direktori
cd ~/olt-manager

# Jalankan script instalasi
sudo ./install.sh

# Atau jika ingin melihat output secara real-time
sudo ./install.sh | tee install.log
```

### 5. Monitoring Proses Instalasi

Selama instalasi berlangsung, Anda dapat:

```bash
# Monitor log instalasi (terminal baru)
ssh username@ip-server
tail -f ~/olt-manager/install.log

# Monitor penggunaan sistem
htop
# atau
top

# Monitor ruang disk
df -h

# Monitor proses
ps aux | grep -E "(python|node|postgres|redis)"
```

## 🔍 Verifikasi Instalasi

Setelah instalasi selesai:

```bash
# Cek status layanan
sudo systemctl status olt-manager-backend
sudo systemctl status olt-manager-frontend
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server

# Cek port yang terbuka
sudo netstat -tlnp | grep -E ':(80|443|3000|8000|5432|6379)'

# Test koneksi API
curl http://localhost:8000/health
curl http://localhost/api/health

# Cek log jika ada masalah
sudo journalctl -u olt-manager-backend -n 50
sudo journalctl -u olt-manager-frontend -n 50
```

## 🌐 Akses Aplikasi

Setelah instalasi berhasil:

- **Web Interface**: `http://ip-server-anda` atau `http://ip-server-anda:80`
- **API Documentation**: `http://ip-server-anda/api/docs`
- **Direct Backend**: `http://ip-server-anda:8000/docs`
- **Login Default**: `admin` / `admin123`

### Contoh Akses:
```
http://192.168.1.100          # Web Interface
http://192.168.1.100/api/docs # API Documentation
http://your-server.com        # Jika menggunakan domain
```

## 🔐 Konfigurasi Keamanan SSH

### 1. Konfigurasi Firewall

```bash
# Enable UFW (sudah dikonfigurasi oleh script instalasi)
sudo ufw status

# Jika perlu menambah aturan SSH
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Untuk akses dari IP tertentu saja
sudo ufw allow from 192.168.1.0/24 to any port 22
```

### 2. Konfigurasi SSH yang Aman

```bash
# Edit konfigurasi SSH
sudo nano /etc/ssh/sshd_config

# Pengaturan yang direkomendasikan:
# Port 2222                    # Ubah port default
# PermitRootLogin no           # Disable root login
# PasswordAuthentication yes   # Atau no jika pakai SSH key
# PubkeyAuthentication yes     # Enable SSH key
# MaxAuthTries 3               # Batasi percobaan login

# Restart SSH service
sudo systemctl restart sshd
```

### 3. Setup SSH Key (Opsional tapi Direkomendasikan)

**Di komputer lokal:**
```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# Copy public key ke server
ssh-copy-id username@ip-server

# Atau manual copy
cat ~/.ssh/id_rsa.pub | ssh username@ip-server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## 🔧 Manajemen Remote

### 1. Manajemen Layanan via SSH

```bash
# Start/Stop/Restart layanan
sudo systemctl start olt-manager-backend
sudo systemctl stop olt-manager-backend
sudo systemctl restart olt-manager-backend

# Enable/Disable auto-start
sudo systemctl enable olt-manager-backend
sudo systemctl disable olt-manager-backend

# Cek status semua layanan OLT Manager
sudo systemctl status olt-manager-*
```

### 2. Monitoring Log Real-time

```bash
# Monitor log backend
sudo journalctl -u olt-manager-backend -f

# Monitor log frontend
sudo journalctl -u olt-manager-frontend -f

# Monitor log sistem
sudo journalctl -f

# Monitor log Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. Backup dan Maintenance

```bash
# Backup database
sudo -u postgres pg_dump oltmanager_db > backup_$(date +%Y%m%d).sql

# Backup konfigurasi
tar -czf config_backup_$(date +%Y%m%d).tar.gz /opt/olt-manager/backend/.env /etc/nginx/sites-available/olt-manager

# Update aplikasi (jika ada update)
cd ~/olt-manager
git pull origin main  # Jika menggunakan git
sudo systemctl restart olt-manager-backend olt-manager-frontend
```

## 🐛 Troubleshooting SSH

### 1. Masalah Koneksi SSH

```bash
# Cek status SSH server
sudo systemctl status sshd

# Cek port SSH
sudo netstat -tlnp | grep :22

# Cek firewall
sudo ufw status
sudo iptables -L

# Test koneksi dari server lain
telnet ip-server 22
```

### 2. Masalah Permission

```bash
# Fix permission SSH
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Fix ownership
chown -R $USER:$USER ~/.ssh
```

### 3. Masalah Transfer File

```bash
# Cek ruang disk
df -h

# Cek permission direktori
ls -la ~/olt-manager

# Fix permission jika perlu
chmod -R 755 ~/olt-manager
chown -R $USER:$USER ~/olt-manager
```

## 📊 Monitoring Sistem Remote

### 1. Resource Monitoring

```bash
# CPU dan Memory
htop
# atau
top

# Disk usage
df -h
du -sh /opt/olt-manager

# Network
netstat -i
ss -tuln
```

### 2. Application Monitoring

```bash
# Cek proses aplikasi
ps aux | grep -E "(uvicorn|node|postgres|redis|nginx)"

# Cek koneksi database
sudo -u postgres psql -c "\l"
sudo -u postgres psql -d oltmanager_db -c "SELECT count(*) FROM information_schema.tables;"

# Test API endpoints
curl -s http://localhost:8000/health | jq
curl -s http://localhost:3000 | head -10
```

## 🔄 Update dan Maintenance Remote

### 1. Update Sistem

```bash
# Update Ubuntu packages
sudo apt update && sudo apt upgrade -y

# Update aplikasi (jika menggunakan git)
cd ~/olt-manager
git pull origin main

# Restart layanan setelah update
sudo systemctl restart olt-manager-backend olt-manager-frontend
```

### 2. Backup Otomatis

Buat script backup otomatis:

```bash
# Buat script backup
sudo nano /opt/backup-olt.sh

# Isi script:
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
sudo -u postgres pg_dump oltmanager_db > $BACKUP_DIR/db_$DATE.sql
gzip $BACKUP_DIR/db_$DATE.sql

# Config backup
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/olt-manager/backend/.env

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

# Make executable
sudo chmod +x /opt/backup-olt.sh

# Add to crontab untuk backup harian
sudo crontab -e
# Tambahkan: 0 2 * * * /opt/backup-olt.sh
```

## 📞 Support dan Bantuan

### Log Locations untuk Troubleshooting:

- **Backend**: `sudo journalctl -u olt-manager-backend`
- **Frontend**: `sudo journalctl -u olt-manager-frontend`
- **Nginx**: `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`
- **System**: `sudo journalctl -xe`

### Perintah Diagnostik Cepat:

```bash
# Health check lengkap
curl http://localhost:8000/health && echo "Backend OK"
curl http://localhost:3000 && echo "Frontend OK"
sudo systemctl is-active olt-manager-backend olt-manager-frontend nginx postgresql redis-server

# Resource check
free -h && df -h && uptime
```

---

**Catatan**: Pastikan Anda memiliki akses SSH yang stabil dan backup koneksi (seperti console access) jika terjadi masalah dengan konfigurasi SSH atau firewall.