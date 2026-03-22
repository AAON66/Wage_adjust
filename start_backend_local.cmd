@echo off
setlocal

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

powershell.exe -ExecutionPolicy Bypass -File "%REPO_ROOT%scripts\start_backend.ps1"
