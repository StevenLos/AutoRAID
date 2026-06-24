# AutoRAID — Windows Usage Guide

Day-to-day operation of the Automated Meetings & Email Notes → RAID Log pipeline on Windows. Setup must be complete before using this guide — see [SETUP-Windows.md](SETUP-Windows.md).

---

## Email workflow

### Step 1 — Export from Outlook

1. Select one or more messages in the Outlook message list.
2. Drag them directly from Outlook into the `Email\Originals\` folder in File Explorer.

Outlook for Windows saves dragged messages as `.msg` files — the expected input format for the Windows pipeline.

### Step 2 — Convert MSG to Markdown

Run the ingest wrapper manually from PowerShell:

```powershell
cd "<vault-root>\Email\Scripts\Windows"
.\run_email_ingest.ps1
```

Or call the Python script directly:

```powershell
python "<vault-root>\Email\Scripts\msg_to_markdown.py" `
    "<vault-root>\Email\Originals" `
    "<vault-root>\Email\Inbox" `
    "<vault-root>\Email\Attachments"
```

If you configured Task Scheduler automation during setup, this step runs automatically and can be skipped.

Each run will:
- Convert new `.msg` files to `.md` notes in `Email\Inbox\`
- Extract attachments to `Email\Attachments\<subject-slug>\`
- Skip emails already processed (deduplication via Message-ID)
- Append a log entry to `Email\Inbox\ingest-log.md`
- Write output to `Email\Scripts\logs\email_ingest.log`

---

## Meeting transcript workflow

### Step 1 — Export from Teams

1. Open the meeting in Teams → **Recap** tab → **Transcript**.
2. Click **...** → **Download as .vtt**.
3. Move the `.vtt` file into `Meetings\Transcripts\`. Teams names the file with the meeting title and date by default — leave the name as-is.

### Step 2 — Convert VTT to Markdown

Run the converter from PowerShell:

```powershell
python "<vault-root>\Email\Scripts\vtt_to_markdown.py" `
    "<vault-root>\Meetings\Transcripts"
```

The script will:
- Convert each new `.vtt` file to a `.md` note in the same folder
- Name the output file `YYYY-MM-DD Meeting Title.md`
- Skip files already converted (deduplication via `.ingest-index.json`)
- Append a log entry to `Meetings\Transcripts\ingest-log.md`

Each converted note matches the structure the RAID prompt expects:

```markdown
# YYYY-MM-DD Meeting Title

**Creation Time**: YYYY/M/D

## Transcription

**00:00:00 - 00:00:15 Speaker Name:**

Transcript text here.
```

### Note: other transcript and note formats

The RAID prompt's only requirement is that input files have a `.md` extension. The content does not need to be formatted Markdown — plain text is fine. This means:

- **Plain text transcripts** (e.g., copy-pasted from Teams, Word, or any other source) can be saved directly as `YYYY-MM-DD Meeting Title.md` and dropped into `Meetings\Transcripts\` — no conversion script needed.
- **Meeting notes, agendas, or written summaries** in any readable format can be ingested the same way.
- The VTT converter exists solely to handle the `.vtt` format Teams exports. For anything already in plain text, just rename the file extension to `.md`.

### Optional: meeting summaries

Save a written or AI-generated summary alongside the transcript as:

```
YYYY-MM-DD Meeting Title (Summary).md
```

The RAID prompt reads both files and cross-references them.

---

## Updating the RAID log

### Run automatically

If the Codex scheduled task is configured (see setup guide), the RAID log updates at your chosen cadence with no action required.

### Run manually

Paste the contents of `03-prompts\Update HHG RAID Log.md` into a Codex session with this vault folder connected and send it.

### What the prompt does

- Scans `Meetings\Transcripts\`, `Meetings\Summary\`, and `Email\Inbox\` for new `.md` files
- Skips any artifact already reflected in the log
- Appends new Risks, Actions, Issues, and Decisions to `RAIDLog\HHG-Phase3-RAIDLog.md`
- Appends new tasks to `AutoTasks\HHG-Phase3-AutoTaskList.md`
- Writes a run summary at the bottom of each file

If no new artifacts are found, neither file is modified.

---

## Day-to-day checklist

**New email to capture:**
1. Drag from Outlook → `Email\Originals\` in File Explorer
2. Run `run_email_ingest.ps1` (or wait for Task Scheduler)

**After a meeting:**
1. Download transcript from Teams → move `.vtt` to `Meetings\Transcripts\`
2. Run `vtt_to_markdown.py` to convert it to `.md`
2. Optionally write a summary → save to `Meetings\Summary\`
3. Run the RAID prompt in Codex (or wait for the scheduled task)

**Reviewing the RAID log:**
- Open `RAIDLog\HHG-Phase3-RAIDLog.md` in Obsidian
- New entries are appended at the bottom; the `Source` field links back to the originating artifact

**Triaging the task list:**
- Open `AutoTasks\HHG-Phase3-AutoTaskList.md`
- New tasks default to `Relevant = TBD` — update each row to `Me` or `N/A`

---

## Troubleshooting

**No files appear in `Email\Originals\` after dragging**
Confirm you are dragging from the Outlook message list (not an open message window) to a File Explorer window showing `Email\Originals\`.

**RAID prompt adds no entries**
The prompt deduplicates by matching filenames against the `Source` fields already in the log. If a file was renamed after the last run, it will appear new. Check the run summary block at the bottom of the RAID log to see exactly what was scanned.
