"""Tests for the CarSoul OS Memory Engine.

Verifies the Step 4 acceptance criteria:
  1. **Persistence** — memories survive an engine restart (new connection
     to the same SQLite file).
  2. **Recall** — memories can be queried by vehicle, topic, and time.
  3. **summarize_for_agent** — produces a token-budgeted Chinese summary
     that can cite specific historical memory entries.
  4. **Simulator integration** — a simulator lifecycle can be ingested
     and the resulting summary mentions trends and correlations.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from kernel.memory_engine import (
    MemoryEngine,
    MemorySummary,
    Source,
    VehicleMemory,
    get_engine,
    reset_engine,
)


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #
@pytest.fixture
def engine():
    """A fresh in-memory engine for each test."""
    eng = MemoryEngine("sqlite:///:memory:")
    yield eng
    eng.close()


@pytest.fixture
def file_engine():
    """A file-backed engine (for persistence/restart tests)."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_memory.db")
    db_url = f"sqlite:///{db_path}"
    eng = MemoryEngine(db_url)
    yield eng, db_url
    eng.close()
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(tmpdir)


def _make_memory(
    vehicle_id="VSIM0000420000",
    event_type="fast_charge_session",
    impact_target="battery_stress",
    impact_delta=0.3,
    days_ago=0,
    source=Source.SIMULATOR,
    **payload,
):
    """Helper: build a VehicleMemory with sensible defaults."""
    from uuid import uuid4
    occurred = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return VehicleMemory.create(
        vehicle_id=vehicle_id,
        event_type=event_type,
        occurred_at=occurred,
        payload=payload if payload else {"ratio": 0.8},
        impact_target=impact_target,
        impact_delta=impact_delta,
        confidence=0.85,
        source=source,
    )


# ------------------------------------------------------------------ #
#  1. Basic remember / recall
# ------------------------------------------------------------------ #
class TestRememberRecall:
    def test_remember_returns_memory(self, engine):
        m = engine.remember(
            vehicle_id="V001",
            event_type="cooling_fault",
            payload={"temp": 52.0},
            impact_target="temperature_anomaly",
            impact_delta=0.5,
            source=Source.SIMULATOR,
        )
        assert isinstance(m, VehicleMemory)
        assert m.id is not None
        assert m.vehicle_id == "V001"
        assert m.event_type == "cooling_fault"
        assert m.impact_target == "temperature_anomaly"
        assert m.impact_delta == 0.5

    def test_remember_many(self, engine):
        memories = [_make_memory(event_type=f"event_{i}") for i in range(10)]
        count = engine.remember_many(memories)
        assert count == 10
        assert engine.count() == 10

    def test_recall_by_vehicle(self, engine):
        engine.remember("V001", "event_a")
        engine.remember("V002", "event_b")
        engine.remember("V001", "event_c")

        v1 = engine.recall("V001")
        v2 = engine.recall("V002")
        assert len(v1) == 2
        assert len(v2) == 1
        assert all(m.vehicle_id == "V001" for m in v1)

    def test_recall_by_topic(self, engine):
        engine.remember("V001", "a", impact_target="battery_stress")
        engine.remember("V001", "b", impact_target="motor_wear")
        engine.remember("V001", "c", impact_target="battery_stress")

        battery = engine.recall("V001", topic="battery_stress")
        assert len(battery) == 2
        assert all(m.impact_target == "battery_stress" for m in battery)

    def test_recall_by_event_type(self, engine):
        engine.remember("V001", "fast_charge")
        engine.remember("V001", "slow_charge")
        engine.remember("V001", "fast_charge")

        fast = engine.recall("V001", event_type="fast_charge")
        assert len(fast) == 2

    def test_recall_since(self, engine):
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(days=100)
        recent_time = now - timedelta(days=5)

        engine.remember("V001", "old_event", occurred_at=old_time)
        engine.remember("V001", "recent_event", occurred_at=recent_time)

        recent = engine.recall("V001", since=now - timedelta(days=30))
        assert len(recent) == 1
        assert recent[0].event_type == "recent_event"

    def test_recall_order_newest_first(self, engine):
        now = datetime.now(timezone.utc)
        for i in range(5):
            engine.remember(
                "V001", f"event_{i}",
                occurred_at=now - timedelta(days=5 - i),
            )
        results = engine.recall("V001")
        assert results[0].event_type == "event_4"
        assert results[-1].event_type == "event_0"

    def test_recall_limit(self, engine):
        for i in range(50):
            engine.remember("V001", f"event_{i}")
        results = engine.recall("V001", limit=10)
        assert len(results) == 10

    def test_get_memory_by_id(self, engine):
        m = engine.remember("V001", "test_event")
        fetched = engine.get_memory(m.id)
        assert fetched is not None
        assert fetched.id == m.id
        assert fetched.event_type == "test_event"

    def test_get_nonexistent_memory(self, engine):
        assert engine.get_memory("nonexistent-id") is None


