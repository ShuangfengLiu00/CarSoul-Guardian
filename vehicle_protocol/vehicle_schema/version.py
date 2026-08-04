"""Schema versioning (semantic versioning).

The schema follows semver:
  - MAJOR: breaking field removals or type changes
  - MINOR: backward-compatible field additions (default value required)
  - PATCH: documentation / constraint refinements

Consumers should check ``SCHEMA_VERSION`` and reject incompatible majors.
"""
from __future__ import annotations

# Human-readable version string.
SCHEMA_VERSION: str = "1.0.0"

# Tuple form for programmatic comparison: (major, minor, patch).
SCHEMA_VERSION_TUPLE: tuple[int, int, int] = (1, 0, 0)


def is_compatible(version_str: str) -> bool:
    """Return True if *version_str* is major-compatible with this schema.

    A consumer built against schema 1.x can safely read data produced by
    any 1.y producer (y >= 0).  A major bump (2.x, 3.x ...) is treated as
    incompatible — the consumer must upgrade.
    """
    try:
        major = int(version_str.split(".")[0])
    except (ValueError, IndexError):
        return False
    return major == SCHEMA_VERSION_TUPLE[0]
