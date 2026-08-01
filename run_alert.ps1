$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir ("alert_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

$env:PYTHONIOENCODING = "utf-8"
# PowerShell의 파이프라인/콘솔 인코딩 변환을 거치면 UTF-8 바이트가 깨지므로
# cmd.exe의 raw 리다이렉션으로 바이트를 그대로 파일에 기록한다.
cmd /c "`"$root\qqq_alert.exe`" > `"$logFile`" 2>&1"
exit $LASTEXITCODE
