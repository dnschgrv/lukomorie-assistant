param([string]$AppRoot = "C:\LukomorieAssistant")
$ErrorActionPreference = "Stop"
$envFile = Join-Path $AppRoot ".env"
Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=", 2)
    if ($parts.Count -eq 2) { [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1], "Process") }
}
Set-Location -LiteralPath $AppRoot
& (Join-Path $AppRoot ".venv\Scripts\python.exe") -m app.ingest --rebuild
if ($LASTEXITCODE -ne 0) { throw "Index build failed with code $LASTEXITCODE" }
