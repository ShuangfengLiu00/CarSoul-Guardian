# CarSoul Guardian backend bootstrap package.
# Importing this package ensures the `ai-agent` module is importable.
from app.core.paths import ensure_paths  # noqa: F401

__all__ = ["ensure_paths"]
__version__ = "0.6.0"
