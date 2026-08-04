"""Project path resolution.

Makes the top-level `ai-agent/` folder importable as the `carsoul_agent`
Python package, so the backend can call the agent layer without coupling
AI logic into the API routes.

Works both in local dev and inside Docker (where `backend` and `ai-agent`
live under `/app`).
"""
from __future__ import annotations

import sys
from pathlib import Path

# paths.py lives at backend/app/core/paths.py
#   parents[0]=core, parents[1]=app, parents[2]=backend, parents[3]=project root
_RESOLVED = Path(__file__).resolve()
BACKEND_DIR = _RESOLVED.parents[2]                             # backend/
PROJECT_ROOT = _RESOLVED.parents[3]                            # CarSoul Guardian/
AI_AGENT_DIR = PROJECT_ROOT / "ai-agent"                       # ai-agent/
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_paths() -> None:
    """Insert the ai-agent folder onto sys.path if not already present."""
    if AI_AGENT_DIR.exists() and str(AI_AGENT_DIR) not in sys.path:
        sys.path.insert(0, str(AI_AGENT_DIR))


# Run once on import so any `from carsoul_agent...` works automatically.
ensure_paths()
