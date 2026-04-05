@echo off
echo ========================================
echo CV Builder Server Restart Script
echo ========================================
echo.
echo This script will restart the server to clear all caches
echo.
echo Stopping any running uvicorn processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq uvicorn*" 2>nul
timeout /t 2 /nobreak >nul
echo.
echo Starting server with auto-reload...
echo Server will be available at: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.
uvicorn apps.api.main:app --reload --port 8000
