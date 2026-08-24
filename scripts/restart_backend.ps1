# Restart backend uvicorn process on Windows.
# Uses Win32_Process to find the uvicorn process by command line match,
# kills it gracefully, then relaunches in background.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/restart_backend.ps1
$proc = Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -like "*uvicorn app.main:app*" -and $_.ProcessId -ne $PID
}
if ($proc) {
  Write-Host "Stopping uvicorn PID(s): $($proc.ProcessId -join ', ')"
  $proc | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
} else {
  Write-Host "No uvicorn process found"
}
Start-Sleep -Seconds 1

# 启动新进程（后台）
$PY = "C:\Users\admin\.workbuddy\binaries\python\envs\btplat\Scripts\python.exe"
$BackendDir = Join-Path $PSScriptRoot "..\backend"
Push-Location $BackendDir
Write-Host "Launching new uvicorn..."
Start-Process -FilePath $PY -ArgumentList "-m","uvicorn app.main:app --host 0.0.0.0 --port 8000" `
  -WorkingDirectory $BackendDir -WindowStyle Hidden
Pop-Location
Start-Sleep -Seconds 2
Write-Host "Done. Health check: http://127.0.0.1:8000/api/health"