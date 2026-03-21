$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
cmd /c "cd /d $repoRoot\frontend && npm.cmd run dev -- --host 127.0.0.1 --port 5174"
