$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv/Scripts/pythonw.exe'
$collectorPath = Join-Path $PSScriptRoot 'collect_public.py'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Python environment is missing.' }
$taskName = 'JejuWeeklyPublicData'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and ($existing.Actions.Execute -ne $pythonPath)) { throw 'A different task uses this name.' }
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"{0}" --run' -f $collectorPath) -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At '06:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Select-Object TaskName,State
