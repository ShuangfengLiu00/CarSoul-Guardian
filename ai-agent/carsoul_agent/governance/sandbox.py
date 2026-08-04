"""Sandbox Executor — 安全沙箱执行环境 (§9 Sandbox Layer).

Implements a sandboxed execution environment for the Governance
Architecture. The sandbox wraps every agent / skill call with:

  - **Tool validation** — only explicitly allowed tools may execute;
    forbidden tools are blocked outright.
  - **Data-access validation** — checks that the calling agent has the
    permission to read the requested data resource (integrates with
    ``permissions.py``).
  - **Timeout protection** — a function that runs longer than
    ``max_execution_time`` is aborted and an error is returned.
  - **Resource limits** — memory and network access flags are declared
    in ``SandboxConfig`` so the workflow engine can enforce them.

This mirrors the pattern used by ``registry.py``: a dataclass for
configuration, a manager class with validation helpers, and a singleton
instance ready for import.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable

from carsoul_agent.governance.permissions import Permission, permission_checker

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for the sandbox execution environment.

    Attributes:
        max_execution_time: Maximum wall-clock seconds a single call may run.
        max_memory_mb: Memory ceiling in megabytes (advisory).
        allowed_tools: Whitelist of tool names that may be invoked.
        forbidden_tools: Blacklist of tool names that must never run.
        network_access: Whether outbound network calls are permitted.
        file_write_access: Whether writing to the filesystem is permitted.
        description: Human-readable description of this config profile.
    """

    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 256
    allowed_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    network_access: bool = False
    file_write_access: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory_mb,
            "allowed_tools": self.allowed_tools,
            "forbidden_tools": self.forbidden_tools,
            "network_access": self.network_access,
            "file_write_access": self.file_write_access,
            "description": self.description,
        }


class SandboxExecutor:
    """安全沙箱执行环境 — 防止错误操作、数据泄露、非授权访问.

    The sandbox is the last line of defence before an agent's code
    actually runs. It validates tools, data access, and enforces a
    timeout so a misbehaving agent cannot hang the system.

    Usage::

        result, error = sandbox_executor.execute_safely(
            expert.consult,
            vehicle_state,
            tool_name="battery_health_analysis",
        )
        if error is not None:
            logger.warning("Sandbox blocked execution: %s", error)
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig(description="默认安全沙箱配置")

    # ---- Tool validation --------------------------------------------
    def validate_tool(self, tool_name: str) -> bool:
        """Return True if *tool_name* may be executed in the sandbox.

        Rules (in order):
          1. If the tool is in ``forbidden_tools`` → reject.
          2. If ``allowed_tools`` is non-empty and the tool is not in
             it → reject.
          3. Otherwise → allow.
        """
        if tool_name in self._config.forbidden_tools:
            logger.warning("Sandbox: forbidden tool blocked: %s", tool_name)
            return False
        if self._config.allowed_tools and tool_name not in self._config.allowed_tools:
            logger.warning("Sandbox: tool not in allowlist: %s", tool_name)
            return False
        return True

    # ---- Data-access validation -------------------------------------
    def validate_data_access(self, data_resource: str, agent_id: str) -> bool:
        """Return True if *agent_id* may access *data_resource*.

        Integrates with ``permission_checker`` so that the sandbox
        respects the same least-privilege model as the rest of the
        governance layer. Resources in ``Permission.FORBIDDEN`` are
        always denied.
        """
        # Never allow access to explicitly forbidden resources.
        if data_resource in Permission.FORBIDDEN:
            logger.warning(
                "Sandbox: forbidden data resource blocked: %s (agent=%s)",
                data_resource, agent_id,
            )
            return False
        # Delegate to the permission checker for the agent-level model.
        allowed = permission_checker.check(agent_id, data_resource)
        if not allowed:
            logger.warning(
                "Sandbox: data access denied: %s (agent=%s)",
                data_resource, agent_id,
            )
        return allowed

    # ---- Safe execution ---------------------------------------------
    def execute_safely(
        self,
        func: Callable[..., Any],
        *args: Any,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> tuple[Any, str | None]:
        """Execute *func* inside the sandbox.

        Args:
            func: The callable to execute.
            *args: Positional arguments forwarded to *func*.
            tool_name: Optional tool name for pre-execution validation.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            A tuple ``(result, error)``. On success *error* is ``None``;
            on timeout, violation, or exception *result* is ``None`` and
            *error* is a human-readable message.
        """
        # --- Pre-execution tool validation ---
        if tool_name is not None and not self.validate_tool(tool_name):
            return None, f"Tool '{tool_name}' is not allowed in the sandbox."

        timeout = self._config.max_execution_time
        logger.debug(
            "Sandbox: executing %s with timeout=%ds",
            tool_name or getattr(func, "__name__", "anonymous"), timeout,
        )

        # --- Execute with timeout (cross-platform via ThreadPoolExecutor) ---
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(func, *args, **kwargs)
                result = future.result(timeout=timeout)
            return result, None
        except FuturesTimeoutError:
            msg = (
                f"Execution timed out after {timeout}s"
                f" (tool={tool_name or getattr(func, '__name__', 'unknown')})."
            )
            logger.error("Sandbox: %s", msg)
            return None, msg
        except Exception as exc:  # noqa: BLE001
            msg = f"Execution failed: {type(exc).__name__}: {exc}"
            logger.error("Sandbox: %s", msg, exc_info=True)
            return None, msg

    # ---- Accessors ---------------------------------------------------
    def get_config(self) -> SandboxConfig:
        """Return the current sandbox configuration."""
        return self._config

    def update_config(self, config: SandboxConfig) -> None:
        """Replace the current sandbox configuration."""
        self._config = config
        logger.info("Sandbox config updated: timeout=%ds", config.max_execution_time)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the sandbox state for API/frontend."""
        return {
            "config": self._config.to_dict(),
            "status": "ready",
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
sandbox_executor = SandboxExecutor()
