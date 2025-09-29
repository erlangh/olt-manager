@echo off
REM Quick Deploy Script untuk OLT Manager ke Server Localhost 10.88.8.5
REM Untuk Windows Environment

echo ========================================
echo   OLT Manager Auto Deploy ke Localhost
echo ========================================
echo.

REM Check if WSL is available
wsl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] WSL tidak tersedia. Install WSL terlebih dahulu.
    echo.
    echo Cara install WSL:
    echo 1. Buka PowerShell sebagai Administrator
    echo 2. Jalankan: wsl --install
    echo 3. Restart komputer
    echo 4. Setup Ubuntu di WSL
    pause
    exit /b 1
)

echo [INFO] WSL tersedia, menjalankan deployment script...
echo.

REM Convert Windows path to WSL path
set "SCRIPT_DIR=%~dp0"
set "WSL_SCRIPT_DIR=/mnt/c%SCRIPT_DIR:C:=%"
set "WSL_SCRIPT_DIR=%WSL_SCRIPT_DIR:\=/%"

REM Run the deployment script in WSL
wsl bash -c "cd '%WSL_SCRIPT_DIR%' && chmod +x auto-deploy-localhost.sh && ./auto-deploy-localhost.sh"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   DEPLOYMENT BERHASIL!
    echo ========================================
    echo.
    echo Aplikasi OLT Manager telah berhasil di-deploy ke:
    echo - Server: 10.88.8.5:8000
    echo - Domain: https://olt.remoteapps.my.id
    echo.
    echo Login credentials:
    echo - Username: admin
    echo - Password: admin123
    echo.
) else (
    echo.
    echo ========================================
    echo   DEPLOYMENT GAGAL!
    echo ========================================
    echo.
    echo Silakan cek error message di atas.
    echo.
)

pause