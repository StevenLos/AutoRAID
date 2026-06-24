"""
eml_to_markdown.py — Part of the AutoRAID pipeline.
Converts .eml files into Markdown notes.

Improvements over v1:
  - Message-ID based deduplication (index file)
  - HTML-to-Markdown conversion via markdownify
  - Attachment extraction to sibling folder
  - Richer frontmatter (message_id, tags, project, attachments)
  - Sender-based auto-tagging
  - Vault-internal ingest log (ingest-log.md)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    from markdownify import markdownify as md_convert
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Map sender-domain (or full address) fragments → project tag.
# Keys are matched case-insensitively as substrings against the From header.
# First match wins.
SENDER_PROJECT_RULES: dict[str, str] = {
    "hhglobal.com":      "HHG",
    "inwk.com": "HHG",
    "westmonroe.com":    "WM",
    # Add more as needed:
    # "clientdomain.com": "ClientProject",
}

# Default tags applied to every generated note
DEFAULT_TAGS = ["email", "inbox"]

# Name of the index file that tracks processed Message-IDs
INDEX_FILENAME = ".ingest-index.json"

# Name of the vault-internal log file written inside md_dir
LOG_FILENAME = "ingest-log.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:120] or "untitled-email"


def load_index(md_dir: Path) -> dict[str, str]:
    """Load the Message-ID → output filename index."""
    index_path = md_dir / INDEX_FILENAME
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_index(md_dir: Path, index: dict[str, str]) -> None:
    index_path = md_dir / INDEX_FILENAME
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def resolve_project(sender: str) -> str:
    """Return project tag based on sender address, or empty string."""
    sender_lower = sender.lower()
    for fragment, project in SENDER_PROJECT_RULES.items():
        if fragment.lower() in sender_lower:
            return project
    return ""


def html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown. Falls back to basic tag stripping."""
    if HAS_MARKDOWNIFY:
        result = md_convert(
            html,
            heading_style="ATX",
            bullets="-",
            strip=["script", "style", "head"],
        )
        return result.strip()
    # Basic fallback: strip tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    return text.strip()


