$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Start-Process -FilePath powershell.exe -ArgumentList @(
  '-ExecutionPolicy',
  'Bypass',
  '-File',
  (Join-Path $repoRoot 'scripts\start_backend.ps1')
) -WorkingDirectory $repoRoot

Start-Process -FilePath powershell.exe -ArgumentList @(
  '-ExecutionPolicy',
  'Bypass',
  '-File',
  (Join-Path $repoRoot 'scripts\start_frontend.ps1')
) -WorkingDirectory $repoRoot
