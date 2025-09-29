# 🚀 OLT Manager Deployment Instructions

## Issue Resolution
The error `cp: cannot stat 'deployment/*': No such file or directory` occurred because the deployment package extraction didn't create the expected directory structure. I've created a **fixed setup script** to resolve this.

## ✅ Files Successfully Transferred to Server

1. **Deployment Package**: `/tmp/olt-manager-deploy.zip` ✅
2. **Fixed Setup Script**: `/tmp/setup-fixed.sh` ✅

## 🔧 Next Steps - Execute on Server

### 1. Connect to Server
```bash
ssh -p 2225 root@41.216.186.253
```

### 2. Run the Fixed Setup Script
```bash
# Make script executable
chmod +x /tmp/setup-fixed.sh

# Execute the fixed setup script
bash /tmp/setup-fixed.sh
```

## 🔍 What the Fixed Script Does

The updated script includes:

1. **Better Error Handling** - Checks for both directory and direct file extraction
2. **Debug Information** - Shows extracted files for troubleshooting
3. **Fallback Logic** - Handles different zip extraction patterns
4. **File Verification** - Lists files after copying to confirm success
5. **Automatic Fallback** - Creates `init_database.py` if missing

## 📋 Expected Output

The script will show:
```
=== OLT Manager Server Setup (Fixed) ===
Starting deployment process...
Updating system packages...
Installing dependencies...
Starting PostgreSQL service...
Setting up database...
Creating application directory...
Extracting deployment package...
Extracted files:
[file listing]
Copying from deployment directory...
Files copied successfully
Files in /opt/olt-manager:
[file listing]
Setting up Python environment...
Initializing database...
Creating systemd service...
Starting OLT Manager service...
Verifying deployment...
✅ Deployment successful! Application is running.
```

## 🌐 Access After Deployment

- **Direct Server**: `http://41.216.186.253:8000`
- **Cloudflare Domain**: `https://olt.remoteapps.my.id`

### 🔐 Login Credentials
- **Username**: `admin`
- **Password**: `admin123`

## 🛠️ Troubleshooting Commands

If you encounter issues:

```bash
# Check service status
systemctl status olt-manager

# View logs
journalctl -u olt-manager -f

# Check files in app directory
ls -la /opt/olt-manager/

# Test HTTP response
curl -I http://localhost:8000

# Restart service if needed
systemctl restart olt-manager
```

## 🔄 Alternative Manual Steps

If the script still has issues, you can manually extract and copy files:

```bash
# On server
cd /tmp
unzip -o olt-manager-deploy.zip
ls -la  # Check what was extracted

# Create app directory
mkdir -p /opt/olt-manager

# Copy files (adjust paths based on extraction)
cp main_simple.py /opt/olt-manager/ 2>/dev/null || cp deployment/main_simple.py /opt/olt-manager/
cp olt-manager-dashboard.html /opt/olt-manager/ 2>/dev/null || cp deployment/olt-manager-dashboard.html /opt/olt-manager/
cp requirements.txt /opt/olt-manager/ 2>/dev/null || cp deployment/requirements.txt /opt/olt-manager/
cp .env.production /opt/olt-manager/.env 2>/dev/null || cp deployment/.env.production /opt/olt-manager/.env
cp init_database.py /opt/olt-manager/ 2>/dev/null || cp deployment/init_database.py /opt/olt-manager/

# Continue with the rest of the setup
cd /opt/olt-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_database.py
```

The fixed script should resolve the directory issue and complete the deployment successfully! 🎉