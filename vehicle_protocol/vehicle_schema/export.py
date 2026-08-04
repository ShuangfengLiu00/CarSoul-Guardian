"""JSON Schema export utilities.

Dumps all CarSoul OS vehicle-schema models as a single JSON Schema
document, so third-party tools (validators, code generators, docs) can
consume the contract without importing Python.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter

from vehicle_schema import (
    BatteryState,
    ChassisState,
    DrivingProfile,
    ImpactRef,
    LifecycleEvent,
    MotorState,
    TelemetryFrame,
    VehicleIdentity,
)
from vehicle_schema.version import SCHEMA_VERSION

# All models to include in the exported schema bundle.
_SCHEMA_MODELS = {
    "VehicleIdentity": VehicleIdentity,
    "BatteryState": BatteryState,
    "MotorState": MotorState,
    "ChassisState": ChassisState,
    "DrivingProfile": DrivingProfile,
    "ImpactRef": ImpactRef,
    "LifecycleEvent": LifecycleEvent,
    "TelemetryFrame": TelemetryFrame,
}


def export_model_schema(model_name: str) -> dict[str, Any]:
    """Return the JSON Schema for a single named model."""
    model_cls = _SCHEMA_MODELS[model_name]
    return TypeAdapter(model_cls).json_schema()


def export_all_schemas() -> dict[str, Any]:
    """Return a bundled JSON Schema document for all models.

    The output is a ``$defs``-style document with the schema version
    embedded, suitable for writing to ``schema-v1.json``.
    """
    definitions: dict[str, Any] = {}
    for name, model_cls in _SCHEMA_MODELS.items():
        definitions[name] = TypeAdapter(model_cls).json_schema()

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CarSoul OS Vehicle Schema",
        "version": SCHEMA_VERSION,
        "description": "Public data standard for the CarSoul OS vehicle protocol layer.",
        "$defs": definitions,
    }


def export_to_file(path: str) -> str:
    """Write the full schema bundle to *path* as JSON. Returns the path."""
    bundle = export_all_schemas()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    return path
