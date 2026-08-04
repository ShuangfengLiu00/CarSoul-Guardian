"""ActionStore SQLite persistence tests (Step 9)."""
import os
import tempfile

import pytest

from carsoul_agent.tools.guard_tools import ActionStore


@pytest.fixture
def temp_db():
    """Create a temporary SQLite file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def mem_store():
    """In-memory ActionStore for fast tests."""
    store = ActionStore(db_path=":memory:")
    yield store
    store.close()


class TestActionStoreBasics:
    """Basic ActionStore functionality."""

    def test_in_memory_store_starts_empty(self, mem_store):
        summary = mem_store.summary()
        assert summary == {
            "reminders": 0,
            "lifecycle_events": 0,
            "suggestions": 0,
            "service_orders": 0,
        }

    def test_append_reminder(self, mem_store):
        record = {
            "vehicle_id": 1,
            "level": "warning",
            "title": "电池温度偏高",
            "message": "建议停车散热",
            "created_at": "2027-01-01T00:00:00",
        }
        mem_store.append_reminder(record)
        assert len(mem_store.reminders) == 1
        assert mem_store.summary()["reminders"] == 1

    def test_append_lifecycle_event(self, mem_store):
        record = {
            "vehicle_id": 1,
            "event_type": "anomaly_detected",
            "title": "冷却系统异常",
            "detail": "冷却液泵效率下降15%",
            "recorded_at": "2027-01-01T00:00:00",
        }
        mem_store.append_lifecycle_event(record)
        assert len(mem_store.lifecycle_events) == 1

    def test_append_suggestion_with_list_field(self, mem_store):
        record = {
            "vehicle_id": 1,
            "priority": "high",
            "actions": ["检查冷却液泵", "清洗冷却流道", "检查冷却液浓度"],
            "explanation": "冷却效率下降导致温度波动",
            "written_at": "2027-01-01T00:00:00",
        }
        mem_store.append_suggestion(record)
        assert len(mem_store.suggestions) == 1

    def test_append_service_order(self, mem_store):
        record = {
            "vehicle_id": 1,
            "service_type": "manufacturer_service",
            "service_name": "电池系统检测",
            "priority": "high",
            "reason": "充电速度下降20%",
            "status": "created",
            "estimated_response": "30分钟内",
            "created_at": "2027-01-01T00:00:00",
        }
        mem_store.append_service_order(record)
        assert len(mem_store.service_orders) == 1


class TestActionStorePersistence:
    """Test SQLite persistence across restarts."""

    def test_data_survives_restart(self, temp_db):
        """Actions written to SQLite survive a process restart."""
        # Write data with store 1.
        store1 = ActionStore(db_path=temp_db)
        store1.append_reminder({
            "vehicle_id": 1,
            "level": "urgent",
            "title": "电池过热",
            "message": "立即停车",
            "created_at": "2027-06-01T12:00:00",
        })
        store1.append_lifecycle_event({
            "vehicle_id": 1,
            "event_type": "guard_intervention",
            "title": "守护介入",
            "detail": "检测到电池温度超阈值",
            "recorded_at": "2027-06-01T12:00:00",
        })
        store1.close()

        # Reopen with store 2 — data should persist.
        store2 = ActionStore(db_path=temp_db)
        store2.reload()
        assert len(store2.reminders) == 1
        assert len(store2.lifecycle_events) == 1
        assert store2.reminders[0]["title"] == "电池过热"
        assert store2.lifecycle_events[0]["event_type"] == "guard_intervention"
        store2.close()

    def test_suggestion_list_field_persisted_and_loaded(self, temp_db):
        """List fields (actions) are JSON-encoded and decoded correctly."""
        store1 = ActionStore(db_path=temp_db)
        store1.append_suggestion({
            "vehicle_id": 1,
            "priority": "medium",
            "actions": ["更换冷却液泵", "检查管路"],
            "explanation": "冷却系统检修",
            "written_at": "2027-06-01T12:00:00",
        })
        store1.close()

        store2 = ActionStore(db_path=temp_db)
        store2.reload()
        assert len(store2.suggestions) == 1
        # The actions list should be deserialized back from JSON.
        suggestion = store2.suggestions[0]
        assert isinstance(suggestion["actions"], list)
        assert "更换冷却液泵" in suggestion["actions"]
        store2.close()

    def test_clear_removes_all_data(self, temp_db):
        """clear() removes data from both memory and SQLite."""
        store = ActionStore(db_path=temp_db)
        store.append_reminder({
            "vehicle_id": 1,
            "level": "info",
            "title": "test",
            "message": "test",
            "created_at": "2027-01-01T00:00:00",
        })
        store.clear()
        assert len(store.reminders) == 0

        # Verify SQLite is also cleared.
        store.reload()
        assert len(store.reminders) == 0
        store.close()

    def test_multiple_records_across_tables(self, temp_db):
        """Multiple records in all four tables persist correctly."""
        store = ActionStore(db_path=temp_db)
        for i in range(5):
            store.append_reminder({
                "vehicle_id": i,
                "level": "info",
                "title": f"提醒{i}",
                "message": f"消息{i}",
                "created_at": f"2027-01-0{i+1}T00:00:00",
            })
            store.append_service_order({
                "vehicle_id": i,
                "service_type": "roadside_assist",
                "service_name": f"救援{i}",
                "priority": "high",
                "reason": f"原因{i}",
                "status": "created",
                "estimated_response": "30分钟内",
                "created_at": f"2027-01-0{i+1}T00:00:00",
            })
        store.close()

        store2 = ActionStore(db_path=temp_db)
        store2.reload()
        assert len(store2.reminders) == 5
        assert len(store2.service_orders) == 5
        assert store2.reminders[0]["title"] == "提醒0"
        assert store2.service_orders[4]["service_name"] == "救援4"
        store2.close()


class TestActionStoreSummary:
    """Test summary() method."""

    def test_summary_reflects_counts(self, mem_store):
        mem_store.append_reminder({
            "vehicle_id": 1, "level": "info", "title": "t",
            "message": "m", "created_at": "2027-01-01T00:00:00",
        })
        mem_store.append_reminder({
            "vehicle_id": 2, "level": "info", "title": "t2",
            "message": "m2", "created_at": "2027-01-01T00:00:00",
        })
        mem_store.append_suggestion({
            "vehicle_id": 1, "priority": "low", "actions": [],
            "explanation": "e", "written_at": "2027-01-01T00:00:00",
        })
        summary = mem_store.summary()
        assert summary["reminders"] == 2
        assert summary["suggestions"] == 1
        assert summary["lifecycle_events"] == 0
        assert summary["service_orders"] == 0
