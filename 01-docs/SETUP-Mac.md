# AutoRAID — Mac Setup Guide

One-time setup for the Automated Meetings & Email Notes → RAID Log pipeline on macOS. Once complete, refer to [USAGE-Mac.md](USAGE-Mac.md) for day-to-day operation.

---

## Prerequisites

Before starting, confirm you have:

- **macOS 12+** (Monterey or later recommended)
- **Python 3.9+** — check with `python3 --version` in Terminal
- **Microsoft Outlook for Mac** (desktop client)
- **Microsoft Teams** (for transcript exports)
- **Codex** with this vault folder connected as a workspace
- **Obsidian** (recommended) or another Markdown viewer — download from [obsidian.md](https://obsidian.md)

---

## 1. Folder setup

Create the following structure under your vault root. Replace `<vault-root>` with your actual path (e.g., `~/Documents/ObsidianVaults/HHG/HHG-Phase3`).

```
<vault-root>/
├── Email/
│   ├── Originals/
│   ├── Inbox/
│   ├── Attachments/
│   └── Scripts/
│       ├── eml_to_markdown.py
│       ├── vtt_to_markdown.py
│       ├── run_email_ingest.sh
│       └── logs/
├── Meetings/
│   ├── Transcripts/
│   └── Summary/
├── RAIDLog/
└── AutoTasks/
```

Copy the Mac scripts from `02-scripts/Mac/` in this repo into `<vault-root>/Email/Scripts/`. This includes `eml_to_markdown.py`, `vtt_to_markdown.py`, and `run_email_ingest.sh`. To create any missing folders:

```zsh
mkdir -p <vault-root>/Email/{Originals,Inbox,Attachments,Scripts/logs}
mkdir -p <vault-root>/Meetings/{Transcripts,Summary}
mkdir -p <vault-root>/RAIDLog
mkdir -p <vault-root>/AutoTasks
```

---

## 2. Install Python dependency

```zsh
pip3 install markdownify
```

`markdownify` converts HTML email bodies to clean Markdown. Without it, `eml_to_markdown.py` falls back to basic tag stripping, which produces messier output.

---

## 3. Configure the scripts

### run_email_ingest.sh

Open `Email/Scripts/run_email_ingest.sh` and set your vault path:

```zsh
VAULT="/Users/yourname/Documents/ObsidianVaults/YourVault"
```

All other paths are derived from `VAULT` automatically. Then make the script executable:

```zsh
chmod +x "<vault-root>/Email/Scripts/run_email_ingest.sh"
```

### eml_to_markdown.py — sender tagging

The converter auto-tags notes by the sender's domain. Edit `SENDER_PROJECT_RULES` near the top of `eml_to_markdown.py` to match your engagement:

```python
SENDER_PROJECT_RULES: dict[str, str] = {
    "clientdomain.com":  "ClientProject",
    "yourfirm.com":      "Internal",
}
```

---

## 4. Optional: automate EML conversion with launchd

To run `run_email_ingest.sh` on a schedule (e.g., every hour) without manual intervention, create a launchd plist:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.email-ingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>/Users/yourname/Documents/ObsidianVaults/YourVault/Email/Scripts/run_email_ingest.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/yourname/Documents/ObsidianVaults/YourVault/Email/Scripts/logs/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/yourname/Documents/ObsidianVaults/YourVault/Email/Scripts/logs/launchd-stderr.log</string>
</dict>
</plist>
```

Save it to `~/Library/LaunchAgents/com.yourname.email-ingest.plist`, then load it:

```zsh
launchctl load ~/Library/LaunchAgents/com.yourname.email-ingest.plist
```

This runs conversion automatically whenever new `.eml` files appear in `Originals/`. The RAID log update is a separate scheduled task configured in Codex (see step 5 below).

---

## 5. Configure the Codex scheduled task

The RAID log and task list are updated by a Codex scheduled task. Full setup instructions — including all UI fields, recommended settings, and verification steps — are in a dedicated guide:

→ **[SETUP-Codex-Scheduled-Task.md](SETUP-Codex-Scheduled-Task.md)**

The Codex setup is identical on Mac and Windows, so this guide covers both platforms.

---

## Troubleshooting

**`eml_to_markdown.py` produces garbled HTML in the note body**
Install `markdownify`: `pip3 install markdownify`. The script falls back to basic tag stripping if the library is absent.

**Emails are processed twice / duplicates appear**
Check that `Email/Inbox/.ingest-index.json` exists. If it was deleted, the script will reprocess all EML files. Re-running is safe — new notes get `-1`, `-2` suffixes rather than overwriting existing ones.

**launchd job does not appear to run**
Confirm the plist path is exactly `~/Library/LaunchAgents/com.yourname.email-ingest.plist` and that the script path inside the plist matches your actual vault location. Check `launchd-stderr.log` for errors.
