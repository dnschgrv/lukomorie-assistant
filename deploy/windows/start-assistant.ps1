param(
    [string]$AppRoot = "C:\LukomorieAssistant"
)

$ErrorActionPreference = "Stop"
$envFile = Join-Path $AppRoot ".env"
$python = Join-Path $AppRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $AppRoot "logs"
$logFile = Join-Path $logDir "service.log"

if (-not (Test-Path -LiteralPath $python)) { throw "Python environment not found: $python" }
if (-not (Test-Path -LiteralPath $envFile)) { throw "Configuration not found: $envFile" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=", 2)
    if ($parts.Count -eq 2) {
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1], "Process")
    }
}

Set-Location -LiteralPath $AppRoot
while ($true) {
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "$(Get-Date -Format o) assistant starting"
    & $python -m app.server 2>&1 | ForEach-Object { Add-Content -LiteralPath $logFile -Encoding UTF8 -Value $_ }
    $exitCode = $LASTEXITCODE
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value "$(Get-Date -Format o) assistant stopped with code $exitCode; restarting in 5 seconds"
    Start-Sleep -Seconds 5
}
