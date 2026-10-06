@echo off
chcp 65001 >nul
echo Instalando el cangrejito de Claude...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
echo.
pause
