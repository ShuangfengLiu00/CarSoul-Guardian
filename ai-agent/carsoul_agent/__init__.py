"""CarSoul Guardian AI Agent package.

This is the project's independent agent layer. It is intentionally kept
separable from the backend so it can be reused by other frontends / runners.

Public surface:
    from carsoul_agent.agents import get_agent, register_agent
    from carsoul_agent.agents.carsoul_agent import CarSoulGuardianAgent
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["__version__"]
