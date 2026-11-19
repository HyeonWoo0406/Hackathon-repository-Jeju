@echo off
setlocal
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\manage_server.py"
if errorlevel 1 pause
