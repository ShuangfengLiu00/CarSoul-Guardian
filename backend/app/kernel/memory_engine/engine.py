"""The memory engine — public API for vehicle long-term memory.

The :class:`MemoryEngine` wraps a :class:`MemoryStore` and provides
the three core operations defined in the V1.0 development plan:

  1. ``remember(...)`` — record an event → impact memory
  2. ``recall(...)`` — query memories by vehicle / topic / time
  3. ``summarize_for_agent(...)`` — produce a token-budgeted natural-
     language summary for prompt injection

The engine is deliberately stateless beyond the persistent store: every
call reads from / writes to SQLite, so memory survives restarts.

Singleton
---------
:func:`get_engine` returns a process-wide singleton, defaulting to an
in-memory database.  Production code should call
``get_engine(db_url="sqlite:///carsoul.db")`` once at startup.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from kernel.memory_engine.models import MemorySummary, Source, VehicleMemory
from kernel.memory_engine.store import MemoryStore
from kernel.memory_engine.summarizer import Summarizer

# Default token budget for agent summaries (~500 tokens ≈ 1000 Chinese chars).
_DEFAULT_TOKEN_BUDGET = 500


class MemoryEngine:
    """The public-facing memory engine.

    Parameters
    ----------
    db_url : str
        SQLite connection string.  Use ``"sqlite:///:memory:"`` for
        testing or ``"sqlite:///carsoul.db"`` for persistence.
    """

    def __init__(self, db_url: str = "sqlite:///:memory:") -> None:
        self._store = MemoryStore(db_url)
        self._summarizer = Summarizer()

    # ------------------------------------------------------------------ #
    #  remember — record a memory
    # ------------------------------------------------------------------ #
    def remember(
        self,
        vehicle_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        impact_target: str | None = None,
        impact_delta: float = 0.0,
        confidence: float = 1.0,
        source: str | Source = Source.AGENT,
        occurred_at: datetime | None = None,
        causality_grade: str = "correlational",
        mechanism: str | None = None,
    ) -> VehicleMemory:
        """Record a vehicle memory (event → impact).

        This is the primary *write* API.  Every significant event in a
        vehicle's lifecycle should produce a memory: simulator telemetry
        anomalies, diagnosis results, user-reported symptoms, agent
        decisions.

        Parameters
        ----------
        vehicle_id : str
            The vehicle this memory belongs to (VIN).
        event_type : str
            What happened (e.g. ``"fast_charge_session"``,
            ``"cooling_fault"``, ``"diagnosis"``).
        payload : dict, optional
            Event details as a JSON-safe dict.
        impact_target : str, optional
            What the event impacted (e.g. ``"battery_stress"``).
            ``None`` if no direct component impact.
        impact_delta : float
            Signed impact magnitude.  Positive = degradation,
            negative = improvement.
        confidence : float
            Confidence in the impact link (0.0-1.0).
        source : str | Source
            Where the memory came from.
        occurred_at : datetime, optional
            When the event happened. Defaults to now.
        causality_grade : str
            causal / correlational / insufficient_data（C-06 因果纪律）。
        mechanism : str, optional
            因果机理；causal 必填，correlational 必须为 None。

        Returns
        -------
        VehicleMemory
            The persisted memory record.
        """
        # ── C-06 因果纪律校验 ──
        if causality_grade == "causal" and not mechanism:
            raise ValueError("causal 事件必须提供 mechanism")
        if causality_grade == "correlational" and mechanism:
            raise ValueError("correlational 事件禁止提供 mechanism")

        enriched_payload = dict(payload or {})
        enriched_payload["causality_grade"] = causality_grade
        enriched_payload["mechanism"] = mechanism

        memory = VehicleMemory.create(
            vehicle_id=vehicle_id,
            event_type=event_type,
            occurred_at=occurred_at,
            payload=enriched_payload,
            impact_target=impact_target,
            impact_delta=impact_delta,
            confidence=confidence,
            source=source,
        )
        self._store.insert(memory)
        return memory

    def remember_many(self, memories: list[VehicleMemory]) -> int:
        """Batch-insert pre-constructed :class:`VehicleMemory` objects.

        Useful for ingesting a full simulator lifecycle at once.
        Returns the number of records inserted.
        """
        return self._store.insert_many(memories)

    # ------------------------------------------------------------------ #
    #  recall — query memories
    # ------------------------------------------------------------------ #
    def recall(
        self,
        vehicle_id: str,
        topic: str | None = None,
        since: datetime | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[VehicleMemory]:
        """Query memories for a vehicle.

        Parameters
        ----------
        vehicle_id : str
            The vehicle to query.
        topic : str, optional
            Filter by ``impact_target``.  Pass ``"battery_stress"`` to
            get only battery-related memories, for example.
        since : datetime, optional
            Only memories at or after this time.
        event_type : str, optional
            Filter by event type.
        limit : int
            Max records (most recent first).

        Returns
        -------
        list[VehicleMemory]
            Matching memories, newest first.
        """
        return self._store.recall(
            vehicle_id=vehicle_id,
            topic=topic,
            since=since,
            event_type=event_type,
            limit=limit,
        )

    def get_memory(self, memory_id: str) -> VehicleMemory | None:
        """Fetch a single memory by ID."""
        return self._store.get_by_id(memory_id)

    def topics(self, vehicle_id: str) -> list[str]:
        """Return the distinct impact topics for a vehicle."""
        return self._store.topics(vehicle_id)

    def count(self, vehicle_id: str | None = None) -> int:
        """Count memory records, optionally filtered by vehicle."""
        return self._store.count(vehicle_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a single memory by ID."""
        return self._store.delete(memory_id)

    def delete_all(self, vehicle_id: str | None = None) -> int:
        """Delete all memories (optionally for one vehicle). Use with care."""
        return self._store.delete_all(vehicle_id)

    # ------------------------------------------------------------------ #
    #  summarize_for_agent — the key innovation
    # ------------------------------------------------------------------ #
    def summarize_for_agent(
        self,
        vehicle_id: str,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
        since: datetime | None = None,
        agent_domain: str = "all",
    ) -> MemorySummary:
        """Produce a natural-language memory summary for agent injection.

        This is the *read* API that powers the "会诊意见能引用具体历史
        记忆条目" acceptance criterion.  The summariser:

          1. Aggregates memories by topic and time window
          2. Detects trends (e.g. "fast-charge frequency up 40%")
          3. Correlates impacts across topics
          4. Outputs Chinese text within a token budget

        Parameters
        ----------
        vehicle_id : str
            The vehicle to summarise.
        token_budget : int
            Approximate max tokens (~2 Chinese chars per token).
        since : datetime, optional
            Only consider memories from this time onward.  Defaults to
            365 days ago.
        agent_domain : str
            领域裁剪：usage / cabin / after_sales / all。

        Returns
        -------
        MemorySummary
            The summary, ready for prompt injection.
        """
        domain_filter = {
            "usage": ["battery_soh", "motor_wear", "brake_pad_wear", "battery_stress"],
            "cabin": ["driving_behavior", "fatigue_event", "comfort_setting"],
            "after_sales": ["maintenance_record", "insurance_claim", "recall_event"],
            "all": None,
        }
        relevant_targets = domain_filter.get(agent_domain)

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=365)

        memories = self.recall(vehicle_id, since=since, limit=500)
        if relevant_targets:
            memories = [m for m in memories if m.impact_target in relevant_targets]

        topics = list({m.impact_target for m in memories if m.impact_target})
        return self._summarizer.summarize(
            vehicle_id=vehicle_id,
            memories=memories,
            topics=topics,
            token_budget=token_budget,
        )

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Close the underlying store."""
        self._store.close()


# ------------------------------------------------------------------ #
#  Singleton
# ------------------------------------------------------------------ #
_engine: MemoryEngine | None = None


def get_engine(db_url: str | None = None) -> MemoryEngine:
    """Return the process-wide :class:`MemoryEngine` singleton.

    The first call initialises the engine.  Subsequent calls return the
    same instance regardless of ``db_url`` (to reset, call
    :func:`reset_engine`).

    Parameters
    ----------
    db_url : str, optional
        Connection string for the first call.  Defaults to an in-memory
        database (useful for tests, but memory is lost on exit).
    """
    global _engine
    if _engine is None:
        _engine = MemoryEngine(db_url or "sqlite:///:memory:")
    return _engine


def reset_engine(db_url: str = "sqlite:///:memory:") -> MemoryEngine:
    """Discard the current singleton and create a new one. Mainly for tests."""
    global _engine
    if _engine is not None:
        _engine.close()
    _engine = MemoryEngine(db_url)
    return _engine
