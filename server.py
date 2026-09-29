"""Vercel entry point for the Inbox-to-Action Butler application."""
from pathlib import Path
import sys

# The production app lives in backend/app. Add backend to the import path so
# its existing `app.*` imports work both locally and in Vercel's Python runtime.
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
