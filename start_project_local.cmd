@echo off
setlocal

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

start "" powershell.exe -ExecutionPolicy Bypass -File "%REPO_ROOT%scripts\start_backend.ps1"
start "" powershell.exe -ExecutionPolicy Bypass -File "%REPO_ROOT%scripts\start_frontend.ps1"