# ------------------------------------------------------------------ #
#  2. Persistence — the key acceptance criterion
# ------------------------------------------------------------------ #
class TestPersistence:
    def test_memory_survives_restart(self, file_engine):
        """Acceptance: 重启后记忆仍在."""
        eng1, db_url = file_engine

        # Write memories with the first engine instance.
        eng1.remember(
            "V001", "cooling_fault",
            payload={"temp": 55.0},
            impact_target="temperature_anomaly",
            impact_delta=0.5,
            source=Source.SIMULATOR,
        )
        eng1.remember(
            "V001", "fast_charge_session",
            payload={"ratio": 0.8},
            impact_target="battery_stress",
            impact_delta=0.3,
            source=Source.SIMULATOR,
        )
        eng1.close()

        # Simulate a "restart": create a new engine pointing at the same DB file.
        eng2 = MemoryEngine(db_url)
        memories = eng2.recall("V001")

        assert len(memories) == 2
        event_types = {m.event_type for m in memories}
        assert "cooling_fault" in event_types
        assert "fast_charge_session" in event_types

        # The impact semantics survived too.
        cooling = [m for m in memories if m.event_type == "cooling_fault"][0]
        assert cooling.impact_target == "temperature_anomaly"
        assert cooling.impact_delta == 0.5
        assert cooling.payload["temp"] == 55.0

    def test_file_based_persistence(self, file_engine):
        """Verify that data is in a real file, not just in-memory."""
        eng, db_url = file_engine
        eng.remember("V001", "test_persistence")
        eng.close()

        # The DB file should exist and be non-empty.
        db_path = db_url.replace("sqlite:///", "")
        assert os.path.exists(db_path)
        assert os.path.getsize(db_path) > 0


# ------------------------------------------------------------------ #
#  3. Topics and metadata
# ------------------------------------------------------------------ #
class TestTopicsAndMetadata:
    def test_topics(self, engine):
        engine.remember("V001", "a", impact_target="battery_stress")
        engine.remember("V001", "b", impact_target="motor_wear")
        engine.remember("V001", "c", impact_target="battery_stress")
        engine.remember("V001", "d")  # no impact_target

        topics = engine.topics("V001")
        assert "battery_stress" in topics
        assert "motor_wear" in topics
        assert len(topics) == 2

    def test_count_all(self, engine):
        engine.remember("V001", "a")
        engine.remember("V002", "b")
        assert engine.count() == 2

    def test_count_by_vehicle(self, engine):
        engine.remember("V001", "a")
        engine.remember("V001", "b")
        engine.remember("V002", "c")
        assert engine.count("V001") == 2
        assert engine.count("V002") == 1

    def test_delete(self, engine):
        m = engine.remember("V001", "test")
        assert engine.count() == 1
        assert engine.delete(m.id) is True
        assert engine.count() == 0
        assert engine.delete("nonexistent") is False

    def test_delete_all_by_vehicle(self, engine):
        engine.remember("V001", "a")
        engine.remember("V001", "b")
        engine.remember("V002", "c")
        deleted = engine.delete_all("V001")
        assert deleted == 2
        assert engine.count("V001") == 0
        assert engine.count("V002") == 1


