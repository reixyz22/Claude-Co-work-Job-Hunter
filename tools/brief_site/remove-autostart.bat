@echo off
REM Turns autostart off and stops the background dashboard.
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\job-hunter-dashboard.vbs"
if exist "%VBS%" del "%VBS%"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8787" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
echo Autostart removed and the dashboard stopped. start-dashboard.bat still works by hand.
pause
