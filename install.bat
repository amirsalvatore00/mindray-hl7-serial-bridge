@echo off
setlocal
title Mindray Bridge Installer
echo ============================================================
echo   Mindray BC-5150 Smart Bridge - Auto Installer
echo ============================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Run this file as Administrator!
    pause
    exit /b 1
)

echo [1/5] Setting static IP on second NIC...
netsh interface ip set address name="Ethernet 2" static 192.168.200.192 255.255.255.0 >nul 2>&1
if %errorlevel% neq 0 (
    echo     Trying "Ethernet 3"...
    netsh interface ip set address name="Ethernet 3" static 192.168.200.192 255.255.255.0 >nul 2>&1
)
echo     [OK]

echo [2/5] Setting network profile to Private...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object {$_.InterfaceAlias -match 'Ethernet'} | ForEach-Object { Set-NetConnectionProfile -InterfaceIndex $_.InterfaceIndex -NetworkCategory Private -ErrorAction SilentlyContinue }" >nul 2>&1
echo     [OK]

echo [3/5] Adding firewall rule for TCP 5200...
netsh advfirewall firewall delete rule name="Mindray LIS Server Port 5200" >nul 2>&1
netsh advfirewall firewall add rule name="Mindray LIS Server Port 5200" dir=in action=allow protocol=TCP localport=5200 >nul 2>&1
if %errorlevel% neq 0 (
    echo     [WARN] Firewall rule blocked by GPO. Ask IT.
) else (
    echo     [OK]
)

echo [4/5] Registering auto-start task...
schtasks /delete /tn "MindrayHL7Bridge" /f >nul 2>&1

set "EXE_PATH=%~dp0SmartMindrayBridge.exe"
if not exist "%EXE_PATH%" (
    echo     [ERROR] SmartMindrayBridge.exe not found!
    pause
    exit /b 1
)

schtasks /create /tn "MindrayHL7Bridge" /tr "\"%EXE_PATH%\"" /sc onstart /ru SYSTEM /rl HIGHEST /f >nul 2>&1
if %errorlevel% neq 0 (
    echo     [ERROR] Failed to register task.
    pause
    exit /b 1
)
echo     [OK]

echo [5/5] Starting bridge now...
taskkill /F /IM SmartMindrayBridge.exe >nul 2>&1
start "" "%EXE_PATH%"
echo     [OK]

echo.
echo ============================================================
echo   INSTALLATION COMPLETE
echo ============================================================
echo Check "server_bridge_log.txt" for status.
pause
endlocal