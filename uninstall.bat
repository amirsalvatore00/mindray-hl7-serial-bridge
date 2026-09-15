@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Run as Administrator!
    pause
    exit /b 1
)
echo Stopping bridge...
taskkill /F /IM SmartMindrayBridge.exe >nul 2>&1
echo Removing task...
schtasks /delete /tn "MindrayHL7Bridge" /f >nul 2>&1
echo Removing firewall rule...
netsh advfirewall firewall delete rule name="Mindray LIS Server Port 5200" >nul 2>&1
echo Done.
pause