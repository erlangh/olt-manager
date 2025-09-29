# OLT Manager

Sistem manajemen OLT (Optical Line Terminal) berbasis web untuk monitoring dan konfigurasi perangkat jaringan fiber optik. Aplikasi ini dibangun dengan FastAPI (backend) dan React (frontend).

## 🚀 Fitur Utama

- **Dashboard Monitoring**: Real-time monitoring status OLT dan ONT
- **Manajemen OLT**: Konfigurasi dan monitoring perangkat OLT
- **Manajemen ONT**: Monitoring dan troubleshooting ONT
- **Sistem Alarm**: Notifikasi real-time untuk masalah jaringan
- **Laporan**: Generate laporan performa dan status jaringan
- **User Management**: Sistem autentikasi dan otorisasi
- **API Documentation**: Dokumentasi API lengkap dengan Swagger UI

## 🛠️ Teknologi yang Digunakan

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM untuk database
- **SQLite**: Database (default, dapat diganti PostgreSQL/MySQL)
- **JWT**: Autentikasi token
- **SNMP**: Komunikasi dengan perangkat OLT
- **WebSocket**: Real-time communication
- **Uvicorn**: ASGI server

### Frontend
- **React**: JavaScript library untuk UI
- **Material-UI**: Component library
- **Axios**: HTTP client
- **React Router**: Navigation
- **Context API**: State management

### Infrastructure
- **Nginx**: Reverse proxy dan web server
- **Systemd**: Service management
- **Ubuntu Server**: Operating system

## 📋 Persyaratan Sistem

### Minimum Requirements
- **OS**: Ubuntu Server 22.04 LTS atau 24.04 LTS
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB free space
- **CPU**: 2 cores minimum
- **Network**: Internet connection untuk download dependencies

### Software Dependencies
- **Python**: 3.11 atau lebih baru
- **Node.js**: 18.x atau lebih baru
- **Nginx**: 1.18 atau lebih baru
- **Git**: Untuk clone repository

### Port Requirements
- **Port 80**: HTTP (Nginx)
- **Port 443**: HTTPS (SSL/TLS) - optional
- **Port 8000**: Backend API (internal)
- **Port 22**: SSH access

## 🚀 Instalasi Cepat

### Instalasi Otomatis (Recommended)

```bash
# Clone repository
git clone https://github.com/erlangh/olt-manager.git
cd olt-manager

# Jalankan script instalasi
sudo ./install.sh
```

### Instalasi Manual

Lihat panduan lengkap di [INSTALL_UBUNTU.md](INSTALL_UBUNTU.md)

## 🔧 Konfigurasi

### Environment Variables

Copy file `.env.example` ke `.env` dan sesuaikan konfigurasi:

```bash
cp .env.example .env
nano .env
```

Konfigurasi penting yang perlu disesuaikan:
- `SECRET_KEY`: Ganti dengan key yang aman
- `DATABASE_URL`: URL database
- `CORS_ORIGINS`: Domain yang diizinkan akses API

### Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **PENTING**: Ganti password default setelah login pertama!

## 🏃‍♂️ Menjalankan Aplikasi

### Development Mode

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main_simple:app --host 0.0.0.0 --port 8000 --reload

# Frontend (terminal baru)
cd frontend
npm start
```

### Production Mode

```bash
# Start services
sudo systemctl start olt-manager-backend
sudo systemctl start nginx

# Check status
sudo systemctl status olt-manager-backend
sudo systemctl status nginx
```

## 📖 Penggunaan

### Akses Web Interface

- **Frontend**: `http://your-server-ip/`
- **API Documentation**: `http://your-server-ip/docs`

### API Endpoints

- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/olt/` - List semua OLT
- `GET /api/v1/ont/` - List semua ONT
- `GET /api/v1/monitoring/dashboard` - Dashboard data
- `GET /docs` - API documentation

## 🔍 Monitoring dan Troubleshooting

### Check Service Status

```bash
# Backend service
sudo systemctl status olt-manager-backend

# Nginx
sudo systemctl status nginx

# Check ports
sudo netstat -tlnp | grep -E ':(80|8000)'
```

### View Logs

```bash
# Backend logs
sudo journalctl -u olt-manager-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

1. **Service tidak start**: Check logs untuk error messages
2. **Port conflict**: Pastikan port 80 dan 8000 tidak digunakan aplikasi lain
3. **Permission denied**: Check file permissions di `/opt/olt-manager`
4. **Database error**: Recreate database dengan `python init_db.py`

## 🔄 Update Aplikasi

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

## 💾 Backup dan Restore

### Backup Database

```bash
# Manual backup
sudo cp /opt/olt-manager/backend/olt_manager.db /opt/backups/olt_manager_$(date +%Y%m%d_%H%M%S).db

# Automated backup (crontab)
0 2 * * * /usr/bin/cp /opt/olt-manager/backend/olt_manager.db /opt/backups/olt_manager_$(date +\%Y\%m\%d_\%H\%M\%S).db
```

### Restore Database

```bash
sudo systemctl stop olt-manager-backend
sudo cp /opt/backups/olt_manager_backup.db /opt/olt-manager/backend/olt_manager.db
sudo systemctl start olt-manager-backend
```

## 🔒 Keamanan

### Rekomendasi Keamanan

1. **Ganti default password** setelah instalasi
2. **Setup firewall** dengan ufw
3. **Enable HTTPS** dengan Let's Encrypt
4. **Regular security updates**
5. **Monitor access logs**
6. **Backup database** secara berkala

### Setup Firewall

```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
```

### Setup SSL/HTTPS

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com
```

## 🤝 Kontribusi

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Support

Jika mengalami masalah atau butuh bantuan:

1. Check [troubleshooting guide](INSTALL_UBUNTU.md#troubleshooting)
2. Review [common issues](#common-issues)
3. Check logs untuk error messages
4. Create issue di GitHub repository

## 🗺️ Roadmap

- [ ] Support untuk multiple OLT vendors
- [ ] Advanced reporting dan analytics
- [ ] Mobile responsive design
- [ ] Integration dengan sistem monitoring eksternal
- [ ] Automated backup ke cloud storage
- [ ] Multi-tenant support

## 📊 Project Structure

```
olt-manager/
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── auth/               # Authentication
│   ├── core/               # Core functionality
│   ├── database/           # Database configuration
│   ├── models/             # Database models
│   ├── routers/            # API routers
│   ├── services/           # Business logic
│   └── main_simple.py      # Main application
├── frontend/               # React frontend
│   ├── public/             # Static files
│   └── src/                # Source code
├── deployment/             # Deployment files
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── install.sh              # Installation script
├── INSTALL_UBUNTU.md       # Installation guide
└── README.md               # This file
```

---

**OLT Manager** - Solusi lengkap untuk manajemen jaringan fiber optik 🌐
