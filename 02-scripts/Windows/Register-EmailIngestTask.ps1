<#
.SYNOPSIS
    AutoRAID — Registers a Windows Task Scheduler job to run the email ingest pipeline.

.DESCRIPTION
    Creates a scheduled task that calls run_email_ingest.ps1 on a repeating
    interval. The task runs under the current user's credentials and does not
    require elevated privileges.

    Run this script once to register the task. After registration, the task
    appears in Task Scheduler under the name defined by $TaskName.

    To remove the task later:
        Unregister-ScheduledTask -TaskName "EmailIngest-YourVault" -Confirm:$false

.PARAMETER VaultRoot
    Root path of your vault. Edit the default value below to match your setup.

.PARAMETER TaskName
    Name for the scheduled task. Defaults to "EmailIngest-<vault folder name>".

.PARAMETER IntervalMinutes
    How often the task runs, in minutes. Default: 60 (every hour).
    Set to 0 to use a daily trigger instead (see -DailyAt).

.PARAMETER DailyAt
    If IntervalMinutes is 0, run once daily at this time. Format: "HH:mm".
    Example: "08:00" for 8 AM.

.EXAMPLE
    .\Register-EmailIngestTask.ps1
    Registers an hourly task with default settings.

.EXAMPLE
    .\Register-EmailIngestTask.ps1 -IntervalMinutes 0 -DailyAt "07:30"
    Registers a daily task that runs at 7:30 AM.

.NOTES
    Requires: Windows 8 / Server 2012 or later (ScheduledTasks module).
    Must be run as the user who will own the task (not necessarily elevated).
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    # -----------------------------------------------------------------------
    # Edit this default path to match your vault root
    # -----------------------------------------------------------------------
    [string]$VaultRoot = "$env:USERPROFILE\Documents\ObsidianVaults\YourVault",

    [string]$TaskName       = "",
    [int]   $IntervalMinutes = 60,
    [string]$DailyAt         = "07:00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Derive task name from vault folder if not provided
if (-not $TaskName) {
    $vaultLeaf = Split-Path $VaultRoot -Leaf
    $TaskName  = "EmailIngest-$vaultLeaf"
}

$wrapperScript = Join-Path $VaultRoot "Email\Scripts\Windows\run_email_ingest.ps1"

if (-not (Test-Path $wrapperScript)) {
    Write-Error "Wrapper script not found: $wrapperScript`nEnsure run_email_ingest.ps1 is deployed to Email\Scripts\Windows\ under your vault root."
    exit 1
}

# PowerShell executable path
$psExe = (Get-Command powershell.exe -ErrorAction SilentlyContinue)?.Source
if (-not $psExe) {
    $psExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
}

# Action: run the wrapper script
$action = New-ScheduledTaskAction `
    -Execute $psExe `
    -Argument "-NonInteractive -NoProfile -ExecutionPolicy Bypass -File `"$wrapperScript`" -VaultRoot `"$VaultRoot`""

# Trigger
if ($IntervalMinutes -gt 0) {
    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -Once -At (Get-Date)
    $triggerDesc = "every $IntervalMinutes minutes"
} else {
    [DateTime]$dailyTime = [DateTime]::ParseExact($DailyAt, "HH:mm", $null)
    $trigger = New-ScheduledTaskTrigger -Daily -At $dailyTime
    $triggerDesc = "daily at $DailyAt"
}

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -WakeToRun:$false

# Principal (current user, run only when logged on)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task ($triggerDesc)")) {
    # Remove existing task with the same name if present
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[info] Removed existing task: $TaskName"
    }

    Register-ScheduledTask `
        -TaskName  $TaskName `
        -Action    $action `
        -Trigger   $trigger `
        -Settings  $settings `
        -Principal $principal `
        -Description "Converts new .eml files in $VaultRoot to Markdown notes." |
        Out-Null

    Write-Host "[ok] Registered scheduled task: $TaskName"
    Write-Host "     Schedule: $triggerDesc"
    Write-Host "     Script:   $wrapperScript"
    Write-Host ""
    Write-Host "To view the task: Open Task Scheduler and look under Task Scheduler Library."
    Write-Host "To remove it:     Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
}
