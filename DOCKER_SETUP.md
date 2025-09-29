# OLT Manager ZTE C320 - Docker Setup Guide

## 📋 Overview

This guide provides instructions for deploying the OLT Manager ZTE C320 system using Docker and Docker Compose. This method provides an isolated, reproducible environment that works consistently across different systems.

## 🔧 Prerequisites

### System Requirements
- **OS**: Ubuntu 24.04 LTS, CentOS 8+, or any Docker-compatible Linux distribution
- **CPU**: 2 cores minimum (4 cores recommended)
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 20GB free space minimum
- **Network**: Internet connection for image downloads

### Required Software
- Docker Engine 24.0+
- Docker Compose 2.0+

## 🚀 Quick Start

### 1. Install Docker and Docker Compose

#### Ubuntu 24.04
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 2. Deploy OLT Manager

```bash
# Clone or download the project
git clone <your-repository-url>
cd olt-manager

# Or if you have the files locally
cd /path/to/olt-manager

# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

## 📁 Project Structure

```
olt-manager/
├── docker-compose.yml          # Main Docker Compose configuration
├── backend/
│   ├── Dockerfile             # Backend container definition
│   ├── requirements.txt       # Python dependencies
│   └── ...                    # Backend source code
├── frontend/
│   ├── Dockerfile             # Frontend container definition
│   ├── package.json           # Node.js dependencies
│   └── ...                    # Frontend source code
├── nginx/
│   ├── nginx.conf             # Nginx configuration
│   └── conf.d/                # Additional Nginx configs
├── monitoring/
│   ├── Dockerfile             # Monitoring service
│   └── ...                    # Monitoring scripts
└── database/
    └── init/                  # Database initialization scripts
```

## 🐳 Docker Services

The Docker Compose setup includes the following services:

### Core Services
- **postgres**: PostgreSQL 16 database
- **redis**: Redis 7 cache and message broker
- **backend**: FastAPI application server
- **frontend**: React web application
- **nginx**: Reverse proxy and web server

### Optional Services
- **monitor**: System monitoring and SNMP polling

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root to customize settings:

```bash
# Database Configuration
POSTGRES_DB=oltmanager_db
POSTGRES_USER=oltmanager
POSTGRES_PASSWORD=oltmanager123

# Redis Configuration
REDIS_PASSWORD=oltmanager123

# Backend Configuration
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# Monitoring Configuration
SNMP_COMMUNITY=public
MONITORING_INTERVAL=60
```

### Port Configuration

Default ports used by the services:

- **80**: Nginx (HTTP)
- **443**: Nginx (HTTPS)
- **3000**: Frontend (React)
- **8000**: Backend (FastAPI)
- **5432**: PostgreSQL
- **6379**: Redis

To change ports, modify the `docker-compose.yml` file:

```yaml
services:
  nginx:
    ports:
      - "8080:80"  # Change HTTP port to 8080
      - "8443:443" # Change HTTPS port to 8443
```

## 🔧 Management Commands

### Basic Operations

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart services
docker compose restart

# View service status
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f backend
docker compose logs -f frontend
```

### Service Management

```bash
# Start specific service
docker compose up -d backend

# Stop specific service
docker compose stop backend

# Restart specific service
docker compose restart backend

# Scale services (if needed)
docker compose up -d --scale backend=2
```

### Database Operations

```bash
# Access PostgreSQL
docker compose exec postgres psql -U oltmanager -d oltmanager_db

# Backup database
docker compose exec postgres pg_dump -U oltmanager oltmanager_db > backup.sql

# Restore database
docker compose exec -T postgres psql -U oltmanager -d oltmanager_db < backup.sql

# View database logs
docker compose logs postgres
```

### Redis Operations

```bash
# Access Redis CLI
docker compose exec redis redis-cli -a oltmanager123

# Monitor Redis
docker compose exec redis redis-cli -a oltmanager123 monitor

# View Redis logs
docker compose logs redis
```

