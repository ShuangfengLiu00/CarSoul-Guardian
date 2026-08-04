"""Pytest configuration for backend tests."""
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `import app...` works from tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a dev SQLite DB so tests never touch a real database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_carsoul.db")
