$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir ("alert_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

$env:PYTHONIOENCODING = "utf-8"
& "$root\venv\Scripts\python.exe" "$root\alert_job.py" 2>&1 | Out-File -FilePath $logFile -Encoding utf8
exit $LASTEXITCODE