## 🔍 Monitoring and Troubleshooting

### Health Checks

All services include health checks. Check service health:

```bash
# View service health status
docker compose ps

# Check specific service health
docker inspect olt-manager-backend --format='{{.State.Health.Status}}'
```

### Log Analysis

```bash
# View all logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View logs for specific service
docker compose logs backend

# View last 100 lines
docker compose logs --tail=100 backend

# Filter logs by timestamp
docker compose logs --since="2024-01-01T00:00:00" backend
```

### Performance Monitoring

```bash
# View resource usage
docker stats

# View detailed container information
docker compose exec backend ps aux
docker compose exec backend df -h
docker compose exec backend free -m
```

## 🔐 Security Considerations

### Production Deployment

1. **Change Default Passwords**:
   ```bash
   # Update .env file with strong passwords
   POSTGRES_PASSWORD=your-strong-password
   REDIS_PASSWORD=your-strong-redis-password
   SECRET_KEY=your-32-character-secret-key
   ```

2. **Enable HTTPS**:
   ```bash
   # Add SSL certificates to nginx/ssl/
   # Update nginx configuration for HTTPS
   ```

3. **Network Security**:
   ```bash
   # Limit exposed ports
   # Use Docker networks for internal communication
   # Configure firewall rules
   ```

4. **Regular Updates**:
   ```bash
   # Update base images regularly
   docker compose pull
   docker compose up -d
   ```

## 📊 Backup and Recovery

### Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker compose exec -T postgres pg_dump -U oltmanager oltmanager_db > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql.gz"
EOF

chmod +x backup.sh
```

### Volume Backup

```bash
# Backup Docker volumes
docker run --rm -v olt-manager_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .
docker run --rm -v olt-manager_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_data_backup.tar.gz -C /data .
```

### Recovery

```bash
# Restore database
docker compose exec -T postgres psql -U oltmanager -d oltmanager_db < backup.sql

# Restore volumes
docker run --rm -v olt-manager_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_data_backup.tar.gz -C /data
```

## 🚀 Production Deployment

### Docker Compose Override

Create `docker-compose.prod.yml` for production settings:

```yaml
version: '3.8'

services:
  backend:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    restart: always
    
  frontend:
    environment:
      - NODE_ENV=production
    restart: always
    
  nginx:
    volumes:
      - ./nginx/prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    restart: always
```

Deploy with production settings:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Systemd Service

Create a systemd service for automatic startup:

```bash
sudo tee /etc/systemd/system/olt-manager.service > /dev/null << EOF
[Unit]
Description=OLT Manager Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/olt-manager
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable olt-manager
sudo systemctl start olt-manager
```

## 🌐 Access Information

After successful deployment:

- **Web Interface**: `http://localhost` or `http://your-server-ip`
- **API Documentation**: `http://localhost/api/docs`
- **Direct Backend**: `http://localhost:8000/docs`
- **Default Login**: `admin` / `admin123`

## 📞 Support and Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check what's using ports
   sudo netstat -tlnp | grep -E ':(80|443|3000|8000|5432|6379)'
   
   # Change ports in docker-compose.yml if needed
   ```

2. **Permission Issues**:
   ```bash
   # Fix Docker permissions
   sudo chown -R $USER:$USER .
   sudo chmod -R 755 .
   ```

3. **Memory Issues**:
   ```bash
   # Check available memory
   free -h
   
   # Increase swap if needed
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

4. **Network Issues**:
   ```bash
   # Check Docker networks
   docker network ls
   docker network inspect olt-manager_olt-network
   ```

### Getting Help

1. Check service logs: `docker compose logs [service-name]`
2. Verify service health: `docker compose ps`
3. Check resource usage: `docker stats`
4. Review configuration files
5. Ensure all required ports are available

---

**Note**: This Docker setup is designed for both development and production use. Adjust security settings and configurations according to your specific requirements.