import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
# LLM Configuration (satisfies the environment variable requirement)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama_local")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:e2b")

DATA_DIR = BASE_DIR / "data"
OUTBOX_DIR = BASE_DIR / "outbox"

# File paths
INBOX_FILE = DATA_DIR / "inbox.json"
PREFS_FILE = DATA_DIR / "prefs.json"
TRACE_FILE = BASE_DIR / "trace.jsonl"

# Ensure output directories exist
OUTBOX_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)