def cleanup_body(body: str) -> str:
    """Normalize whitespace and trim quoted reply chains."""
    body = body.replace("\r\n", "\n").replace("\r", "\n")

    # Remove common mobile/app footers
    body = re.sub(
        r"\nSent from my .*$",
        "",
        body,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    body = re.sub(
        r"\nGet Outlook for .*$",
        "",
        body,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Trim at common reply-chain markers (first occurrence only)
    markers = [
        r"^On .{10,100} wrote:\s*$",
        r"^From:\s.+$",
        r"^Sent:\s.+$",
        r"^-----Original Message-----\s*$",
        r"^_{5,}\s*$",
    ]

    lines = body.split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in markers):
            break
        out.append(line)

    body = "\n".join(out).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body


def extract_body(msg) -> str:
    """Extract and convert the message body to Markdown."""
    plain: str | None = None
    html: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition.lower():
                continue
            try:
                payload = part.get_content()
            except Exception:
                continue
            if content_type == "text/plain" and plain is None:
                plain = payload
            elif content_type == "text/html" and html is None:
                html = payload
    else:
        try:
            payload = msg.get_content()
        except Exception:
            payload = ""
        if msg.get_content_type() == "text/plain":
            plain = payload
        elif msg.get_content_type() == "text/html":
            html = payload

    if plain:
        return cleanup_body(plain)
    elif html:
        converted = html_to_markdown(html)
        return cleanup_body(converted)
    return ""


def extract_attachments(msg, attachment_dir: Path) -> list[str]:
    """
    Save attachments into attachment_dir.
    Returns a list of saved filenames (not full paths).
    """
    saved: list[str] = []

    if not msg.is_multipart():
        return saved

    attachment_dir.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in disposition.lower():
            continue

        filename = part.get_filename()
        if not filename:
            continue

        # Sanitize filename
        safe_name = re.sub(r"[^\w.\- ]", "_", filename).strip()
        if not safe_name:
            continue

        dest = attachment_dir / safe_name

        # Avoid overwriting if duplicate filename
        counter = 1
        stem = dest.stem
        suffix = dest.suffix
        while dest.exists():
            dest = attachment_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            payload = part.get_payload(decode=True)
            if payload:
                dest.write_bytes(payload)
                saved.append(dest.name)
        except Exception:
            continue

    return saved


def append_vault_log(md_dir: Path, message: str) -> None:
    """Append a timestamped line to the vault-internal ingest log."""
    log_path = md_dir / LOG_FILENAME
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"- `{timestamp}` {message}\n"

    if not log_path.exists():
        log_path.write_text(
            "# Email Ingest Log\n\nThis file is auto-generated by eml_to_markdown.py.\n\n",
            encoding="utf-8",
        )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

def convert_one(
    eml_path: Path,
    md_dir: Path,
    attachment_base_dir: Path,
    index: dict[str, str],
) -> tuple[Path | None, str]:
    """
    Convert a single .eml file to a Markdown note.

    Returns (md_path, status) where status is one of:
      "created"   - new note written
      "skipped"   - already in index (duplicate)
      "error"     - exception occurred
    """
    try:
        with eml_path.open("rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
    except Exception as exc:
        return None, f"error reading {eml_path.name}: {exc}"

    # --- Deduplication via Message-ID ---
    message_id = str(msg.get("Message-ID", "")).strip()
    if not message_id:
        # Fall back to a synthetic ID based on file stem if header is absent
        message_id = f"synthetic:{eml_path.stem}"

    if message_id in index:
        return None, f"skipped (duplicate) {eml_path.name}"

    # --- Extract headers ---
    subject = str(msg.get("Subject", "")).strip()
    sender  = str(msg.get("From", "")).strip()
    to      = str(msg.get("To", "")).strip()
    date    = str(msg.get("Date", "")).strip()

    # --- Resolve output path ---
    slug = slugify(subject or eml_path.stem)
    md_path = md_dir / f"{slug}.md"

    # Handle slug collisions (different Message-ID, same subject)
    counter = 1
    base_slug = slug
    while md_path.exists():
        md_path = md_dir / f"{base_slug}-{counter}.md"
        counter += 1

    # --- Extract body ---
    body = extract_body(msg)

    # --- Extract attachments ---
    attachment_dir = attachment_base_dir / slug
    saved_attachments = extract_attachments(msg, attachment_dir)

    # --- Build tags and project ---
    project = resolve_project(sender)
    tags = DEFAULT_TAGS.copy()
    if project:
        tags.append(project.lower().replace(" ", "-"))

    # --- Render YAML frontmatter ---
    def q(s: str) -> str:
        """Quote a string for YAML."""
        return s.replace('"', '\\"')

    tags_yaml = ", ".join(f'"{t}"' for t in tags)

    attachment_links = ""
    if saved_attachments:
        link_lines = "\n".join(f"  - \"[[{a}]]\"" for a in saved_attachments)
        attachment_links = f"attachments:\n{link_lines}\n"

    frontmatter = (
        f'---\n'
        f'type: email\n'
        f'subject: "{q(subject)}"\n'
        f'from: "{q(sender)}"\n'
        f'to: "{q(to)}"\n'
        f'date: "{q(date)}"\n'
        f'message_id: "{q(message_id)}"\n'
        f'project: "{q(project)}"\n'
        f'tags: [{tags_yaml}]\n'
        f'source: "[[{eml_path.name}]]"\n'
        f'{attachment_links}'
        f'---\n'
        f'\n'
        f'## Summary\n'
        f'\n'
        f'## Key points\n'
        f'\n'
        f'## Actions\n'
        f'\n'
    )

    if saved_attachments:
        attachment_section = "## Attachments\n\n"
        for a in saved_attachments:
            attachment_section += f"- [[{a}]]\n"
        attachment_section += "\n"
        frontmatter += attachment_section

    frontmatter += f"## Body\n\n{body}\n"

    md_path.write_text(frontmatter, encoding="utf-8")

    # --- Update index ---
    index[message_id] = md_path.name

    return md_path, "created"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) not in (3, 4):
        print("Usage: python3 eml_to_markdown.py <eml_dir> <md_dir> [<attachment_dir>]")
        print()
        print("  eml_dir        : folder containing .eml source files")
        print("  md_dir         : folder where Markdown notes are written")
        print("  attachment_dir : folder for extracted attachments")
        print("                   (defaults to <md_dir>/../Attachments)")
        sys.exit(1)

    eml_dir  = Path(sys.argv[1]).expanduser().resolve()
    md_dir   = Path(sys.argv[2]).expanduser().resolve()

    if len(sys.argv) == 4:
        attachment_base = Path(sys.argv[3]).expanduser().resolve()
    else:
        attachment_base = md_dir.parent / "Attachments"

    md_dir.mkdir(parents=True, exist_ok=True)
    attachment_base.mkdir(parents=True, exist_ok=True)

    index = load_index(md_dir)

    created_count  = 0
    skipped_count  = 0
    error_count    = 0

    for eml_path in sorted(eml_dir.glob("*.eml")):
        result_path, status = convert_one(eml_path, md_dir, attachment_base, index)

        if status.startswith("created"):
            created_count += 1
            print(f"[created]  {result_path.name}")
            append_vault_log(md_dir, f"Created `{result_path.name}` from `{eml_path.name}`")
        elif status.startswith("skipped"):
            skipped_count += 1
            print(f"[skipped]  {eml_path.name}")
        else:
            error_count += 1
            print(f"[error]    {status}", file=sys.stderr)
            append_vault_log(md_dir, f"ERROR: {status}")

    # Persist updated index
    save_index(md_dir, index)

    print(f"\nDone. created={created_count}  skipped={skipped_count}  errors={error_count}")


if __name__ == "__main__":
    main()
