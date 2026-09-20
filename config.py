import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTBOX_DIR = BASE_DIR / "outbox"

# File paths
INBOX_FILE = DATA_DIR / "inbox.json"
PREFS_FILE = DATA_DIR / "prefs.json"
TRACE_FILE = BASE_DIR / "trace.jsonl"

# Ensure output directories exist
OUTBOX_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)