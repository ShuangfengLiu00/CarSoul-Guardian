"""Chassis component digital twin — state machine for brake/tyre/suspension.

The ChassisTwin aggregates three wear-intensive subsystems into a single
twin: brake pads, tyres, and suspension.  Each has its own wear metric,
and the twin's state is determined by the worst-performing subsystem.

State transition logic (based on the worst subsystem):
  - **degrading**: any wear > 0.3 or suspension < 80
  - **warning**: any wear > 0.6 or suspension < 60
  - **critical**: any wear > 0.85 or suspension < 40
"""
from __future__ import annotations

from vehicle_schema import ChassisState, ComponentStatus, TelemetryFrame

from digital_twin.component_model.base import (
    ComponentHealthResult,
    ComponentTwin,
    HealthDeduction,
    StateTransition,
)


class ChassisTwin(ComponentTwin):
    """Digital twin for the chassis subsystem (brakes, tyres, suspension).

    Parameters
    ----------
    wear_warning : float
        Wear level (0-1) above which a part is "degrading". Default 0.3.
    wear_danger : float
        Wear level above which a part is "warning". Default 0.6.
    wear_critical : float
        Wear level above which a part is "critical". Default 0.85.
    suspension_warning : float
        Suspension health below which it's "degrading". Default 80.
    suspension_danger : float
        Suspension health below which it's "warning". Default 60.
    tire_pressure_low : float
        Tire pressure (bar) below which it's abnormal. Default 2.0.
    """

    component_name = "chassis"

    def __init__(
        self,
        wear_warning: float = 0.3,
        wear_danger: float = 0.6,
        wear_critical: float = 0.85,
        suspension_warning: float = 80.0,
        suspension_danger: float = 60.0,
        tire_pressure_low: float = 2.0,
    ) -> None:
        super().__init__()
        self.wear_warning = wear_warning
        self.wear_danger = wear_danger
        self.wear_critical = wear_critical
        self.suspension_warning = suspension_warning
        self.suspension_danger = suspension_danger
        self.tire_pressure_low = tire_pressure_low

        # Latest observed values.
        self.brake_wear: float = 0.0
        self.tire_wear: float = 0.0
        self.suspension_health: float = 100.0
        self.tire_pressure: float | None = None
        self.min_tire_pressure: float | None = None  # historical min (under-inflation damage is permanent)

    def ingest(self, frame: TelemetryFrame) -> StateTransition | None:
        """Ingest a telemetry frame and evolve the chassis state."""
        self.last_ts = frame.ts
        c: ChassisState = frame.chassis
        self.brake_wear = c.brake_wear
        self.tire_wear = c.tire_wear
        self.suspension_health = c.suspension_health
        self.tire_pressure = c.tire_pressure
        if self.min_tire_pressure is None or c.tire_pressure < self.min_tire_pressure:
            self.min_tire_pressure = c.tire_pressure

        new_state = self._evaluate_state()

        return self._transition_to(
            new_state,
            frame.ts,
            self._transition_reason(new_state),
        )

    def _evaluate_state(self) -> ComponentStatus:
        """Determine the target state from the worst subsystem."""
        # Check for critical conditions.
        if (self.brake_wear > self.wear_critical
                or self.tire_wear > self.wear_critical
                or self.suspension_health < self.suspension_danger - 20):
            return "critical"
        # Check for warning conditions.
        if (self.brake_wear > self.wear_danger
                or self.tire_wear > self.wear_danger
                or self.suspension_health < self.suspension_danger):
            return "warning"
        # Check for degrading conditions.
        if (self.brake_wear > self.wear_warning
                or self.tire_wear > self.wear_warning
                or self.suspension_health < self.suspension_warning):
            return "degrading"
        return "normal"

    def _transition_reason(self, new_state: ComponentStatus) -> str:
        """Generate a human-readable reason for the state transition."""
        reasons = []
        if self.brake_wear > self.wear_warning:
            reasons.append(f"brake wear={self.brake_wear:.1%}")
        if self.tire_wear > self.wear_warning:
            reasons.append(f"tire wear={self.tire_wear:.1%}")
        if self.suspension_health < self.suspension_warning:
            reasons.append(f"suspension={self.suspension_health:.1f}")

        if not reasons:
            return "Metrics within normal range"
        return "Worst subsystem: " + ", ".join(reasons)

    def health_result(self) -> ComponentHealthResult:
        """Return the current chassis health with explainable deductions."""
        deductions: list[HealthDeduction] = []

        # Brake wear deduction: up to 20 points.
        if self.brake_wear > 0:
            brake_penalty = self.brake_wear * 20
            deductions.append(HealthDeduction(
                component="chassis.brake",
                metric="brake_wear",
                value=round(self.brake_wear, 4),
                threshold=self.wear_warning,
                points=round(brake_penalty, 1),
                reason=f"Brake wear={self.brake_wear:.1%} — pad replacement approaching",
            ))

        # Tire wear deduction: up to 15 points.
        if self.tire_wear > 0:
            tire_penalty = self.tire_wear * 15
            deductions.append(HealthDeduction(
                component="chassis.tire",
                metric="tire_wear",
                value=round(self.tire_wear, 4),
                threshold=self.wear_warning,
                points=round(tire_penalty, 1),
                reason=f"Tire wear={self.tire_wear:.1%} — tread depth reducing",
            ))

        # Suspension deduction.
        if self.suspension_health < 100:
            susp_penalty = (100 - self.suspension_health) * 0.15  # up to 15 points
            deductions.append(HealthDeduction(
                component="chassis.suspension",
                metric="suspension_health",
                value=round(self.suspension_health, 1),
                threshold=self.suspension_warning,
                points=round(susp_penalty, 1),
                reason=f"Suspension health={self.suspension_health:.1f}/100 — comfort degradation",
            ))

        # Tire pressure deduction (uses minimum historical pressure —
        # under-inflation damage is permanent, matching the one-way
        # state machine philosophy).
        if self.min_tire_pressure is not None and self.min_tire_pressure < self.tire_pressure_low:
            pressure_penalty = (self.tire_pressure_low - self.min_tire_pressure) * 20
            deductions.append(HealthDeduction(
                component="chassis.tire",
                metric="tire_pressure",
                value=round(self.min_tire_pressure, 2),
                threshold=self.tire_pressure_low,
                points=round(pressure_penalty, 1),
                reason=f"Min tire pressure={self.min_tire_pressure:.1f} bar < {self.tire_pressure_low} — under-inflation stress retained",
            ))

        total_penalty = sum(d.points for d in deductions)
        score = self._clamp_score(100 - total_penalty)

        return ComponentHealthResult(
            component=self.component_name,
            score=score,
            state=self.state,
            deductions=deductions,
        )