# ------------------------------------------------------------------ #
#  4. summarize_for_agent — the key innovation
# ------------------------------------------------------------------ #
class TestSummarizeForAgent:
    def test_empty_summary(self, engine):
        summary = engine.summarize_for_agent("V_EMPTY")
        assert isinstance(summary, MemorySummary)
        assert summary.memory_count == 0
        assert "暂无" in summary.text

    def test_summary_has_overview(self, engine):
        engine.remember(
            "V001", "fast_charge",
            impact_target="battery_stress",
            impact_delta=0.3,
        )
        summary = engine.summarize_for_agent("V001")
        assert summary.memory_count == 1
        assert "车辆记忆概览" in summary.text
        assert "电池应力" in summary.text

    def test_summary_mentions_topics(self, engine):
        engine.remember("V001", "a", impact_target="battery_stress")
        engine.remember("V001", "b", impact_target="motor_wear")
        summary = engine.summarize_for_agent("V001")
        assert "电池应力" in summary.text
        assert "电机磨损" in summary.text

    def test_summary_cites_specific_entries(self, engine):
        """Acceptance: 会诊意见能引用具体历史记忆条目."""
        now = datetime.now(timezone.utc)
        engine.remember(
            "V001", "fast_charge_session",
            payload={"ratio": 0.8, "month": "2026-08"},
            impact_target="battery_stress",
            impact_delta=0.3,
            occurred_at=now - timedelta(days=5),
        )
        engine.remember(
            "V001", "cooling_fault",
            payload={"peak_temp": 52.0},
            impact_target="temperature_anomaly",
            impact_delta=0.5,
            occurred_at=now - timedelta(days=3),
        )

        summary = engine.summarize_for_agent("V001")

        # The summary should reference the specific event types.
        assert "fast_charge_session" in summary.text
        assert "cooling_fault" in summary.text
        # The summary should mention the correlation.
        assert "关联" in summary.text or "相关" in summary.text

    def test_summary_token_budget(self, engine):
        """summarize_for_agent output should fit within token budget."""
        # Insert many memories to generate a long summary.
        for i in range(100):
            engine.remember(
                "V001", f"event_type_{i % 5}",
                impact_target=f"topic_{i % 3}",
                impact_delta=0.1 * i,
                occurred_at=datetime.now(timezone.utc) - timedelta(days=i),
            )

        summary = engine.summarize_for_agent("V001", token_budget=100)
        # 100 tokens ≈ 200 Chinese chars.
        assert summary.token_estimate <= 105  # small overhead
        assert summary.truncated is True

    def test_summary_not_truncated_with_budget(self, engine):
        engine.remember("V001", "single_event", impact_target="battery_stress")
        summary = engine.summarize_for_agent("V001", token_budget=500)
        assert summary.truncated is False
        assert summary.token_estimate < 500

    def test_summary_trends(self, engine):
        """Summary should detect trends (recent vs previous 30 days)."""
        now = datetime.now(timezone.utc)
        # Previous period: 1 event
        engine.remember(
            "V001", "fast_charge",
            impact_target="battery_stress",
            occurred_at=now - timedelta(days=50),
        )
        # Recent period: 5 events (500% increase)
        for i in range(5):
            engine.remember(
                "V001", "fast_charge",
                impact_target="battery_stress",
                occurred_at=now - timedelta(days=i + 1),
            )

        summary = engine.summarize_for_agent("V001")
        assert "趋势" in summary.text
        assert "上升" in summary.text

    def test_summary_correlation(self, engine):
        """Summary should detect correlations between co-occurring topics."""
        now = datetime.now(timezone.utc)
        # Both topics in the same month → correlation.
        engine.remember(
            "V001", "fast_charge",
            impact_target="charging_behavior",
            occurred_at=now - timedelta(days=5),
        )
        engine.remember(
            "V001", "battery_stress_event",
            impact_target="battery_stress",
            occurred_at=now - timedelta(days=4),
        )

        summary = engine.summarize_for_agent("V001")
        assert "关联" in summary.text or "相关" in summary.text


# ------------------------------------------------------------------ #
#  5. Source enum
# ------------------------------------------------------------------ #
class TestSource:
    def test_source_values(self):
        assert Source.SIMULATOR.value == "simulator"
        assert Source.DIAGNOSIS.value == "diagnosis"
        assert Source.USER.value == "user"
        assert Source.AGENT.value == "agent"

    def test_source_accepted_by_remember(self, engine):
        for src in Source:
            m = engine.remember("V001", "test", source=src)
            assert m.source == src.value


