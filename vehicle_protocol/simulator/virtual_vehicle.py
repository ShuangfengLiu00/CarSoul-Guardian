"""Virtual vehicle — the time-compression engine.

A ``VirtualVehicle`` wraps a :class:`VehicleProfile` and a random seed,
and produces a stream of :class:`TelemetryFrame` objects representing
the vehicle's lifecycle over any number of days.

The engine runs in **time-compression mode**: calling ``run(days=365)``
synthesises a full year of daily TelemetryFrame snapshots in seconds.
Each frame is a complete point-in-time state of the vehicle, with all
component states evolved according to the profile's degradation curves
and the active scenario.

Data flow
---------
::

    VirtualVehicle.run(days=365)
        │
        ├── for each day:
        │     ├── advance mileage (daily distance from behaviour model)
        │     ├── evolve component states (degradation × style × charging)
        │     ├── apply scenario effects (seasonal temp, anomalies)
        │     └── emit one TelemetryFrame
        │
        └── return list[TelemetryFrame]

Reproducibility
---------------
Same ``profile + seed + scenario`` always produces identical output.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from typing import Iterator

from vehicle_schema import (
    BatteryState,
    ChassisState,
    DrivingProfile,
    MotorState,
    TelemetryFrame,
    VehicleIdentity,
)

from simulator.profiles import VehicleProfile, get_profile
from simulator.scenarios import (
    AnomalyType,
    ScenarioConfig,
    normal_lifecycle,
    seasonal_ambient_temp,
)


class VirtualVehicle:
    """A virtual vehicle that synthesises TelemetryFrame data over time.

    Parameters
    ----------
    profile : VehicleProfile
        The vehicle profile (degradation curves, sensor baselines, etc.).
    seed : int
        Random seed for reproducibility.
    vin : str, optional
        VIN for the virtual vehicle. Auto-generated from the seed if
        not provided.
    """

    def __init__(
        self,
        profile: VehicleProfile,
        seed: int = 42,
        vin: str | None = None,
    ) -> None:
        self.profile = profile
        self.seed = seed
        self.rng = random.Random(seed)

        # Generate a deterministic VIN from the seed.
        if vin is None:
            # 17-char VIN: prefix + zero-padded seed.
            self.vin = f"VSIM{abs(seed) % 1000000:06d}00000"[:17]
        else:
            self.vin = vin

        # ---- Initial vehicle state (day 0) ----
        self.mileage: float = 0.0
        self.charge_cycles: int = 0
        self._soh: float = 100.0
        self._motor_wear: float = 0.0
        self._brake_wear: float = 0.0
        self._tire_wear: float = 0.0
        self._suspension_health: float = 100.0

        # The VehicleIdentity built from the profile.
        self.identity = VehicleIdentity(
            vin=self.vin,
            brand=profile.brand,
            model=profile.model,
            year=profile.year,
            fuel_type=profile.fuel_type,
            battery_capacity=profile.battery_capacity,
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def run(
        self,
        days: int = 365,
        scenario: ScenarioConfig | None = None,
    ) -> list[TelemetryFrame]:
        """Run the time-compression engine for *days* days.

        Produces one TelemetryFrame per day.  Same profile + seed +
        scenario always produces identical output.

        Parameters
        ----------
        days : int
            Number of days to simulate.
        scenario : ScenarioConfig, optional
            Scenario configuration.  Defaults to ``normal_lifecycle()``.

        Returns
        -------
        list[TelemetryFrame]
            One frame per simulated day, in chronological order.
        """
        if scenario is None:
            scenario = normal_lifecycle()

        frames: list[TelemetryFrame] = []
        start_date = datetime(self.profile.year, 1, 1, tzinfo=timezone.utc)

        for day_idx in range(days):
            frame = self._simulate_day(day_idx, start_date, scenario)
            frames.append(frame)

        return frames

    def run_iter(
        self,
        days: int = 365,
        scenario: ScenarioConfig | None = None,
    ) -> Iterator[TelemetryFrame]:
        """Like :meth:`run` but yields frames one at a time (streaming mode)."""
        if scenario is None:
            scenario = normal_lifecycle()

        start_date = datetime(self.profile.year, 1, 1, tzinfo=timezone.utc)
        for day_idx in range(days):
            yield self._simulate_day(day_idx, start_date, scenario)

    # ------------------------------------------------------------------ #
    #  Day-level simulation
    # ------------------------------------------------------------------ #
    def _simulate_day(
        self,
        day_idx: int,
        start_date: datetime,
        scenario: ScenarioConfig,
    ) -> TelemetryFrame:
        """Simulate a single day and return a TelemetryFrame."""
        ts = start_date + timedelta(days=day_idx)
        current_date = ts.date()
        years_elapsed = day_idx / 365.0

        # ---- 1. Advance mileage ----
        daily_dist = self._sample_daily_distance()
        road_type = scenario.road_mix.sample(self.rng)
        road_mult = self._road_multiplier(road_type)
        daily_distance = daily_dist * road_mult
        self.mileage += daily_distance

        # ---- 2. Evolve component states ----
        style = self._sample_style()
        style_mult = self._style_multiplier(style, self.profile.degradation.aggressive_multiplier)
        fast_charge_ratio = scenario.charging.ratio_at(years_elapsed)

        # Battery SoH degradation.
        deg = self.profile.degradation
        soh_loss = deg.battery_soh_per_10k * (daily_distance / 10000.0) * style_mult
        # Fast-charge stress.
        if fast_charge_ratio > 0.5:
            soh_loss *= deg.fast_charge_stress * (fast_charge_ratio - 0.5) / 0.5
        # Cell imbalance anomaly.
        cell_anom = scenario.anomaly_intensity(AnomalyType.CELL_IMBALANCE, day_idx)
        soh_loss *= (1.0 + cell_anom * 2.0)  # up to 3x degradation
        self._soh = max(0.0, self._soh - soh_loss)

        # Charge cycles (~1 per day, more with short trips).
        self.charge_cycles += max(1, int(daily_distance / 50))

        # Motor wear.
        motor_wear_gain = deg.motor_wear_per_10k * (daily_distance / 10000.0) * style_mult
        self._motor_wear = min(1.0, self._motor_wear + motor_wear_gain)

        # Brake wear.
        brake_wear_gain = deg.brake_wear_per_10k * (daily_distance / 10000.0) * style_mult
        brake_anom = scenario.anomaly_intensity(AnomalyType.BRAKE_SYSTEM_FAULT, day_idx)
        brake_wear_gain *= (1.0 + brake_anom * 2.0)
        self._brake_wear = min(1.0, self._brake_wear + brake_wear_gain)

        # Tyre wear.
        tire_wear_gain = deg.tire_wear_per_10k * (daily_distance / 10000.0) * style_mult
        self._tire_wear = min(1.0, self._tire_wear + tire_wear_gain)

        # Suspension health.
        self._suspension_health = max(
            0.0,
            self._suspension_health - deg.suspension_loss_per_10k * (daily_distance / 10000.0) * style_mult,
        )

        # ---- 3. Compute sensor values ----
        ambient = seasonal_ambient_temp(current_date) + scenario.ambient_temp_offset

        # Battery temperature (influenced by ambient + cooling anomaly).
        cooling_anom = scenario.anomaly_intensity(AnomalyType.COOLING_FAILURE, day_idx)
        battery_temp_base = self.profile.sensors.battery_temp + (ambient - 20) * 0.3
        battery_temp_drift = cooling_anom * 20.0  # up to +20°C
        battery_temp = self.rng.gauss(
            battery_temp_base + battery_temp_drift,
            self.profile.sensors.battery_temp_jitter,
        )
        battery_temp = max(-40.0, min(120.0, battery_temp))

        # Motor temperature.
        motor_overheat = scenario.anomaly_intensity(AnomalyType.MOTOR_OVERHEAT, day_idx)
        motor_temp_base = self.profile.sensors.motor_temp + style_mult * 5
        motor_temp_drift = motor_overheat * 30.0
        motor_temp = self.rng.gauss(
            motor_temp_base + motor_temp_drift,
            self.profile.sensors.motor_temp_jitter,
        )
        motor_temp = max(-40.0, min(200.0, motor_temp))

        # Tire pressure.
        tire_pressure = self.rng.gauss(
            self.profile.sensors.tire_pressure,
            self.profile.sensors.tire_pressure_jitter,
        )
        tire_pressure = max(0.0, min(5.0, tire_pressure))

        # ---- 4. Compute driving scores ----
        safety_score = self._compute_safety_score(style)
        eco_score = self._compute_eco_score(style, fast_charge_ratio)
        avg_speed = self.rng.uniform(*self.profile.behaviour.avg_speed_range)
        harsh_events = self._sample_harsh_events(style)

        # ---- 5. Build the TelemetryFrame ----
        # Battery state (only for EV/hybrid).
        battery_state = None
        if self.profile.battery_capacity is not None:
            soc = self.rng.uniform(30.0, 90.0)
            battery_state = BatteryState(
                soh=round(self._soh, 2),
                temperature=round(battery_temp, 2),
                charge_cycles=self.charge_cycles,
                fast_charge_ratio=round(fast_charge_ratio, 3),
                soc=round(soc, 1),
                status=self._battery_status(battery_temp, self._soh),
            )

        motor_state = MotorState(
            efficiency=round(self.profile.motor_efficiency_new * (1 - self._motor_wear * 0.3), 4),
            wear=round(self._motor_wear, 4),
            temperature=round(motor_temp, 2),
            status=self._component_status(self._motor_wear, motor_temp,
                                          self.profile.sensors.motor_temp_warning),
        )

        chassis_state = ChassisState(
            brake_wear=round(self._brake_wear, 4),
            tire_wear=round(self._tire_wear, 4),
            suspension_health=round(self._suspension_health, 1),
            tire_pressure=round(tire_pressure, 2),
            status=self._chassis_status(),
        )

        driving_profile = DrivingProfile(
            style=style,
            safety_score=round(safety_score, 1),
            eco_score=round(eco_score, 1),
            harsh_event_count=harsh_events,
            avg_speed=round(avg_speed, 1),
        )

        return TelemetryFrame(
            ts=ts,
            vin=self.vin,
            battery=battery_state,
            motor=motor_state,
            chassis=chassis_state,
            driving=driving_profile,
            mileage=round(self.mileage, 1),
            ambient_temp=round(ambient, 1),
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _sample_daily_distance(self) -> float:
        """Sample a daily distance from the behaviour model."""
        lo, hi, mean = self.profile.behaviour.daily_distance
        # Triangular distribution around the mean.
        return max(0.0, self.rng.triangular(lo, hi, mean))

    def _sample_style(self) -> str:
        """Sample a driving style from the behaviour model."""
        weights = self.profile.behaviour.style_weights
        styles = list(weights.keys())
        w = list(weights.values())
        return self.rng.choices(styles, weights=w)[0]

    @staticmethod
    def _style_multiplier(style: str, aggressive_mult: float) -> float:
        """Return the wear multiplier for a driving style."""
        return {
            "eco": 0.7,
            "balanced": 1.0,
            "sporty": 1.2,
            "aggressive": aggressive_mult,
        }.get(style, 1.0)

    @staticmethod
    def _road_multiplier(road_type: str) -> float:
        """Return the distance multiplier for a road type."""
        return {
            "urban": 0.8,
            "highway": 1.3,
            "suburban": 1.0,
            "mountain": 1.1,
            "rural": 1.2,
        }.get(road_type, 1.0)

    def _compute_safety_score(self, style: str) -> float:
        """Compute the safety score for the day."""
        base = self.profile.behaviour.safety_score_base
        adj = {"eco": 8, "balanced": 0, "sporty": -8, "aggressive": -18}
        score = base + adj.get(style, 0)
        # Slight degradation as components wear.
        score -= self._brake_wear * 10 + self._tire_wear * 8
        return max(0.0, min(100.0, score + self.rng.gauss(0, 2)))

    def _compute_eco_score(self, style: str, fast_charge_ratio: float) -> float:
        """Compute the eco score for the day."""
        base = self.profile.behaviour.eco_score_base
        adj = {"eco": 10, "balanced": 0, "sporty": -10, "aggressive": -20}
        score = base + adj.get(style, 0)
        # High fast-charge ratio hurts eco score.
        score -= max(0, fast_charge_ratio - 0.4) * 15
        return max(0.0, min(100.0, score + self.rng.gauss(0, 2)))

    def _sample_harsh_events(self, style: str) -> int:
        """Sample the number of harsh events for the day."""
        base = {"eco": 0, "balanced": 1, "sporty": 3, "aggressive": 6}.get(style, 1)
        return max(0, base + self.rng.randint(-1, 2))

    def _battery_status(self, temp: float, soh: float) -> str:
        """Determine the battery component status."""
        if temp > self.profile.sensors.battery_temp_critical or soh < 50:
            return "critical"
        if temp > self.profile.sensors.battery_temp_warning or soh < 70:
            return "warning"
        if soh < 85:
            return "degrading"
        return "normal"

    def _component_status(self, wear: float, temp: float, temp_warning: float) -> str:
        """Determine a generic component status from wear and temperature."""
        if wear > 0.9 or temp > temp_warning * 1.1:
            return "critical"
        if wear > 0.7 or temp > temp_warning:
            return "warning"
        if wear > 0.4:
            return "degrading"
        return "normal"

    def _chassis_status(self) -> str:
        """Determine the chassis component status."""
        if self._brake_wear > 0.85 or self._tire_wear > 0.85:
            return "critical"
        if self._brake_wear > 0.7 or self._tire_wear > 0.7:
            return "warning"
        if self._brake_wear > 0.4 or self._tire_wear > 0.4:
            return "degrading"
        return "normal"


# ------------------------------------------------------------------ #
#  Factory function
# ------------------------------------------------------------------ #
def create_virtual_vehicle(
    profile: str,
    seed: int = 42,
    vin: str | None = None,
) -> VirtualVehicle:
    """Create a virtual vehicle from a named profile.

    Parameters
    ----------
    profile : str
        Profile name. One of: ``performance_ev``, ``family_ev``, ``hybrid``.
    seed : int
        Random seed for reproducibility.
    vin : str, optional
        VIN override. Auto-generated if not provided.

    Returns
    -------
    VirtualVehicle
        A ready-to-run virtual vehicle.

    Raises
    ------
    KeyError
        If the profile name is not found.

    Example
    -------
    ::

        v = create_virtual_vehicle("family_ev", seed=42)
        frames = v.run(days=365)
        print(f"Generated {len(frames)} frames, final mileage: {frames[-1].mileage}")
    """
    return VirtualVehicle(
        profile=get_profile(profile),
        seed=seed,
        vin=vin,
    )
