"""Vehicle digital twin — aggregates component twins into a unified model.

The VehicleTwin is the top-level digital twin that:
  1. Holds BatteryTwin, MotorTwin, and ChassisTwin instances
  2. Dispatches TelemetryFrame data to each component twin
  3. Computes an **explainable soul-score** from component health

The soul-score is derived from component health, not computed as a simple
average.  Each deduction is traceable to a specific component and metric,
making the score fully explainable:

    soul_score = 100 - sum(all component deductions)

The score is also weighted by component importance:
  - Battery: 35% (most critical for EVs)
  - Motor: 30% (drivetrain core)
  - Chassis: 35% (safety-critical wear items)

But the **deductions** remain per-component, so every point lost can be
traced back to its source.

Data flow
---------
::

    Simulator → TelemetryFrame stream
        │
        ├── VehicleTwin.ingest(frame)
        │     ├── BatteryTwin.ingest(frame)  → StateTransition?
        │     ├── MotorTwin.ingest(frame)    → StateTransition?
        │     └── ChassisTwin.ingest(frame)  → StateTransition?
        │
        └── VehicleTwin.soul_score()
              ├── BatteryTwin.health_result()  → ComponentHealthResult
              ├── MotorTwin.health_result()    → ComponentHealthResult
              └── ChassisTwin.health_result()  → ComponentHealthResult
              → SoulScoreResult (explainable)
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterator

from vehicle_schema import TelemetryFrame

from digital_twin.component_model.base import (
    ComponentHealthResult,
    HealthDeduction,
    SoulScoreResult,
    StateTransition,
)
from digital_twin.component_model.battery_twin import BatteryTwin
from digital_twin.component_model.chassis_twin import ChassisTwin
from digital_twin.component_model.motor_twin import MotorTwin

# Component weights for soul-score calculation.
_COMPONENT_WEIGHTS = {
    "battery": 0.35,
    "motor": 0.30,
    "chassis": 0.35,
}

# Score → grade mapping.
_GRADE_THRESHOLDS = [
    (95, "legendary", "传奇状态"),
    (80, "excellent", "优秀状态"),
    (60, "normal", "正常状态"),
    (0, "risk", "风险状态"),
]


class VehicleTwin:
    """The aggregate digital twin for a vehicle.

    Aggregates BatteryTwin, MotorTwin, and ChassisTwin into a unified
    model.  Ingests TelemetryFrame data from the simulator and produces
    explainable soul-score results.

    Parameters
    ----------
    vin : str, optional
        The vehicle identification number. Set from the first ingested frame.
    has_battery : bool, optional
        Whether the vehicle has a battery (EV/hybrid). Default True.
    """

    def __init__(
        self,
        vin: str | None = None,
        has_battery: bool = True,
    ) -> None:
        self.vin = vin
        self.has_battery = has_battery

        # Component twins.
        self.battery: BatteryTwin | None = BatteryTwin() if has_battery else None
        self.motor: MotorTwin = MotorTwin()
        self.chassis: ChassisTwin = ChassisTwin()

        # Ingestion metadata.
        self._frames_ingested: int = 0
        self._all_transitions: list[StateTransition] = []
        self._last_ts: datetime | None = None
        self._mileage: float = 0.0

    # ------------------------------------------------------------------ #
    #  Ingestion
    # ------------------------------------------------------------------ #
    def ingest(self, frame: TelemetryFrame) -> list[StateTransition]:
        """Ingest a TelemetryFrame and dispatch to all component twins.

        Returns a list of StateTransitions that occurred during this
        ingestion (may be empty if no state changed).
        """
        if self.vin is None:
            self.vin = frame.vin

        self._frames_ingested += 1
        self._last_ts = frame.ts
        self._mileage = frame.mileage

        transitions: list[StateTransition] = []

        if self.battery is not None:
            t = self.battery.ingest(frame)
            if t is not None:
                transitions.append(t)

        t = self.motor.ingest(frame)
        if t is not None:
            transitions.append(t)

        t = self.chassis.ingest(frame)
        if t is not None:
            transitions.append(t)

        self._all_transitions.extend(transitions)
        return transitions

    def ingest_stream(
        self,
        frames: Iterator[TelemetryFrame] | list[TelemetryFrame],
    ) -> list[list[StateTransition]]:
        """Ingest a stream of TelemetryFrames.

        Returns a list of transition lists, one per frame (may contain
        empty lists for frames where no transition occurred).
        """
        all_transitions: list[list[StateTransition]] = []
        for frame in frames:
            all_transitions.append(self.ingest(frame))
        return all_transitions

    # ------------------------------------------------------------------ #
    #  Soul-score (the explainable aggregate)
    # ------------------------------------------------------------------ #
    def soul_score(self) -> SoulScoreResult:
        """Compute the explainable soul-score from component health.

        The score is a weighted average of component scores, but the
        deductions list preserves full traceability: every point lost
        is linked to a specific component, metric, and threshold.
        """
        component_results: dict[str, ComponentHealthResult] = {}
        all_deductions: list[HealthDeduction] = []

        if self.battery is not None:
            result = self.battery.health_result()
            component_results["battery"] = result
            all_deductions.extend(result.deductions)

        result = self.motor.health_result()
        component_results["motor"] = result
        all_deductions.extend(result.deductions)

        result = self.chassis.health_result()
        component_results["chassis"] = result
        all_deductions.extend(result.deductions)

        # Compute weighted score from component scores.
        total_weight = 0.0
        weighted_sum = 0.0
        component_scores: dict[str, float] = {}

        for name, weight in _COMPONENT_WEIGHTS.items():
            if name in component_results:
                score = component_results[name].score
                component_scores[name] = round(score, 1)
                weighted_sum += score * weight
                total_weight += weight

        if total_weight > 0:
            score = weighted_sum / total_weight
        else:
            score = 100.0

        score = max(0.0, min(100.0, score))

        # Determine grade.
        grade_label = "risk"
        for threshold, label, _ in _GRADE_THRESHOLDS:
            if score >= threshold:
                grade_label = label
                break

        return SoulScoreResult(
            score=round(score, 1),
            grade=grade_label,
            component_scores=component_scores,
            deductions=all_deductions,
            transitions=list(self._all_transitions),
            ts=self._last_ts,
        )

    # ------------------------------------------------------------------ #
    #  Component accessors
    # ------------------------------------------------------------------ #
    def component_health(self, component: str) -> ComponentHealthResult | None:
        """Get the health result for a specific component."""
        if component == "battery":
            return self.battery.health_result() if self.battery else None
        if component == "motor":
            return self.motor.health_result()
        if component == "chassis":
            return self.chassis.health_result()
        return None

    def all_transitions(self) -> list[StateTransition]:
        """Return all state transitions across all components."""
        return list(self._all_transitions)

    def transitions_for(self, component: str) -> list[StateTransition]:
        """Return transitions for a specific component."""
        return [t for t in self._all_transitions if t.component == component]

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #
    @property
    def frames_ingested(self) -> int:
        """Total number of TelemetryFrames ingested."""
        return self._frames_ingested

    @property
    def mileage(self) -> float:
        """Latest mileage from the ingested frames."""
        return self._mileage

    @property
    def last_ts(self) -> datetime | None:
        """Timestamp of the last ingested frame."""
        return self._last_ts

    def to_dict(self) -> dict:
        """Serialise the twin state to a dictionary (for API responses)."""
        score = self.soul_score()
        return {
            "vin": self.vin,
            "mileage": self._mileage,
            "frames_ingested": self._frames_ingested,
            "last_ts": self._last_ts.isoformat() if self._last_ts else None,
            "soul_score": score.score,
            "grade": score.grade,
            "component_scores": score.component_scores,
            "component_states": {
                name: result.state
                for name, result in {
                    "battery": self.battery.health_result() if self.battery else None,
                    "motor": self.motor.health_result(),
                    "chassis": self.chassis.health_result(),
                }.items()
                if result is not None
            },
            "deductions": [
                {
                    "component": d.component,
                    "metric": d.metric,
                    "value": d.value,
                    "threshold": d.threshold,
                    "points": d.points,
                    "reason": d.reason,
                }
                for d in score.deductions
            ],
            "transitions": [
                {
                    "component": t.component,
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "ts": t.ts.isoformat() if t.ts else None,
                    "reason": t.reason,
                }
                for t in self._all_transitions
            ],
        }


# ------------------------------------------------------------------ #
#  Factory: create VehicleTwin from a simulator stream
# ------------------------------------------------------------------ #
def create_vehicle_twin_from_simulator(
    frames: list[TelemetryFrame],
    vin: str | None = None,
) -> VehicleTwin:
    """Create a VehicleTwin by ingesting a list of TelemetryFrames.

    This is the primary integration point between the simulator and the
    digital twin: the simulator produces frames, and this function creates
    a fully-populated twin.

    Parameters
    ----------
    frames : list[TelemetryFrame]
        Telemetry frames from the simulator.
    vin : str, optional
        VIN override. Auto-detected from the first frame if not provided.

    Returns
    -------
    VehicleTwin
        A vehicle twin with all frames ingested.

    Example
    -------
    ::

        from simulator import create_virtual_vehicle
        from digital_twin.component_model import create_vehicle_twin_from_simulator

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)
        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()
        print(f"Soul Score: {score.score} ({score.grade})")
        for d in score.deductions:
            print(f"  -{d.points} pts: {d.reason}")
    """
    # Detect if the vehicle has a battery from the first frame.
    has_battery = frames[0].battery is not None if frames else True

    twin = VehicleTwin(vin=vin, has_battery=has_battery)
    twin.ingest_stream(frames)
    return twin
