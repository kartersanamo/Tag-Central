@echo off
REM Wrapper for build-windows.ps1 (double-click or cmd).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
if errorlevel 1 exit /b 1
