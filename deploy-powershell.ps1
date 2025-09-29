# Auto Deploy Script untuk OLT Manager ke Server Localhost 10.88.8.5
# PowerShell Native Version (Tanpa WSL)
# Author: OLT Manager Team
# Version: 1.0

param(
    [string]$ServerIP = "41.216.186.253",
    [string]$Username = "root",
    [int]$Port = 2225,
    [string]$AppDir = "/opt/olt-manager",
    [string]$ServiceName = "olt-manager"
)

# Konfigurasi warna
$Colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = $Colors[$Type]
    Write-Host "[$timestamp] [$Type] $Message" -ForegroundColor $color
}

function Test-SSHConnection {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port
    )
    
    Write-Log "Testing SSH connection to $Server..." "Info"
    
    try {
        # Test SSH connection using plink (PuTTY) or ssh if available
        $testResult = ssh -o ConnectTimeout=10 -o BatchMode=yes -p $Port "$User@$Server" "echo 'SSH OK'" 2>$null
        
        if ($testResult -eq "SSH OK") {
            Write-Log "SSH connection successful" "Success"
            return $true
        } else {
            Write-Log "SSH connection failed" "Error"
            return $false
        }
    } catch {
        Write-Log "SSH connection error: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Invoke-SSHCommand {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$Command
    )
    
    try {
        $result = ssh -p $Port "$User@$Server" $Command 2>&1
        return @{
            Success = $LASTEXITCODE -eq 0
            Output = $result
            ExitCode = $LASTEXITCODE
        }
    } catch {
        return @{
            Success = $false
            Output = $_.Exception.Message
            ExitCode = -1
        }
    }
}

function Copy-FileToServer {
    param(
        [string]$LocalPath,
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$RemotePath
    )
    
    Write-Log "Copying $LocalPath to ${Server}:$RemotePath..." "Info"
    
    try {
        scp -P $Port $LocalPath "$User@$Server`:$RemotePath"
        if ($LASTEXITCODE -eq 0) {
            Write-Log "File copied successfully" "Success"
            return $true
        } else {
            Write-Log "File copy failed" "Error"
            return $false
        }
    } catch {
        Write-Log "File copy error: $($_.Exception.Message)" "Error"
        return $false
    }
}

