"""Scenario orchestration for the virtual-vehicle simulator.

Scenarios are configurable "story lines" that modulate the simulator's
output over time.  They allow a single profile to produce very different
lifecycles — e.g. a careful family EV vs. an aggressively-driven one,
or a vehicle that develops a cooling-system fault in year 2.

Scenario types
--------------
  - **ChargingHabit** — controls the fast-charge ratio over time
  - **SeasonalTemp** — modulates ambient and battery temperature by month
  - **RoadMix** — weights for urban / highway / mountain driving
  - **AnomalyInjection** — injects a component fault at a specific time
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Literal


# ------------------------------------------------------------------ #
#  Seasonal temperature
# ------------------------------------------------------------------ #
# Monthly ambient temperature baselines for a temperate climate (°C).
# Index 0 = January, 11 = December.
_SEASONAL_TEMPS: list[float] = [
    3, 5, 10, 16, 21, 25, 29, 28, 24, 18, 11, 5,
]


def seasonal_ambient_temp(d: date) -> float:
    """Return the baseline ambient temperature (°C) for a given date.

    Uses a sinusoidal interpolation around the monthly baseline so the
    temperature varies smoothly day-to-day.
    """
    month = d.month - 1
    # Blend current and next month for smooth transition.
    next_month = (month + 1) % 12
    day_of_month = d.day
    # Approximate days in month.
    days_in_month = 28 + (d.month in (1, 3, 5, 7, 8, 10, 12)) + (d.month == 2 and 0 or 2)
    frac = day_of_month / max(days_in_month, 1)
    base = _SEASONAL_TEMPS[month] * (1 - frac) + _SEASONAL_TEMPS[next_month] * frac
    return round(base, 1)


# ------------------------------------------------------------------ #
#  Charging habit
# ------------------------------------------------------------------ #
@dataclass
class ChargingHabit:
    """Controls how the fast-charge ratio evolves over the vehicle's life.

    ``base_ratio`` is the starting fast-charge fraction (0-1).
    ``drift_per_year`` is the annual change — e.g. +0.05 means the
    driver gradually fast-charges more.  Clamped to [0, 1].
    """

    base_ratio: float = 0.3
    drift_per_year: float = 0.0

    def ratio_at(self, years_elapsed: float) -> float:
        """Return the fast-charge ratio at *years_elapsed* years."""
        r = self.base_ratio + self.drift_per_year * years_elapsed
        return max(0.0, min(1.0, r))


# ------------------------------------------------------------------ #
#  Road mix
# ------------------------------------------------------------------ #
RoadType = Literal["urban", "highway", "suburban", "mountain", "rural"]


@dataclass
class RoadMix:
    """Probability weights for road types.

    Mountain driving increases brake and tyre wear; highway driving
    increases motor temperature and efficiency.
    """

    weights: dict[str, float] = field(default_factory=lambda: {
        "urban": 0.40,
        "highway": 0.25,
        "suburban": 0.20,
        "mountain": 0.05,
        "rural": 0.10,
    })

    def sample(self, rng: Any) -> str:
        """Sample a road type using the configured weights."""
        import random
        types = list(self.weights.keys())
        weights = list(self.weights.values())
        return rng.choices(types, weights=weights)[0]


# ------------------------------------------------------------------ #
#  Anomaly injection
# ------------------------------------------------------------------ #
class AnomalyType(str, Enum):
    """Supported anomaly injection types."""

    COOLING_FAILURE = "cooling_failure"       # battery cooling system degrades
    BRAKE_SYSTEM_FAULT = "brake_system_fault" # brake wear accelerates
    CELL_IMBALANCE = "cell_imbalance"         # battery SoH drops faster
    MOTOR_OVERHEAT = "motor_overheat"         # motor temperature spikes


@dataclass
class AnomalyInjection:
    """Injects a component fault starting at a specific time.

    The anomaly ramps up over ``ramp_days`` and then persists for the
    rest of the simulation (or until ``end_day`` if set).  The
    simulator applies the effect to the relevant TelemetryFrame fields.
    """

    anomaly_type: AnomalyType
    start_day: int                           # day index from simulation start
    ramp_days: int = 30                      # days to reach full effect
    end_day: int | None = None               # None = persists until end
    severity: float = 1.0                    # 0-1, effect intensity multiplier

    def is_active(self, day_index: int) -> bool:
        """Return True if the anomaly is active at *day_index*."""
        if day_index < self.start_day:
            return False
        if self.end_day is not None and day_index >= self.end_day:
            return False
        return True

    def intensity(self, day_index: int) -> float:
        """Return the anomaly intensity (0-1) at *day_index*.

        Ramps linearly from 0 to ``severity`` over ``ramp_days``.
        """
        if not self.is_active(day_index):
            return 0.0
        days_into = day_index - self.start_day
        if days_into < self.ramp_days:
            return self.severity * (days_into / max(self.ramp_days, 1))
        return self.severity


# ------------------------------------------------------------------ #
#  Scenario config
# ------------------------------------------------------------------ #
@dataclass
class ScenarioConfig:
    """Bundles all scenario parameters for a simulation run.

    Pass this to ``VirtualVehicle.run(scenario=...)`` to control the
    story line.  Defaults produce a "normal lifecycle" without anomalies.
    """

    charging: ChargingHabit = field(default_factory=ChargingHabit)
    road_mix: RoadMix = field(default_factory=RoadMix)
    anomalies: list[AnomalyInjection] = field(default_factory=list)
    # Starting ambient temperature offset (°C). 0 = use seasonal baseline.
    ambient_temp_offset: float = 0.0

    def active_anomalies(self, day_index: int) -> list[AnomalyInjection]:
        """Return all anomalies active at *day_index*."""
        return [a for a in self.anomalies if a.is_active(day_index)]

    def anomaly_intensity(self, anomaly_type: AnomalyType, day_index: int) -> float:
        """Return the combined intensity of a specific anomaly type."""
        total = 0.0
        for a in self.anomalies:
            if a.anomaly_type == anomaly_type:
                total += a.intensity(day_index)
        return min(total, 1.0)  # cap at 1.0


# ------------------------------------------------------------------ #
#  Preset scenarios
# ------------------------------------------------------------------ #
def normal_lifecycle() -> ScenarioConfig:
    """A normal lifecycle: moderate charging, no anomalies."""
    return ScenarioConfig(
        charging=ChargingHabit(base_ratio=0.3, drift_per_year=0.0),
    )


def aggressive_lifecycle() -> ScenarioConfig:
    """An aggressive lifecycle: high fast-charge, fast wear, sporty driving."""
    return ScenarioConfig(
        charging=ChargingHabit(base_ratio=0.6, drift_per_year=0.05),
        road_mix=RoadMix(weights={"urban": 0.30, "highway": 0.35, "suburban": 0.15,
                                  "mountain": 0.10, "rural": 0.10}),
    )


def cooling_fault_scenario() -> ScenarioConfig:
    """A lifecycle with a cooling-system fault developing in year 2.

    This is the "killer demo" scenario: the vehicle is healthy for the
    first year, then the battery cooling system starts degrading,
    causing temperature spikes that the agent team should detect and
    diagnose.
    """
    return ScenarioConfig(
        charging=ChargingHabit(base_ratio=0.35, drift_per_year=0.02),
        anomalies=[
            AnomalyInjection(
                anomaly_type=AnomalyType.CELL_IMBALANCE,
                start_day=400,   # ~13 months in
                ramp_days=60,
                severity=0.7,
            ),
            AnomalyInjection(
                anomaly_type=AnomalyType.COOLING_FAILURE,
                start_day=450,   # ~15 months in
                ramp_days=45,
                severity=0.8,
            ),
        ],
    )
