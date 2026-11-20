@echo off
REM Double-click ONCE. Makes the Job Hunter dashboard start hidden every time
REM you log in to Windows, and restarts it now with the latest code.
REM Undo with remove-autostart.bat.
cd /d "%~dp0"
set "PYW="
for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW for /f "delims=" %%i in ('where pyw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW (
  echo Could not find pythonw or pyw on this PC, so autostart was not installed.
  pause
  exit /b 1
)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\job-hunter-dashboard.vbs"
> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%VBS%" echo sh.CurrentDirectory = "%~dp0"
>> "%VBS%" echo sh.Run """%PYW%"" ""%~dp0serve.py"" --no-open", 0, False

echo Stopping any dashboard already running on port 8787...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8787" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
timeout /t 2 >nul

echo Starting it in the background...
wscript "%VBS%"
timeout /t 5 >nul
start "" http://127.0.0.1:8787/
echo.
echo Done. It now starts by itself when you log in, with no window.
echo Bookmark http://127.0.0.1:8787/ and just open it.
pause