# ------------------------------------------------------------------ #
#  6. Singleton
# ------------------------------------------------------------------ #
class TestSingleton:
    def test_get_engine_returns_same_instance(self):
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2

    def test_reset_engine(self):
        e1 = get_engine()
        e2 = reset_engine()
        assert e1 is not e2
        assert e2 is get_engine()


# ------------------------------------------------------------------ #
#  7. Simulator integration (acceptance scenario)
# ------------------------------------------------------------------ #
class TestSimulatorIntegration:
    def test_ingest_simulator_lifecycle_and_summarize(self):
        """Full pipeline: simulator → memories → summary.

        This mirrors the demo scenario: ingest a year of simulator
        telemetry as memories, then produce a summary that cites
        specific events.
        """
        import sys
        base = r"c:\Users\Henry008\Desktop\CarSoul Guardian"
        if base not in sys.path:
            sys.path.insert(0, base)
        if (base + r"\vehicle_protocol") not in sys.path:
            sys.path.insert(0, base + r"\vehicle_protocol")

        from simulator import create_virtual_vehicle
        from simulator.scenarios import cooling_fault_scenario

        eng = MemoryEngine("sqlite:///:memory:")

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=600, scenario=cooling_fault_scenario())

        # Convert key telemetry events into memories.
        vin = sim.vin
        for i, frame in enumerate(frames):
            b = frame.battery
            if b is None:
                continue

            # Detect high-temperature events (cooling fault effect).
            # Cooling faults cause both temperature anomaly AND battery stress.
            if b.temperature > 45.0:
                eng.remember(
                    vehicle_id=vin,
                    event_type="temperature_anomaly",
                    payload={
                        "day": i,
                        "temp": b.temperature,
                        "soh": b.soh,
                    },
                    impact_target="temperature_anomaly",
                    impact_delta=round((b.temperature - 45) * 0.1, 3),
                    confidence=0.9,
                    source=Source.SIMULATOR,
                    occurred_at=frame.ts,
                )
                # High temperature also stresses the battery.
                eng.remember(
                    vehicle_id=vin,
                    event_type="thermal_stress",
                    payload={"day": i, "temp": b.temperature, "soh": b.soh},
                    impact_target="battery_stress",
                    impact_delta=round((b.temperature - 45) * 0.05, 3),
                    confidence=0.85,
                    source=Source.SIMULATOR,
                    occurred_at=frame.ts,
                )

        # The engine should have memories.
        assert eng.count(vin) > 0

        # The summary should mention temperature and battery stress.
        summary = eng.summarize_for_agent(vin)
        assert summary.memory_count > 0
        assert "温度异常" in summary.text or "电池应力" in summary.text

        # The correlation should be detected (both topics co-occur).
        assert "关联" in summary.text or "相关" in summary.text

        eng.close()

    def test_diagnosis_can_cite_memory(self):
        """Acceptance: 会诊意见能引用具体历史记忆条目.

        Simulates a diagnosis agent reading memories and producing a
        consultation that references specific past events.
        """
        eng = MemoryEngine("sqlite:///:memory:")
        vin = "VSIM0000420000"

        # Simulate memories from a cooling-fault lifecycle.
        now = datetime.now(timezone.utc)
        eng.remember(
            vehicle_id=vin,
            event_type="fast_charge_session",
            payload={"month": "2026-08", "ratio": 0.8, "count": 12},
            impact_target="battery_stress",
            impact_delta=0.3,
            confidence=0.85,
            source=Source.SIMULATOR,
            occurred_at=now - timedelta(days=10),
        )
        eng.remember(
            vehicle_id=vin,
            event_type="cooling_fault",
            payload={"peak_temp": 52.0, "duration_days": 18},
            impact_target="temperature_anomaly",
            impact_delta=0.5,
            confidence=0.9,
            source=Source.SIMULATOR,
            occurred_at=now - timedelta(days=5),
        )

        # A diagnosis agent reads the summary.
        summary = eng.summarize_for_agent(vin)

        # The summary should contain enough detail for the agent to cite
        # specific events in its consultation.
        assert "fast_charge_session" in summary.text
        assert "cooling_fault" in summary.text
        assert "关联" in summary.text or "相关" in summary.text

        # The agent can also recall specific memories directly.
        battery_memories = eng.recall(vin, topic="battery_stress")
        assert len(battery_memories) >= 1
        assert battery_memories[0].payload["ratio"] == 0.8

        eng.close()
