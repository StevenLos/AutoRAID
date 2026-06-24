# AutoRAID — Windows Setup Guide

One-time setup for the Automated Meetings & Email Notes → RAID Log pipeline on Windows. Once complete, refer to [USAGE-Windows.md](USAGE-Windows.md) for day-to-day operation.

---

## Prerequisites

Before starting, confirm you have:

- **Windows 10 or 11**
- **Python 3.9+** — download from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**.
- **Microsoft Outlook** (desktop client — not Outlook Web)
- **Microsoft Teams** (for transcript exports)
- **Codex** with this vault folder connected as a workspace
- **Obsidian** (recommended) or another Markdown viewer — download from [obsidian.md](https://obsidian.md)
- **PowerShell 5.1+** (included in Windows 10/11 — no separate install needed)

---

## 1. Allow PowerShell scripts to run

By default, Windows blocks unsigned PowerShell scripts. Run this once in an elevated PowerShell prompt (right-click PowerShell → "Run as Administrator"):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

`RemoteSigned` allows locally-written scripts to run while still blocking untrusted scripts downloaded from the internet.

---

## 2. Folder setup

Create the following structure under your vault root. Replace `<vault-root>` with your actual path (e.g., `C:\Users\yourname\Documents\ObsidianVaults\HHG\HHG-Phase3`).

```
<vault-root>\
├── Email\
│   ├── Originals\
│   ├── Inbox\
│   ├── Attachments\
│   └── Scripts\
│       ├── msg_to_markdown.py
│       ├── vtt_to_markdown.py
│       ├── logs\
│       └── Windows\
│           ├── run_email_ingest.ps1
│           └── Register-EmailIngestTask.ps1
├── Meetings\
│   ├── Transcripts\
│   └── Summary\
├── RAIDLog\
└── AutoTasks\
```

To create the folders from PowerShell:

```powershell
$vault = "C:\Users\yourname\Documents\ObsidianVaults\YourVault"

@(
    "$vault\Email\Originals",
    "$vault\Email\Inbox",
    "$vault\Email\Attachments",
    "$vault\Email\Scripts\logs",
    "$vault\Email\Scripts\Windows",
    "$vault\Meetings\Transcripts",
    "$vault\Meetings\Summary",
    "$vault\RAIDLog",
    "$vault\AutoTasks"
) | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
```

Copy `msg_to_markdown.py`, `vtt_to_markdown.py`, `run_email_ingest.ps1`, and `Register-EmailIngestTask.ps1` from `02-scripts/Windows/` in this repo into the paths shown above.

---

## 3. Install Python dependencies

```powershell
pip install extract-msg markdownify
```

`extract-msg` parses the `.msg` format Outlook produces on Windows. `markdownify` converts HTML email bodies to clean Markdown. If `pip` is not recognized, use `python -m pip install extract-msg markdownify`.

---

## 4. Configure the scripts

Open `run_email_ingest.ps1` and `Register-EmailIngestTask.ps1` and update the `$VaultRoot` default value near the top of each file:

```powershell
[string]$VaultRoot = "C:\Users\yourname\Documents\ObsidianVaults\YourVault"
```

All other paths are derived from `$VaultRoot` automatically.

### msg_to_markdown.py — sender tagging

The converter auto-tags notes by the sender's domain. Edit `SENDER_PROJECT_RULES` near the top of `msg_to_markdown.py` to match your engagement:

```python
SENDER_PROJECT_RULES: dict[str, str] = {
    "clientdomain.com":  "ClientProject",
    "yourfirm.com":      "Internal",
}
```

---

## 5. Optional: automate MSG conversion with Task Scheduler

To run `run_email_ingest.ps1` on a schedule without manual intervention, use `Register-EmailIngestTask.ps1`.

### Register an hourly task

```powershell
cd "<vault-root>\Email\Scripts\Windows"
.\Register-EmailIngestTask.ps1
```

### Register a daily task (e.g., 7:30 AM)

```powershell
.\Register-EmailIngestTask.ps1 -IntervalMinutes 0 -DailyAt "07:30"
```

The task appears in **Task Scheduler** under `EmailIngest-<vault-folder-name>` and runs under your user account while you are logged on.

To remove it later:

```powershell
Unregister-ScheduledTask -TaskName "EmailIngest-YourVault" -Confirm:$false
```

---

## 6. Configure the Codex scheduled task

The RAID log and task list are updated by a Codex scheduled task. Full setup instructions — including all UI fields, recommended settings, and verification steps — are in a dedicated guide:

→ **[SETUP-Codex-Scheduled-Task.md](SETUP-Codex-Scheduled-Task.md)**

The Codex setup is identical on Mac and Windows, so this guide covers both platforms.

---

## Troubleshooting

**PowerShell reports "script is not digitally signed"**
Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in an elevated terminal (see Step 1).

**`python` is not recognized**
Reinstall Python from python.org and check "Add Python to PATH" during installation. Restart your terminal after reinstalling.

**`msg_to_markdown.py` produces garbled HTML in note body**
Install `markdownify`: `pip install markdownify`. Without it the script uses a basic regex fallback.

**Emails are re-processed after moving the vault**
The deduplication index lives at `Email\Inbox\.ingest-index.json`. Copy it with the rest of the vault when moving — it is safe to keep and contains no sensitive data.

**Task Scheduler job does not appear to run**
Open Task Scheduler, find the task under Task Scheduler Library, and check the Last Run Result column. Common causes: Python not on PATH for the scheduled user context, or `$VaultRoot` still set to the placeholder value.
