param(
    [string]$AppRoot = "C:\LukomorieAssistant"
)

$ErrorActionPreference = "Stop"
$taskName = "Lukomorie AI Assistant"
$runner = Join-Path $AppRoot "deploy\windows\start-assistant.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Runner not found: $runner" }

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`" -AppRoot `"$AppRoot`"" `
    -WorkingDirectory $AppRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Installed and started scheduled task: $taskName"
