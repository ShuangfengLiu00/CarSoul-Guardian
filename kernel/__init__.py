"""CarSoul OS Kernel — the operating-system core.

This package will eventually hold all OS-kernel subsystems:
  - ``memory_engine``  — persistent vehicle memory (event → impact)
  - ``agent_runtime``  — agent registration / routing / lifecycle
  - ``workflow_engine`` — StateGraph + DAG orchestration
  - ``governance``      — permissions / sandbox / version / MCP registry

Currently only ``memory_engine`` is implemented (Step 4 of the V1.0 plan).
"""