function New-DeploymentPackage {
    Write-Log "Creating deployment package..." "Info"
    
    $packageName = "olt-manager-production-v1.0.zip"
    
    # Remove existing package
    if (Test-Path $packageName) {
        Remove-Item $packageName -Force
    }
    
    # Create package with required files
    $filesToPackage = @(
        "deployment/main_simple.py",
        "deployment/olt-manager-dashboard.html", 
        "deployment/requirements.txt",
        "deployment/.env.production",
        "deployment/init_database.py"
    )
    
    # Check if files exist
    $missingFiles = @()
    foreach ($file in $filesToPackage) {
        if (-not (Test-Path $file)) {
            $missingFiles += $file
        }
    }
    
    if ($missingFiles.Count -gt 0) {
        Write-Log "Missing files: $($missingFiles -join ', ')" "Error"
        return $false
    }
    
    # Create zip package
    try {
        Compress-Archive -Path $filesToPackage -DestinationPath $packageName -Force
        Write-Log "Deployment package created: $packageName" "Success"
        return $true
    } catch {
        Write-Log "Failed to create package: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Backup-OldApplication {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$AppDir
    )
    
    Write-Log "Creating backup of old application..." "Info"
    
    $backupCommand = @"
if [ -d '$AppDir' ]; then
    sudo mkdir -p /opt/olt-manager-backup
    sudo cp -r $AppDir /opt/olt-manager-backup/olt-manager-`$(date +%Y%m%d_%H%M%S)
    echo 'Backup created successfully'
else
    echo 'No existing application to backup'
fi
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $backupCommand
    Write-Log $result.Output "Info"
}

function Stop-ApplicationService {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$ServiceName
    )
    
    Write-Log "Stopping service $ServiceName..." "Info"
    
    $stopCommand = @"
if sudo systemctl is-active --quiet $ServiceName; then
    sudo systemctl stop $ServiceName
    echo 'Service stopped'
else
    echo 'Service not running'
fi
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $stopCommand
    Write-Log $result.Output "Info"
}

function Install-Dependencies {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$AppDir
    )
    
    Write-Log "Installing dependencies..." "Info"
    
    $installCommand = @"
cd $AppDir

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
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $installCommand
    
    if ($result.Success) {
        Write-Log "Dependencies installed successfully" "Success"
    } else {
        Write-Log "Failed to install dependencies: $($result.Output)" "Error"
    }
    
    return $result.Success
}

function Setup-Database {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$AppDir
    )
    
    Write-Log "Setting up database..." "Info"
    
    $dbCommand = @"
# Setup PostgreSQL database
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'olt_manager'" | grep -q 1 || sudo -u postgres createdb olt_manager
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'oltmanager'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER oltmanager WITH PASSWORD 'oltmanager123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE olt_manager TO oltmanager;"

# Initialize database
cd $AppDir
source venv/bin/activate
python init_database.py

echo 'Database setup completed'
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $dbCommand
    
    if ($result.Success) {
        Write-Log "Database setup completed" "Success"
    } else {
        Write-Log "Database setup failed: $($result.Output)" "Error"
    }
    
    return $result.Success
}

function New-SystemdService {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$AppDir,
        [string]$ServiceName
    )
    
    Write-Log "Creating systemd service..." "Info"
    
    $serviceCommand = @"
sudo tee /etc/systemd/system/$ServiceName.service > /dev/null << EOF
[Unit]
Description=OLT Manager Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$AppDir
Environment=PATH=$AppDir/venv/bin
ExecStart=$AppDir/venv/bin/python main_simple.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $ServiceName
echo 'Systemd service created'
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $serviceCommand
    Write-Log $result.Output "Info"
    return $result.Success
}

function Start-ApplicationService {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$ServiceName
    )
    
    Write-Log "Starting service $ServiceName..." "Info"
    
    $startCommand = @"
sudo systemctl start $ServiceName
sleep 3

if sudo systemctl is-active --quiet $ServiceName; then
    echo 'Service started successfully'
    sudo systemctl status $ServiceName --no-pager -l
else
    echo 'Failed to start service'
    sudo journalctl -u $ServiceName --no-pager -l -n 20
    exit 1
fi
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $startCommand
    
    if ($result.Success) {
        Write-Log "Service started successfully" "Success"
    } else {
        Write-Log "Failed to start service: $($result.Output)" "Error"
    }
    
    return $result.Success
}

function Test-Deployment {
    param(
        [string]$Server,
        [string]$User,
        [int]$Port,
        [string]$ServiceName
    )
    
    Write-Log "Verifying deployment..." "Info"
    
    $verifyCommand = @"
# Check service status
echo 'Service Status:'
sudo systemctl status $ServiceName --no-pager

# Check port
echo -e '\nPort Status:'
netstat -tlnp | grep 8000 || echo 'Port 8000 not found'

# Test HTTP response
echo -e '\nHTTP Test:'
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ || echo 'HTTP test failed'

echo -e '\nDeployment verification completed'
"@
    
    $result = Invoke-SSHCommand -Server $Server -User $User -Port $Port -Command $verifyCommand
    Write-Log $result.Output "Info"
    return $result.Success
}

# Main deployment function
function Start-AutoDeployment {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   OLT Manager Auto Deploy ke Localhost" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Log "Target Server: $ServerIP" "Info"
    Write-Log "Deployment Directory: $AppDir" "Info"
    Write-Host ""
    
    # Check SSH connection
    if (-not (Test-SSHConnection -Server $ServerIP -User $Username -Port $Port)) {
        Write-Log "Deployment aborted due to SSH connection failure" "Error"
        return $false
    }
    
    # Create deployment package
    if (-not (New-DeploymentPackage)) {
        Write-Log "Deployment aborted due to package creation failure" "Error"
        return $false
    }
    
    # Backup old application
    Backup-OldApplication -Server $ServerIP -User $Username -Port $Port -AppDir $AppDir
    
    # Stop service
    Stop-ApplicationService -Server $ServerIP -User $Username -Port $Port -ServiceName $ServiceName
    
    # Upload package
    if (-not (Copy-FileToServer -LocalPath "olt-manager-production-v1.0.zip" -Server $ServerIP -User $Username -Port $Port -RemotePath "/tmp/")) {
        Write-Log "Deployment aborted due to file upload failure" "Error"
        return $false
    }
    
    # Setup application
    Write-Log "Setting up application..." "Info"
    $setupCommand = @"
cd /tmp
unzip -o olt-manager-production-v1.0.zip

sudo mkdir -p $AppDir
sudo cp deployment/main_simple.py $AppDir/
sudo cp deployment/olt-manager-dashboard.html $AppDir/
sudo cp deployment/requirements.txt $AppDir/
sudo cp deployment/.env.production $AppDir/.env
sudo cp deployment/init_database.py $AppDir/

sudo chown -R root:root $AppDir
sudo chmod +x $AppDir/main_simple.py

echo 'Application setup completed'
"@
    
    $setupResult = Invoke-SSHCommand -Server $ServerIP -User $Username -Port $Port -Command $setupCommand
    if (-not $setupResult.Success) {
        Write-Log "Application setup failed: $($setupResult.Output)" "Error"
        return $false
    }
    
    # Install dependencies
    if (-not (Install-Dependencies -Server $ServerIP -User $Username -Port $Port -AppDir $AppDir)) {
        Write-Log "Deployment aborted due to dependency installation failure" "Error"
        return $false
    }
    
    # Setup database
    if (-not (Setup-Database -Server $ServerIP -User $Username -Port $Port -AppDir $AppDir)) {
        Write-Log "Deployment aborted due to database setup failure" "Error"
        return $false
    }
    
    # Create systemd service
    if (-not (New-SystemdService -Server $ServerIP -User $Username -Port $Port -AppDir $AppDir -ServiceName $ServiceName)) {
        Write-Log "Deployment aborted due to service creation failure" "Error"
        return $false
    }
    
    # Start service
    if (-not (Start-ApplicationService -Server $ServerIP -User $Username -Port $Port -ServiceName $ServiceName)) {
        Write-Log "Deployment aborted due to service start failure" "Error"
        return $false
    }
    
    # Verify deployment
    Test-Deployment -Server $ServerIP -User $Username -Port $Port -ServiceName $ServiceName
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   DEPLOYMENT SELESAI!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Log "Aplikasi dapat diakses di:" "Success"
    Write-Log "- Local: http://$ServerIP`:8000" "Success"
    Write-Log "- Domain: https://olt.remoteapps.my.id" "Success"
    Write-Log "- Credentials: admin / admin123" "Success"
    Write-Host ""
    Write-Log "Untuk monitoring:" "Info"
    Write-Log "- Status service: ssh $Username@$ServerIP 'sudo systemctl status $ServiceName'" "Info"
    Write-Log "- Log service: ssh $Username@$ServerIP 'sudo journalctl -u $ServiceName -f'" "Info"
    
    return $true
}

# Check prerequisites
Write-Log "Checking prerequisites..." "Info"

# Check if SSH is available
try {
    ssh -V 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "SSH client not found. Please install OpenSSH or PuTTY." "Error"
        exit 1
    }
} catch {
    Write-Log "SSH client not found. Please install OpenSSH or PuTTY." "Error"
    exit 1
}

# Check if SCP is available
try {
    scp 2>$null | Out-Null
} catch {
    Write-Log "SCP not found. Please install OpenSSH." "Error"
    exit 1
}

# Start deployment
if (Start-AutoDeployment) {
    Write-Log "Auto deployment completed successfully!" "Success"
    exit 0
} else {
    Write-Log "Auto deployment failed!" "Error"
    exit 1
}