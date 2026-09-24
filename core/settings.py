"""Paths and environment settings."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
RULES_DIR = CONFIG_DIR / "rules"
TEMPLATES_DIR = CONFIG_DIR / "templates"
SEED_DIR = ROOT / "data" / "seed"
FRONTEND_DIR = ROOT / "frontend"
RECORDS_DIR = Path(os.getenv("RECORDS_DIR", str(ROOT / "records")))

# ":memory:" rebuilds the database from the seed files on every start.
SQLITE_PATH = os.getenv("SQLITE_PATH", ":memory:")

# Optional LLM fallback for the classifier. Without a key the system runs
# fully deterministic.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en")
