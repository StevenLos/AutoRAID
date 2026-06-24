# AutoRAID

> *Turn your meetings and email into a living RAID log — automatically.*

AutoRAID is a lightweight ingest pipeline that converts Outlook emails and Teams meeting transcripts into structured Markdown notes, then uses a scheduled Codex task to extract Risks, Actions, Issues, and Decisions (RAID) into a living project log and task list.

## What it does

**Diagram 1 — End-to-end flow**

```
  ┌───────────────────── ────┐       ┌────────────────────  ─────┐
  │      Outlook Email       │       │    Teams Transcript      │
  │  drag to Email/Originals │       │  export .vtt, drop in    │
  │  Mac → .eml              │       │  Meetings/Transcripts/   │
  │  Windows → .msg          │       │                          │
  └────────────┬──────── ────┘       └────────────┬───────  ─────┘
               │                                 │
               ▼                                 ▼
  ┌───────────────────── ────┐       ┌─────────────────────────┐
  │    Converter Script      │       │   Converter Script      │
  │  eml_to_markdown.py (Mac)│       │   vtt_to_markdown.py    │
  │  msg_to_markdown.py (Win)│       │                         │
  └────────────┬─────── ─────┘       └────────────┬────────────┘
               │                                 │
               ▼                                 ▼
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │      Email/Inbox/       │       │   Meetings/Transcripts/ │
  │      (.md notes)        │       │   (.md files)           │
  └────────────┬────────────┘       └────────────┬────────────┘
               │                                 │
               └──────────────────┬──────────────┘
                                  │
                                  ▼
                   ┌──────────────────────── ──┐
                   │    Codex Scheduled Task   │
                   │  scans new .md files and  │
                   │  extracts RAID entries    │
                   └──────────────┬──────── ───┘
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
     ┌─────────────────────────┐   ┌─────────────────────────┐
     │         RAID Log        │   │        Task List         │
     │  Risks / Actions /      │   │  action items extracted  │
     │  Issues / Decisions     │   │  from meetings & email   │
     └─────────────────────────┘   └─────────────────────────┘
```

**Diagram 2 — Platform paths (Mac vs. Windows)**

```
             macOS                              Windows
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │   Drag email from       │       │   Drag email from        │
  │   Outlook to Finder     │       │   Outlook to Explorer    │
  └────────────┬────────────┘       └────────────┬────────────┘
               │ saves as .eml                   │ saves as .msg
               ▼                                 ▼
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │   eml_to_markdown.py    │       │   msg_to_markdown.py    │
  │   run_email_ingest.sh   │       │   run_email_ingest.ps1 │
  │   (launchd optional)    │       │   (Task Scheduler opt.)  │
  └────────────┬────────────┘       └────────────┬────────────┘
               │                                 │
               └──────────────┬──────────────────┘
                              │ identical .md output
                              ▼
                 ┌───────────────────────── ───┐
                 │        Email/Inbox/         │
                 │  (same format, both         │
                 │   platforms — fed into      │
                 │   Codex on same schedule)   │
                 └──────────────────────── ────┘
```

## Folder structure

This repo's layout separates scripts, documentation, and the Codex prompt from any project-specific reference material:

```
/
├── README.md                              ← you are here
├── 01-docs/
│   ├── SETUP-Mac.md                       One-time Mac installation and configuration
│   ├── USAGE-Mac.md                       Day-to-day Mac operation
│   ├── SETUP-Windows.md                   One-time Windows installation and configuration
│   ├── USAGE-Windows.md                   Day-to-day Windows operation
│   └── SETUP-Codex-Scheduled-Task.md      Codex scheduled task setup (both platforms)
├── 02-scripts/
│   ├── Mac/
│   │   ├── eml_to_markdown.py             EML → Markdown converter
│   │   ├── vtt_to_markdown.py             VTT → Markdown converter (cross-platform)
│   │   └── run_email_ingest.sh            Ingest wrapper / launchd target
│   └── Windows/
│       ├── msg_to_markdown.py             MSG → Markdown converter
│       ├── vtt_to_markdown.py             VTT → Markdown converter (cross-platform)
│       ├── run_email_ingest.ps1         Ingest wrapper / Task Scheduler target
│       └── Register-EmailIngestTask.ps1   One-time Task Scheduler registration
└── 03-prompts/
    └── Update RAID Log.md            Codex prompt — paste or schedule in Codex
```

The vault that Codex reads and writes at runtime lives **outside** this repo, managed by each user (see the platform guides for the expected vault layout).

## Platform guides

**macOS**
- **[SETUP-Mac.md](01-docs/SETUP-Mac.md)** — One-time installation and configuration
- **[USAGE-Mac.md](01-docs/USAGE-Mac.md)** — Day-to-day operation

**Windows**
- **[SETUP-Windows.md](01-docs/SETUP-Windows.md)** — One-time installation and configuration
- **[USAGE-Windows.md](01-docs/USAGE-Windows.md)** — Day-to-day operation

## Key components

| Component | Path | Purpose |
|-----------|------|---------|
| Mac EML converter | `02-scripts/Mac/eml_to_markdown.py` | Converts `.eml` files (Outlook for Mac drag output) to Markdown with YAML frontmatter. Deduplicates via Message-ID index. |
| Mac ingest wrapper | `02-scripts/Mac/run_email_ingest.sh` | Shell wrapper called by launchd or manually; logs to `Email/Scripts/logs/`. |
| VTT converter | `02-scripts/Mac/vtt_to_markdown.py` (also in `Windows/`) | Converts Teams `.vtt` transcript files to Markdown. Cross-platform — identical script in both folders. Deduplicates via `.ingest-index.json`. |
| Windows MSG converter | `02-scripts/Windows/msg_to_markdown.py` | Converts `.msg` files (Outlook for Windows drag output) to Markdown with YAML frontmatter. Deduplicates via Message-ID index. |
| Windows ingest wrapper | `02-scripts/Windows/run_email_ingest.ps1` | PowerShell wrapper called by Task Scheduler or manually. |
| Windows scheduler setup | `02-scripts/Windows/Register-EmailIngestTask.ps1` | One-time script to register the ingest job in Windows Task Scheduler. |
| RAID log prompt | `03-prompts/Update RAID Log.md` | The Codex prompt run on a schedule to scan new artifacts and update the RAID log and task list. |

## How the RAID update runs

The RAID log is updated by a **Codex scheduled task** that submits the prompt in `03-prompts/Update RAID Log.md` on a configured cadence (e.g., daily or after each meeting). Codex scans the `Meetings/` and `Email/Inbox/` folders in your vault for new artifacts not yet reflected in the log, then appends structured entries.

No new items are added if no new artifacts are found. See the prompt file itself for the full entry schema and safety rules.

## Prerequisites (both platforms)

- Python 3.9+ with dependencies installed (Mac: `pip3 install markdownify` / Windows: `pip install extract-msg markdownify`)
- Microsoft Outlook (desktop client, not web)
- Codex with this vault folder connected as a workspace
- Microsoft Teams (for transcript exports)
