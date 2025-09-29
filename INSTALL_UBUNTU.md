# OLT Manager - Panduan Instalasi Ubuntu Server

Panduan lengkap untuk menginstal OLT Manager di Ubuntu Server 22.04/24.04.

## Persyaratan Sistem

### Minimum Requirements
- Ubuntu Server 22.04 LTS atau 24.04 LTS
- RAM: 2GB minimum, 4GB recommended
- Storage: 10GB free space
- CPU: 2 cores minimum
- Network: Internet connection untuk download dependencies

### Port Requirements
- Port 80: HTTP (Nginx)
- Port 443: HTTPS (SSL/TLS)
- Port 8000: Backend API (internal)
- Port 22: SSH access

## Instalasi Otomatis (Recommended)

### 1. Download dan Jalankan Script Instalasi

```bash
# Clone repository
git clone https://github.com/[your-username]/olt-manager.git
cd olt-manager

# Berikan permission execute
chmod +x install.sh

# Jalankan instalasi
sudo ./install.sh
```

### 2. Konfigurasi Environment

```bash
# Edit file environment
sudo nano /opt/olt-manager/.env

# Sesuaikan konfigurasi berikut:
DATABASE_URL=sqlite:///./olt_manager.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Start Services

```bash
# Enable dan start services
sudo systemctl enable olt-manager-backend
sudo systemctl start olt-manager-backend

# Check status
sudo systemctl status olt-manager-backend
```

## Instalasi Manual

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Dependencies

```bash
# Install Python 3.11+
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Nginx
sudo apt install nginx -y

# Install Git
sudo apt install git -y
```

### 3. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/[your-username]/olt-manager.git
sudo chown -R $USER:$USER /opt/olt-manager
cd /opt/olt-manager
```

### 4. Setup Backend

```bash
# Masuk ke direktori backend
cd /opt/olt-manager/backend

# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Setup database
python init_db.py

# Test backend
python -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
```

### 5. Setup Frontend

```bash
# Masuk ke direktori frontend
cd /opt/olt-manager/frontend

# Install Node.js dependencies
npm install

# Build production
npm run build
```

### 6. Configure Nginx

```bash
# Backup default config
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# Create OLT Manager config
sudo tee /etc/nginx/sites-available/olt-manager << 'EOF'
server {
    listen 80;
    server_name localhost;

    # Frontend
    location / {
        root /opt/olt-manager/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/olt-manager /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test dan restart nginx
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/olt-manager-backend.service << 'EOF'
[Unit]
Description=OLT Manager Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/olt-manager/backend
Environment=PATH=/opt/olt-manager/backend/venv/bin
ExecStart=/opt/olt-manager/backend/venv/bin/uvicorn main_simple:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd dan start service
sudo systemctl daemon-reload
sudo systemctl enable olt-manager-backend
sudo systemctl start olt-manager-backend
```

## Verifikasi Instalasi

### 1. Check Services Status

```bash
# Check backend service
sudo systemctl status olt-manager-backend

# Check nginx
sudo systemctl status nginx

# Check ports
sudo netstat -tlnp | grep -E ':(80|8000)'
```

### 2. Test API

```bash
# Test health endpoint
curl http://localhost/docs

# Test login
curl -X POST "http://localhost/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
```

### 3. Access Web Interface

Buka browser dan akses:
- **Frontend**: `http://your-server-ip/`
- **API Docs**: `http://your-server-ip/docs`

## Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **PENTING**: Ganti password default setelah login pertama!

## Troubleshooting

### Backend Service Tidak Start

```bash
# Check logs
sudo journalctl -u olt-manager-backend -f

# Check file permissions
sudo chown -R root:root /opt/olt-manager
sudo chmod +x /opt/olt-manager/backend/venv/bin/uvicorn
```

### Nginx Error

```bash
# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### Database Issues

```bash
# Recreate database
cd /opt/olt-manager/backend
source venv/bin/activate
python init_db.py
```

### Port Already in Use

```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill process if needed
sudo kill -9 <PID>
```

## SSL/HTTPS Setup (Optional)

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Maintenance

### Update Application

```bash
cd /opt/olt-manager
sudo git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart olt-manager-backend

# Update frontend
cd ../frontend
npm install
npm run build
sudo systemctl restart nginx
```

### Backup Database

```bash
# Backup
sudo cp /opt/olt-manager/backend/olt_manager.db /opt/backups/olt_manager_$(date +%Y%m%d_%H%M%S).db

# Restore
sudo cp /opt/backups/olt_manager_backup.db /opt/olt-manager/backend/olt_manager.db
sudo systemctl restart olt-manager-backend
```

### Monitor Logs

```bash
# Backend logs
sudo journalctl -u olt-manager-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## Support

Jika mengalami masalah:

1. Check logs untuk error messages
2. Pastikan semua services running
3. Verify port tidak conflict
4. Check file permissions
5. Buat issue di GitHub repository

## Security Notes

- Ganti default password
- Setup firewall (ufw)
- Regular security updates
- Monitor access logs
- Backup database secara berkala