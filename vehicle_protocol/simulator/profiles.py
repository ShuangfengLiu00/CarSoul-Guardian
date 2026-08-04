"""Vehicle profiles for the virtual-vehicle simulator.

A ``VehicleProfile`` bundles the physical and behavioural parameters that
the time-compression engine uses to synthesise a year of telemetry:

  - **Degradation curves** — how fast battery SoH, motor wear, brake wear,
    and tyre wear evolve per 10 000 km, modulated by driving style and
    charging habits.
  - **Sensor baselines** — the nominal operating points (temperature,
    voltage, pressure) that the random-walk generator jitters around.
  - **Behaviour model** — the probability distribution over driving
    styles and the resulting safety / eco scores.

Three built-in profiles are provided:

  ===================== ============== ============== ==============
  Profile               powertrain     use-case       battery (kWh)
  ===================== ============== ============== ==============
  ``performance_ev``    pure electric  high-power EV  100
  ``family_ev``         pure electric  family EV      60
  ``hybrid``            plug-in hybrid daily commuter 18
  ===================== ============== ============== ==============
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ------------------------------------------------------------------ #
#  Degradation parameters
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class DegradationCurves:
    """Per-10 000-km degradation rates (before style modulation).

    All rates are *fractions per 10 000 km*.  The simulator multiplies
    by mileage / 10 000 and by a style multiplier to get the actual
    degradation at a given point in time.
    """

    # Battery SoH loss per 10 000 km (%). 0.8 means ~0.8 % per 10k km.
    battery_soh_per_10k: float = 0.8
    # Motor wear gain per 10 000 km (0-1). 0.03 means ~3 % per 10k km.
    motor_wear_per_10k: float = 0.03
    # Brake-pad wear gain per 10 000 km (0-1).
    brake_wear_per_10k: float = 0.10
    # Tyre-tread wear gain per 10 000 km (0-1).
    tire_wear_per_10k: float = 0.075
    # Suspension health loss per 10 000 km (0-100).
    suspension_loss_per_10k: float = 2.0

    # Fast-charge stress multiplier: extra SoH loss when fast_charge_ratio > 0.5.
    fast_charge_stress: float = 1.5
    # Aggressive-driving multiplier applied to all wear rates.
    aggressive_multiplier: float = 1.5


# ------------------------------------------------------------------ #
#  Sensor baselines
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class SensorBaselines:
    """Nominal operating points for random-walk generation.

    Values represent the "healthy midpoint" of each sensor; the
    simulator jitters around them with Gaussian noise and drifts them
    as components degrade.
    """

    battery_temp: float = 28.0       # °C
    motor_temp: float = 45.0         # °C
    tire_pressure: float = 2.4       # bar
    cabin_temp: float = 23.0         # °C
    # Jitter (1-sigma) for each sensor.
    battery_temp_jitter: float = 3.0
    motor_temp_jitter: float = 5.0
    tire_pressure_jitter: float = 0.08

    # Alert thresholds (the simulator pushes values toward these when
    # an anomaly scenario is active).
    battery_temp_warning: float = 45.0
    battery_temp_critical: float = 55.0
    motor_temp_warning: float = 90.0


# ------------------------------------------------------------------ #
#  Behaviour model
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class BehaviourModel:
    """Probability weights for driving styles + score baselines.

    ``style_weights`` maps style → probability.  Scores are the
    baseline values for a *balanced* driver; the simulator adjusts
    them up (eco) or down (aggressive) at run time.
    """

    style_weights: dict[str, float] = field(default_factory=lambda: {
        "eco": 0.25,
        "balanced": 0.50,
        "aggressive": 0.15,
        "sporty": 0.10,
    })
    safety_score_base: float = 85.0
    eco_score_base: float = 80.0
    # Daily distance distribution (km): (min, max, mean).
    daily_distance: tuple[float, float, float] = (5.0, 120.0, 40.0)
    # Average speed range (km/h).
    avg_speed_range: tuple[float, float] = (25.0, 70.0)


# ------------------------------------------------------------------ #
#  VehicleProfile
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class VehicleProfile:
    """A complete vehicle profile for the simulator.

    Bundles identity, powertrain specs, degradation curves, sensor
    baselines, and behaviour model into a single immutable config.
    The simulator uses this to synthesise a full lifecycle of
    TelemetryFrame data.
    """

    name: str
    brand: str
    model: str
    year: int
    fuel_type: str
    battery_capacity: float | None
    # Powertrain character (affects efficiency and temperature baselines).
    motor_efficiency_new: float  # 0-1, design efficiency at zero wear
    # Degradation / sensor / behaviour sub-configs.
    degradation: DegradationCurves
    sensors: SensorBaselines
    behaviour: BehaviourModel
    # Default fast-charge ratio for the profile (0 = all slow, 1 = all fast).
    default_fast_charge_ratio: float = 0.3


# ------------------------------------------------------------------ #
#  Built-in profiles
# ------------------------------------------------------------------ #
PERFORMANCE_EV = VehicleProfile(
    name="performance_ev",
    brand="Tesla",
    model="Model S Plaid",
    year=2025,
    fuel_type="electric",
    battery_capacity=100.0,
    motor_efficiency_new=0.96,
    degradation=DegradationCurves(
        battery_soh_per_10k=1.0,   # high-power → faster battery wear
        motor_wear_per_10k=0.035,
        brake_wear_per_10k=0.08,   # regen braking saves pads
        tire_wear_per_10k=0.12,    # high torque → tyre wear
        suspension_loss_per_10k=2.5,
        fast_charge_stress=1.6,
        aggressive_multiplier=1.6,
    ),
    sensors=SensorBaselines(
        battery_temp=30.0,         # performance pack runs warmer
        motor_temp=50.0,
        battery_temp_jitter=4.0,
    ),
    behaviour=BehaviourModel(
        style_weights={"eco": 0.15, "balanced": 0.45, "aggressive": 0.25, "sporty": 0.15},
        safety_score_base=82.0,
        eco_score_base=75.0,
        daily_distance=(5.0, 200.0, 55.0),
        avg_speed_range=(30.0, 80.0),
    ),
    default_fast_charge_ratio=0.5,
)

FAMILY_EV = VehicleProfile(
    name="family_ev",
    brand="BYD",
    model="Han EV",
    year=2025,
    fuel_type="electric",
    battery_capacity=60.0,
    motor_efficiency_new=0.94,
    degradation=DegradationCurves(
        battery_soh_per_10k=0.6,   # conservative family use → slower wear
        motor_wear_per_10k=0.025,
        brake_wear_per_10k=0.10,
        tire_wear_per_10k=0.075,
        suspension_loss_per_10k=1.5,
        fast_charge_stress=1.4,
        aggressive_multiplier=1.5,
    ),
    sensors=SensorBaselines(
        battery_temp=27.0,
        motor_temp=43.0,
    ),
    behaviour=BehaviourModel(
        style_weights={"eco": 0.35, "balanced": 0.50, "aggressive": 0.08, "sporty": 0.07},
        safety_score_base=88.0,
        eco_score_base=85.0,
        daily_distance=(3.0, 100.0, 35.0),
        avg_speed_range=(20.0, 65.0),
    ),
    default_fast_charge_ratio=0.25,
)

HYBRID = VehicleProfile(
    name="hybrid",
    brand="Toyota",
    model="Prius",
    year=2024,
    fuel_type="plug_in_hybrid",
    battery_capacity=18.0,
    motor_efficiency_new=0.93,
    degradation=DegradationCurves(
        battery_soh_per_10k=0.5,   # small battery, conservative cycling
        motor_wear_per_10k=0.03,
        brake_wear_per_10k=0.12,   # heavier car, less regen
        tire_wear_per_10k=0.08,
        suspension_loss_per_10k=2.0,
        fast_charge_stress=1.3,
        aggressive_multiplier=1.4,
    ),
    sensors=SensorBaselines(
        battery_temp=26.0,
        motor_temp=48.0,
    ),
    behaviour=BehaviourModel(
        style_weights={"eco": 0.40, "balanced": 0.45, "aggressive": 0.08, "sporty": 0.07},
        safety_score_base=87.0,
        eco_score_base=88.0,
        daily_distance=(3.0, 90.0, 38.0),
        avg_speed_range=(22.0, 68.0),
    ),
    default_fast_charge_ratio=0.15,
)

# Registry of built-in profiles.
PROFILES: dict[str, VehicleProfile] = {
    "performance_ev": PERFORMANCE_EV,
    "family_ev": FAMILY_EV,
    "hybrid": HYBRID,
}


def get_profile(name: str) -> VehicleProfile:
    """Look up a built-in profile by name.

    Raises ``KeyError`` if the profile is not found.
    """
    if name not in PROFILES:
        raise KeyError(
            f"Unknown vehicle profile '{name}'. "
            f"Available: {list(PROFILES.keys())}"
        )
    return PROFILES[name]
