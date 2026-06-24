<#
.SYNOPSIS
    AutoRAID — Runs the MSG-to-Markdown conversion pipeline.

.DESCRIPTION
    Windows wrapper around msg_to_markdown.py. Equivalent to run_email_ingest.sh
    on macOS. Can be called manually or registered with Windows Task Scheduler
    via Register-EmailIngestTask.ps1.

    Reads .msg files from Email\Originals, converts them to Markdown notes in
    Email\Inbox, and extracts attachments to Email\Attachments. Output is
    logged to Email\Scripts\logs\email_ingest.log.

.PARAMETER VaultRoot
    Root path of your vault. Edit the default value below to match your setup.

.EXAMPLE
    .\run_email_ingest.ps1
    Runs the ingest pipeline with the default vault path.

.EXAMPLE
    .\run_email_ingest.ps1 -VaultRoot "C:\Users\me\Vault"
    Runs with an explicit vault path.

.NOTES
    Requirements:
      - Python 3.9+ on PATH (verify with: python --version)
      - extract-msg installed: pip install extract-msg
      - markdownify installed: pip install markdownify

    msg_to_markdown.py must exist at:
      <VaultRoot>\Email\Scripts\msg_to_markdown.py
#>

[CmdletBinding()]
param(
    # -----------------------------------------------------------------------
    # Edit this default path to match your vault root
    # -----------------------------------------------------------------------
    [string]$VaultRoot = "$env:USERPROFILE\Documents\ObsidianVaults\YourVault"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Derived paths — do not edit unless you changed the folder structure
# ---------------------------------------------------------------------------
$Originals  = Join-Path $VaultRoot "Email\Originals"
$Inbox      = Join-Path $VaultRoot "Email\Inbox"
$Attachments = Join-Path $VaultRoot "Email\Attachments"
$Script     = Join-Path $VaultRoot "Email\Scripts\msg_to_markdown.py"
$LogDir     = Join-Path $VaultRoot "Email\Scripts\logs"
$LogFile    = Join-Path $LogDir "email_ingest.log"

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
if (-not (Test-Path $Script)) {
    Write-Error "Script not found: $Script`nEnsure msg_to_markdown.py is in Email\Scripts\ under your vault root."
    exit 1
}

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Check Python is available
$pythonCmd = $null
foreach ($candidate in @("python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $pythonCmd = $candidate
        break
    }
}
if (-not $pythonCmd) {
    $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: Python not found on PATH."
    Add-Content -Path $LogFile -Value $msg
    Write-Error "Python not found. Install Python 3.9+ and ensure it is on your PATH."
    exit 1
}

# ---------------------------------------------------------------------------
# Run the converter
# ---------------------------------------------------------------------------
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "`n--- Run started: $timestamp ---"

& $pythonCmd $Script $Originals $Inbox $Attachments 2>&1 |
    Tee-Object -FilePath $LogFile -Append

$exitCode = $LASTEXITCODE
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "--- Run ended: $timestamp (exit code: $exitCode) ---"

exit $exitCode
