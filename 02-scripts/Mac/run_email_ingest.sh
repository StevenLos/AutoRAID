#!/bin/zsh
# run_email_ingest.sh — Part of the AutoRAID pipeline.
# Wrapper script called by launchd to run the email ingestion pipeline.
# Edit VAULT below to match your actual Obsidian vault path.

set -euo pipefail

# -----------------------------------------------------------------------
# Configuration — edit this path to match your vault
# -----------------------------------------------------------------------
VAULT="/Users/slos/Documents/ObsidianVaults/HHG/HHG-Phase3"

# -----------------------------------------------------------------------
# Derived paths — do not edit unless you changed the vault structure
# -----------------------------------------------------------------------
ORIGINALS="$VAULT/Email/Originals"
INBOX="$VAULT/Email/Inbox"
ATTACHMENTS="$VAULT/Email/Attachments"
SCRIPT="$VAULT/Email/Scripts/eml_to_markdown.py"
LOGDIR="$VAULT/Email/Scripts/logs"

# -----------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------
mkdir -p "$LOGDIR"

/usr/bin/python3 "$SCRIPT" "$ORIGINALS" "$INBOX" "$ATTACHMENTS" \
    >> "$LOGDIR/email_ingest.log" 2>&1
