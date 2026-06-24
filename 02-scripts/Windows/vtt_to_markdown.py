#!/usr/bin/env python3
"""
vtt_to_markdown.py — Part of the AutoRAID pipeline.
Convert Teams VTT transcripts to Markdown notes.

Usage:
    python3 vtt_to_markdown.py <input_dir> [output_dir]

    input_dir:  folder containing .vtt files (e.g., Meetings/Transcripts/)
    output_dir: folder to write .md files    (defaults to input_dir)

Already-converted files are tracked in <output_dir>/.ingest-index.json and
skipped on subsequent runs. A log entry is appended to ingest-log.md each run.

Output format matches the expected structure for the Codex RAID update prompt:

    # YYYY-MM-DD Meeting Title

    **Creation Time**: YYYY/M/D

    ## Transcription

    **HH:MM:SS - HH:MM:SS Speaker Name:**

    Transcript text here.

Input filename convention (Teams default):
    2026-04-13 Meeting Title (Transcription).vtt
    2026-04-13 Meeting Title.vtt

No third-party dependencies — uses Python standard library only.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ── Deduplication index ───────────────────────────────────────────────────────

INDEX_FILE = ".ingest-index.json"


def load_index(output_dir: Path) -> set:
    path = output_dir / INDEX_FILE
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_index(output_dir: Path, index: set) -> None:
    path = output_dir / INDEX_FILE
    path.write_text(json.dumps(sorted(index), indent=2), encoding="utf-8")


# ── VTT parsing ───────────────────────────────────────────────────────────────

def strip_ms(ts: str) -> str:
    """00:00:04.920 → 00:00:04  (drop milliseconds, ensure HH:MM:SS)."""
    ts = re.sub(r"\.\d+$", "", ts.strip())
    parts = ts.split(":")
    if len(parts) == 2:          # MM:SS → 00:MM:SS
        ts = f"00:{parts[0]}:{parts[1]}"
    return ts


def parse_vtt(path: Path) -> list:
    """
    Return a list of cue dicts: {start, end, speaker, text}.
    Handles two Teams VTT speaker formats:
        <v Speaker Name>text</v>       (standard WebVTT)
        Speaker Name: text             (some Teams exports)
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cues = []
    i = 0

    # Skip WEBVTT header and any NOTE/STYLE blocks before first timestamp
    while i < len(lines) and not re.match(r"\d", lines[i].lstrip()):
        i += 1

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Skip cue identifier lines (no "-->" present)
        if "-->" not in line:
            i += 1
            continue

        # Timestamp line: 00:00:00.000 --> 00:00:04.920
        ts_match = re.match(r"([\d:.]+)\s+-->\s+([\d:.]+)", line)
        if not ts_match:
            i += 1
            continue

        start = strip_ms(ts_match.group(1))
        end   = strip_ms(ts_match.group(2))
        i += 1

        # Collect payload lines until a blank line
        payload_lines = []
        while i < len(lines) and lines[i].strip():
            payload_lines.append(lines[i].strip())
            i += 1

        raw = " ".join(payload_lines)

        # Extract speaker — try <v Speaker>text</v> first
        speaker = ""
        m = re.match(r"<v\s+([^>]+)>(.*?)(?:</v>)?$", raw, re.DOTALL)
        if m:
            speaker = m.group(1).strip()
            raw     = m.group(2).strip()
        else:
            # Try "Speaker Name: text" (capitalised word(s) before colon)
            m2 = re.match(r"^([A-Z][^:<>]{1,50}):\s+(.*)", raw)
            if m2:
                speaker = m2.group(1).strip()
                raw     = m2.group(2).strip()

        # Strip any remaining inline VTT/HTML tags
        raw = re.sub(r"<[^>]+>", "", raw).strip()

        if raw:
            cues.append({"start": start, "end": end, "speaker": speaker, "text": raw})

    return cues


# ── Filename → date + title ───────────────────────────────────────────────────

def extract_meta(filename: str):
    """
    Parse date and title from a Teams transcript filename.
    Returns (date_iso, creation_time, title).

    Examples:
        "2026-04-13 Phase 3 Discussion (Transcription).vtt"
            → ("2026-04-13", "2026/4/13", "Phase 3 Discussion")
        "Meeting Notes.vtt"
            → (today, today_slash, "Meeting Notes")
    """
    stem = Path(filename).stem
    # Strip trailing parenthetical, e.g. "(Transcription)", "(Teams)"
    stem = re.sub(r"\s*\([^)]*\)\s*$", "", stem).strip()

    m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.*)", stem)
    if m:
        date_iso = m.group(1)
        title    = m.group(2).strip()
        dt = datetime.strptime(date_iso, "%Y-%m-%d")
        creation_time = f"{dt.year}/{dt.month}/{dt.day}"
        return date_iso, creation_time, title

    # No date prefix — fall back to today
    today = datetime.today()
    return (
        today.strftime("%Y-%m-%d"),
        f"{today.year}/{today.month}/{today.day}",
        stem,
    )


# ── Output path collision avoidance ──────────────────────────────────────────

def unique_path(output_dir: Path, stem: str) -> Path:
    p = output_dir / f"{stem}.md"
    if not p.exists():
        return p
    n = 1
    while True:
        p = output_dir / f"{stem}-{n}.md"
        if not p.exists():
            return p
        n += 1


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_markdown(cues: list, date_iso: str, creation_time: str, title: str) -> str:
    lines = [
        f"# {date_iso} {title}",
        "",
        f"**Creation Time**: {creation_time}",
        "",
        "## Transcription",
        "",
    ]

    for cue in cues:
        speaker_part = f" {cue['speaker']}" if cue["speaker"] else ""
        lines.append(f"**{cue['start']} - {cue['end']}{speaker_part}:**")
        lines.append("")
        lines.append(cue["text"])
        lines.append("")

    return "\n".join(lines)


# ── Ingest log ────────────────────────────────────────────────────────────────

def append_log(output_dir: Path, entries: list) -> None:
    if not entries:
        return
    log_path = output_dir / "ingest-log.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = [f"\n## {ts}\n"] + [f"- {e}" for e in entries]
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(block) + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def convert_directory(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    index = load_index(output_dir)

    vtt_files = sorted(input_dir.glob("*.vtt"))
    if not vtt_files:
        print(f"No .vtt files found in {input_dir}")
        return

    new_count = skip_count = error_count = 0
    log_entries = []

    for vtt_path in vtt_files:
        fname = vtt_path.name

        if fname in index:
            skip_count += 1
            continue

        print(f"Converting: {fname}")
        try:
            cues = parse_vtt(vtt_path)
            date_iso, creation_time, title = extract_meta(fname)
            md = render_markdown(cues, date_iso, creation_time, title)

            out_path = unique_path(output_dir, f"{date_iso} {title}")
            out_path.write_text(md, encoding="utf-8")

            index.add(fname)
            new_count += 1
            log_entries.append(f"Converted `{fname}` → `{out_path.name}`")
            print(f"  → {out_path.name}")

        except Exception as exc:
            error_count += 1
            print(f"  ERROR: {exc}")

    save_index(output_dir, index)
    append_log(output_dir, log_entries)

    print(
        f"\nDone. Converted: {new_count}  |  "
        f"Skipped (already processed): {skip_count}  |  "
        f"Errors: {error_count}"
    )


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_dir  = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else input_dir

    if not input_dir.is_dir():
        print(f"ERROR: input directory not found: {input_dir}")
        sys.exit(1)

    convert_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()
