@echo off
REM Double-click me. Finds the workspace by walking up for CLAUDE.md.
cd /d "%~dp0"
python serve.py %*
if errorlevel 1 (
  echo.
  echo Couldn't start with 'python'. Trying 'py'...
  py -3 serve.py %*
)
pause
