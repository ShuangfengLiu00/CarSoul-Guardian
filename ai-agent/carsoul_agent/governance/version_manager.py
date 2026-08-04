"""Version Manager — Agent 版本管理 (§3.2 Versioning).

Implements the versioning lifecycle for the Governance Architecture.
Every agent release moves through a controlled pipeline:

    DEVELOPMENT → CANARY → STABLE → DEPRECATED → RETIRED

  - **DEVELOPMENT** — 内部开发中，不可对外提供服务。
  - **CANARY**      — 灰度测试，按 ``canary_percentage`` 比例分流流量。
  - **STABLE**      — 正式发布，全量对外提供服务。
  - **DEPRECATED**  — 已废弃但仍可用，提示用户尽快迁移。
  - **RETIRED**     — 已下线，不再可用。

The manager tracks the full version history per agent, supports
promotion / deprecation operations, and exposes ``get_current`` to
resolve the active version at runtime.

This mirrors the pattern used by ``registry.py``: a dataclass plus a
central manager with lookup helpers and a singleton instance seeded by
``register_agent_versions()``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """Agent version lifecycle states (§3.2)."""

    DEVELOPMENT = "development"  # 内部开发中
    CANARY = "canary"            # 灰度测试
    STABLE = "stable"            # 正式发布
    DEPRECATED = "deprecated"    # 已废弃
    RETIRED = "retired"          # 已下线


# Priority order for selecting the "current" version.
# Higher index = higher priority for ``get_current``.
_STATUS_PRIORITY: dict[VersionStatus, int] = {
    VersionStatus.RETIRED: 0,
    VersionStatus.DEPRECATED: 1,
    VersionStatus.DEVELOPMENT: 2,
    VersionStatus.CANARY: 3,
    VersionStatus.STABLE: 4,
}


@dataclass
class AgentVersion:
    """Version metadata for a single agent release (§3.2 data structure).

    Mirrors the version schema:

        {
          "agent_id": "powertrain_expert",
          "version": "v1.1",
          "status": "canary",
          "release_notes": "改进SOH预测精度",
          "canary_percentage": 10,
          "parent_version": "v1.0"
        }
    """

    agent_id: str
    version: str  # e.g. "v1.0"
    status: VersionStatus = VersionStatus.STABLE
    release_notes: str = ""
    canary_percentage: int = 0  # Canary traffic share 0-100.
    released_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_version: str | None = None  # Previous version this one builds on.

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "status": self.status.value,
            "release_notes": self.release_notes,
            "canary_percentage": self.canary_percentage,
            "released_at": self.released_at,
            "parent_version": self.parent_version,
        }


class VersionManager:
    """Central manager for agent version history and promotion.

    Provides:
      - Version registration with full lifecycle metadata.
      - ``get_current`` to resolve the active version at runtime
        (prefers STABLE, then CANARY).
      - Promotion operations: ``promote_to_canary``, ``promote_to_stable``.
      - Deprecation: ``deprecate`` to mark a version as legacy.
    """

    def __init__(self) -> None:
        # agent_id → list of AgentVersion (insertion order = chronological).
        self._versions: dict[str, list[AgentVersion]] = {}

    # ---- Registration ------------------------------------------------
    def register_version(
        self,
        agent_id: str,
        version: str,
        status: VersionStatus = VersionStatus.STABLE,
        release_notes: str = "",
        canary_percentage: int = 0,
        parent_version: str | None = None,
    ) -> AgentVersion:
        """Register a new version for an agent.

        If the exact (agent_id, version) pair already exists it is
        overwritten — this allows updating metadata for a pre-registered
        version.
        """
        ver = AgentVersion(
            agent_id=agent_id,
            version=version,
            status=status,
            release_notes=release_notes,
            canary_percentage=canary_percentage,
            parent_version=parent_version,
        )
        versions = self._versions.setdefault(agent_id, [])
        # Replace if the same version string already exists.
        for i, existing in enumerate(versions):
            if existing.version == version:
                versions[i] = ver
                logger.info(
                    "Version updated: %s %s (%s)", agent_id, version, status.value
                )
                return ver
        versions.append(ver)
        logger.info(
            "Version registered: %s %s (%s)", agent_id, version, status.value
        )
        return ver

    # ---- Lookup ------------------------------------------------------
    def get_current(self, agent_id: str) -> AgentVersion | None:
        """Return the current active version for an agent.

        Selection priority: STABLE > CANARY > DEVELOPMENT > DEPRECATED.
        RETIRED versions are never returned. Among equal-priority
        versions the most recently registered one wins.
        """
        versions = self._versions.get(agent_id, [])
        if not versions:
            return None
        # Filter out retired versions.
        candidates = [v for v in versions if v.status != VersionStatus.RETIRED]
        if not candidates:
            return None
        # Pick the highest-priority status; ties broken by latest released.
        return max(
            candidates,
            key=lambda v: (_STATUS_PRIORITY.get(v.status, 0), v.released_at),
        )

    def get_history(self, agent_id: str) -> list[AgentVersion]:
        """Return the full version history for an agent (chronological)."""
        return list(self._versions.get(agent_id, []))

    def all_versions(self) -> list[AgentVersion]:
        """Return all registered versions across all agents."""
        return [v for versions in self._versions.values() for v in versions]

    def agent_ids(self) -> list[str]:
        """Return all agent ids that have at least one version."""
        return list(self._versions.keys())

    # ---- Promotion / deprecation ------------------------------------
    def _find_version(self, agent_id: str, version: str) -> AgentVersion | None:
        """Helper: find a specific version record."""
        for v in self._versions.get(agent_id, []):
            if v.version == version:
                return v
        return None

    def promote_to_canary(
        self, agent_id: str, version: str, percentage: int = 10
    ) -> bool:
        """Promote a version to CANARY status with a traffic percentage.

        Args:
            agent_id: The agent to promote.
            version: The version string to promote.
            percentage: Canary traffic share (0-100, clamped).

        Returns:
            True if the promotion succeeded, False if the version was
            not found.
        """
        ver = self._find_version(agent_id, version)
        if ver is None:
            logger.warning("promote_to_canary: version not found: %s %s", agent_id, version)
            return False
        percentage = max(0, min(100, percentage))
        ver.status = VersionStatus.CANARY
        ver.canary_percentage = percentage
        logger.info(
            "Version promoted to canary: %s %s (%d%%)", agent_id, version, percentage
        )
        return True

    def promote_to_stable(self, agent_id: str, version: str) -> bool:
        """Promote a version to STABLE status (full release).

        When a version becomes STABLE any previously-STABLE version of
        the same agent is automatically demoted to DEPRECATED to avoid
        two concurrent stable releases.

        Returns:
            True if the promotion succeeded, False if the version was
            not found.
        """
        ver = self._find_version(agent_id, version)
        if ver is None:
            logger.warning("promote_to_stable: version not found: %s %s", agent_id, version)
            return False
        # Demote any other currently-stable version for this agent.
        for v in self._versions.get(agent_id, []):
            if v.version != version and v.status == VersionStatus.STABLE:
                v.status = VersionStatus.DEPRECATED
                logger.info(
                    "Previous stable version deprecated: %s %s", agent_id, v.version
                )
        ver.status = VersionStatus.STABLE
        ver.canary_percentage = 100
        logger.info("Version promoted to stable: %s %s", agent_id, version)
        return True

    def deprecate(self, agent_id: str, version: str) -> bool:
        """Mark a version as DEPRECATED.

        Returns:
            True if the deprecation succeeded, False if the version was
            not found.
        """
        ver = self._find_version(agent_id, version)
        if ver is None:
            logger.warning("deprecate: version not found: %s %s", agent_id, version)
            return False
        ver.status = VersionStatus.DEPRECATED
        logger.info("Version deprecated: %s %s", agent_id, version)
        return True

    # ---- Serialisation for API/frontend -----------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire manager for API/frontend."""
        return {
            "agent_count": len(self._versions),
            "total_versions": sum(len(v) for v in self._versions.values()),
            "agents": {
                aid: [v.to_dict() for v in versions]
                for aid, versions in self._versions.items()
            },
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
version_manager = VersionManager()


def register_agent_versions() -> None:
    """Pre-register version information for all CarSoul agents.

    Called once at startup to populate the version manager. Every agent
    starts at ``v1.0 STABLE``. A few agents also have historical
    versions registered to demonstrate the canary / deprecation flow:

      - powertrain_expert: v1.0 (stable) → v1.1 (canary 10%)
      - driving_expert:    v1.0 (stable) → v1.1 (canary 15%)
      - diagnosis:         v0.9 (deprecated) → v1.0 (stable)
    """
    # --- Agents that ship at v1.0 stable (no prior history) ---
    stable_agents = [
        "carsoul_guardian",
        "perception",
        "risk",
        "explainer",
        "service",
        "chassis_expert",
        "electrical_expert",
        "maintenance_expert",
        "judge",
    ]
    for agent_id in stable_agents:
        version_manager.register_version(
            agent_id=agent_id,
            version="v1.0",
            status=VersionStatus.STABLE,
            release_notes="初始正式版本。",
        )

    # --- powertrain_expert: v1.0 stable → v1.1 canary ---
    version_manager.register_version(
        agent_id="powertrain_expert",
        version="v1.0",
        status=VersionStatus.STABLE,
        release_notes="电池健康分析与热风险评估基线版本。",
    )
    version_manager.register_version(
        agent_id="powertrain_expert",
        version="v1.1",
        status=VersionStatus.CANARY,
        release_notes="改进SOH预测精度，新增充电策略优化能力。",
        canary_percentage=10,
        parent_version="v1.0",
    )

    # --- driving_expert: v1.0 stable → v1.1 canary ---
    version_manager.register_version(
        agent_id="driving_expert",
        version="v1.0",
        status=VersionStatus.STABLE,
        release_notes="驾驶行为分析与安全评估基线版本。",
    )
    version_manager.register_version(
        agent_id="driving_expert",
        version="v1.1",
        status=VersionStatus.CANARY,
        release_notes="新增环境碳排放影响分析能力，优化能耗模型。",
        canary_percentage=15,
        parent_version="v1.0",
    )

    # --- diagnosis: v0.9 deprecated → v1.0 stable ---
    version_manager.register_version(
        agent_id="diagnosis",
        version="v0.9",
        status=VersionStatus.DEPRECATED,
        release_notes="早期会诊版本，已被v1.0替代。",
    )
    version_manager.register_version(
        agent_id="diagnosis",
        version="v1.0",
        status=VersionStatus.STABLE,
        release_notes="重构会诊流程，集成Judge仲裁能力。",
        parent_version="v0.9",
    )

    logger.info(
        "Version manager initialised with %d agents, %d total versions",
        len(version_manager.agent_ids()),
        len(version_manager.all_versions()),
    )
