# Setup Cloudflare Tunnel untuk OLT Manager

## Informasi Server
- **IP Publik**: `41.216.186.253` (Server Production)
- **IP Localhost**: `10.88.8.5` (Server dengan Cloudflare Tunnel)
- **Domain**: `olt.remoteapps.my.id`
- **Port Aplikasi**: `8000`

## Status Saat Ini
✅ **Domain Cloudflare**: Aktif dan dapat diakses
✅ **Tunnel Cloudflare**: Terkonfigurasi
❌ **Aplikasi di Localhost**: Belum berjalan di `10.88.8.5:8000`

## Langkah Setup Aplikasi di Server Localhost

### 1. Copy Aplikasi ke Server Localhost (10.88.8.5)

```bash
# Copy deployment package ke server localhost
scp -P 22 olt-manager-production-v1.0.zip user@10.88.8.5:/tmp/

# SSH ke server localhost
ssh user@10.88.8.5

# Extract dan setup aplikasi
cd /tmp
unzip olt-manager-production-v1.0.zip
sudo mkdir -p /opt/olt-manager
sudo cp main_simple.py olt-manager-dashboard.html requirements.txt .env.production /opt/olt-manager/
cd /opt/olt-manager
sudo cp .env.production .env
```

### 2. Install Dependencies

```bash
# Install Python dan dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv bcrypt python-jose[cryptography] PyJWT passlib[bcrypt] python-multipart
```

### 3. Setup Database

```bash
# Setup PostgreSQL
sudo -u postgres createdb olt_manager
sudo -u postgres psql -c "CREATE USER oltmanager WITH PASSWORD 'oltmanager123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE olt_manager TO oltmanager;"

# Initialize database dengan user default
python init_database.py
```

### 4. Jalankan Aplikasi

```bash
# Jalankan aplikasi di port 8000
cd /opt/olt-manager
source venv/bin/activate
python main_simple.py
```

### 5. Setup Systemd Service (Opsional)

```bash
# Buat service file
sudo tee /etc/systemd/system/olt-manager.service << EOF
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

[Install]
WantedBy=multi-user.target
EOF

# Enable dan start service
sudo systemctl daemon-reload
sudo systemctl enable olt-manager
sudo systemctl start olt-manager
sudo systemctl status olt-manager
```

## Konfigurasi Cloudflare Tunnel

Pastikan Cloudflare tunnel dikonfigurasi untuk forward traffic dari domain ke localhost:

```yaml
# cloudflared config.yml
tunnel: your-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  - hostname: olt.remoteapps.my.id
    service: http://localhost:8000
  - service: http_status:404
```

## Akses Aplikasi

Setelah setup selesai, aplikasi dapat diakses melalui:

### 1. Domain Cloudflare (Recommended)
- **URL**: `https://olt.remoteapps.my.id`
- **Username**: `admin`
- **Password**: `admin123`

### 2. IP Publik (Backup)
- **URL**: `http://41.216.186.253:8000`
- **Username**: `admin`
- **Password**: `admin123`

### 3. Localhost (Development)
- **URL**: `http://10.88.8.5:8000`
- **Username**: `admin`
- **Password**: `admin123`

## Troubleshooting

### Domain tidak dapat diakses
1. Cek status Cloudflare tunnel: `cloudflared tunnel list`
2. Cek konfigurasi tunnel: `cloudflared tunnel route dns`
3. Pastikan aplikasi berjalan di `localhost:8000`

### Aplikasi tidak berjalan
1. Cek status service: `sudo systemctl status olt-manager`
2. Cek log aplikasi: `sudo journalctl -u olt-manager -f`
3. Cek port: `netstat -tlnp | grep 8000`

### Database error
1. Cek status PostgreSQL: `sudo systemctl status postgresql`
2. Test koneksi database: `psql -h localhost -U oltmanager -d olt_manager`
3. Reset password user: `sudo -u postgres psql -c "ALTER USER oltmanager PASSWORD 'oltmanager123';"`

## Keamanan

1. **Firewall**: Pastikan hanya port yang diperlukan terbuka
2. **SSL**: Cloudflare menyediakan SSL otomatis
3. **Database**: Gunakan password yang kuat untuk production
4. **Backup**: Setup backup rutin untuk database dan konfigurasi