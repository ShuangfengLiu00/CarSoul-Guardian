"""CarSoul OS Memory Engine — persistent vehicle long-term memory.

The memory engine is the heart of the CarSoul OS story: it persists
**event → impact** semantic links for every vehicle, surviving restarts.
Unlike raw telemetry logs (``lifecycle_events``), memory is an
*interpretation layer* that records *what happened and what it affected*.

Example
-------
::

    from kernel.memory_engine import MemoryEngine

    engine = MemoryEngine("sqlite:///carsoul.db")

    # Record a memory (event → impact).
    engine.remember(
        vehicle_id="VSIM0000420000",
        event_type="fast_charge_session",
        payload={"ratio": 0.8, "duration_min": 35},
        impact_target="battery_stress",
        impact_delta=0.3,
        confidence=0.85,
        source="simulator",
    )

    # Recall memories for a vehicle.
    memories = engine.recall("VSIM0000420000", topic="battery")

    # Produce a token-budgeted summary for agent prompt injection.
    summary = engine.summarize_for_agent("VSIM0000420000")
    print(summary.text)   # "您 2026 年 8 月快充频次上升 40% ..."

Public API
----------
- :class:`MemoryEngine` — the main engine class
- :class:`VehicleMemory` — a single memory record
- :class:`MemorySummary` — the summariser output
- :func:`get_engine` — shared singleton accessor
"""
from kernel.memory_engine.engine import MemoryEngine, get_engine, reset_engine
from kernel.memory_engine.models import MemorySummary, Source, VehicleMemory
from kernel.memory_engine.causal_types import CAUSAL_EVENT_TYPES, get_event_template
from kernel.memory_engine.aggregator import CausalAggregator
from kernel.memory_engine.decay import DECAY_RULES, get_decay_action

__all__ = [
    "MemoryEngine",
    "VehicleMemory",
    "MemorySummary",
    "Source",
    "get_engine",
    "reset_engine",
    "CAUSAL_EVENT_TYPES",
    "get_event_template",
    "CausalAggregator",
    "DECAY_RULES",
    "get_decay_action",
]
