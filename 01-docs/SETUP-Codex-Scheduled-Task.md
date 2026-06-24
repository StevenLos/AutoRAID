# AutoRAID — Codex Scheduled Task Setup

This guide covers creating and configuring the Codex scheduled task that automatically updates the RAID log and task list. It applies to both Mac and Windows — the Codex setup is identical on both platforms.

---

## What the task does

On a repeating schedule, Codex reads the prompt in `03-prompts/Update HHG RAID Log.md`, scans the vault's `Meetings/` and `Email/Inbox/` folders for new artifacts, and appends structured RAID entries and tasks to the log files. If nothing new is found, no changes are made.

---

## Prerequisites

Before creating the task:

- Codex is installed and open
- The vault folder is connected as a workspace in Codex
- `03-prompts/Update HHG RAID Log.md` exists in the repo folder

---

## Creating the scheduled task

### Step 1 — Open the scheduled tasks panel

In Codex, navigate to the scheduled tasks section (clock or calendar icon in the sidebar).

### Step 2 — Create a new task

Click **New Task** (or equivalent) and configure each field as follows:

---

### Field reference

**Status**
Set to `Active` once configuration is complete. Leave inactive while setting up.

**Runs in**
Select `Local`. The task must run locally because it needs direct access to the vault files on your machine. Do not use a remote/cloud option.

**Project**
Select or type the name of your project workspace — e.g., `HHG-Phase3`. This must match the connected vault folder.

**Repeats**
Set your preferred cadence. Recommended: `Weekdays at 3:00 PM`. This gives a same-day update after afternoon meetings or email reviews. Adjust to match your team's working pattern.

> Common options:
> - `Weekdays at 3:00 PM` — daily update on business days
> - `Daily at 8:00 AM` — morning digest before the day starts
> - `Weekdays at 9:00 AM and 4:00 PM` — twice-daily if meeting volume is high

**Model**
Select `GPT-5.5 Extra High` (or the highest-quality model available). The RAID prompt involves careful deduplication, semantic judgment, and structured output — a higher-capability model produces significantly more accurate results than a faster/smaller one.

**Prompt**
Paste the full contents of `03-prompts/Update HHG RAID Log.md` into the prompt field, or point the task at the file directly if Codex supports file-based prompts.

---

### Step 3 — Activate the task

Once all fields are configured, set **Status** to `Active`. The task will run at the next scheduled time.

---

## Verifying the task ran

After the first scheduled run, confirm it executed correctly:

1. Check the **Last ran** timestamp in the task detail view — it should reflect the most recent scheduled time.
2. Open `RAIDLog/HHG-Phase3-RAIDLog.md` in Obsidian and scroll to the bottom. A `### Run:` block will have been appended with a timestamp, list of scanned files, and count of entries added.
3. If the run summary shows `New meetings found: 0` and no entries were added, that is expected — it means no new artifacts were present since the last run.

---

## Adjusting the schedule

To change the cadence after the task is created:

1. Open the task in Codex.
2. Update the **Repeats** field.
3. Save. The next run will reflect the new schedule.

To pause the task temporarily, set **Status** to `Inactive`. Set it back to `Active` to resume.

---

## Running the task manually

To trigger an update outside the schedule — for example, immediately after adding a new meeting transcript:

1. Open Codex with the vault folder connected.
2. Open a new session.
3. Paste the contents of `03-prompts/Update HHG RAID Log.md` and send it.

This produces the same output as the scheduled run.
