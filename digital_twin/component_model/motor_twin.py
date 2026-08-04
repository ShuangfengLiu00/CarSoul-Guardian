"""Motor component digital twin — state machine for motor/engine health.

The MotorTwin tracks efficiency, wear, and temperature.  As the vehicle
ages, motor efficiency drops and wear increases, eventually leading to
performance degradation and potential failure.

State transition logic:
  - **degrading**: wear > 0.3 or efficiency drops below 95% of design
  - **warning**: wear > 0.6 or temperature exceeds warning threshold
  - **critical**: wear > 0.85 or temperature exceeds critical threshold
"""
from __future__ import annotations

from vehicle_schema import ComponentStatus, MotorState, TelemetryFrame

from digital_twin.component_model.base import (
    ComponentHealthResult,
    ComponentTwin,
    HealthDeduction,
    StateTransition,
)


class MotorTwin(ComponentTwin):
    """Digital twin for the motor/engine subsystem.

    Parameters
    ----------
    wear_warning : float
        Wear level (0-1) above which the motor is "degrading". Default 0.3.
    wear_danger : float
        Wear level above which the motor is "warning". Default 0.6.
    wear_critical : float
        Wear level above which the motor is "critical". Default 0.85.
    temp_warning : float
        Temperature (°C) above which the motor is "warning". Default 90.
    temp_critical : float
        Temperature (°C) above which the motor is "critical". Default 120.
    """

    component_name = "motor"

    def __init__(
        self,
        wear_warning: float = 0.3,
        wear_danger: float = 0.6,
        wear_critical: float = 0.85,
        temp_warning: float = 90.0,
        temp_critical: float = 120.0,
    ) -> None:
        super().__init__()
        self.wear_warning = wear_warning
        self.wear_danger = wear_danger
        self.wear_critical = wear_critical
        self.temp_warning = temp_warning
        self.temp_critical = temp_critical

        # Latest observed values.
        self.efficiency: float = 1.0
        self.wear: float = 0.0
        self.temperature: float | None = None
        self.peak_temperature: float | None = None  # historical max (thermal stress is permanent)

    def ingest(self, frame: TelemetryFrame) -> StateTransition | None:
        """Ingest a telemetry frame and evolve the motor state."""
        self.last_ts = frame.ts
        m: MotorState = frame.motor
        self.efficiency = m.efficiency
        self.wear = m.wear
        self.temperature = m.temperature
        if self.peak_temperature is None or m.temperature > self.peak_temperature:
            self.peak_temperature = m.temperature

        new_state = self._evaluate_state()

        return self._transition_to(
            new_state,
            frame.ts,
            self._transition_reason(new_state),
        )

    def _evaluate_state(self) -> ComponentStatus:
        """Determine the target state from current metrics."""
        # Temperature-based transitions (if temperature data is available).
        if self.temperature is not None:
            if self.wear > self.wear_critical or self.temperature > self.temp_critical:
                return "critical"
            if self.wear > self.wear_danger or self.temperature > self.temp_warning:
                return "warning"
        if self.wear > self.wear_warning:
            return "degrading"
        return "normal"

    def _transition_reason(self, new_state: ComponentStatus) -> str:
        """Generate a human-readable reason for the state transition."""
        if new_state == "critical":
            if self.wear > self.wear_critical:
                return f"Wear={self.wear:.1%} > {self.wear_critical:.0%} (critical threshold)"
            return f"Temperature={self.temperature:.1f}°C > {self.temp_critical}°C (critical)"
        if new_state == "warning":
            if self.wear > self.wear_danger:
                return f"Wear={self.wear:.1%} > {self.wear_danger:.0%} (danger threshold)"
            return f"Temperature={self.temperature:.1f}°C > {self.temp_warning}°C (warning)"
        if new_state == "degrading":
            return f"Wear={self.wear:.1%} > {self.wear_warning:.0%} (warning threshold)"
        return "Metrics within normal range"

    def health_result(self) -> ComponentHealthResult:
        """Return the current motor health with explainable deductions."""
        deductions: list[HealthDeduction] = []

        # Wear deduction: up to 35 points for full wear.
        if self.wear > 0:
            wear_penalty = self.wear * 35
            deductions.append(HealthDeduction(
                component="motor",
                metric="wear",
                value=round(self.wear, 4),
                threshold=self.wear_warning,
                points=round(wear_penalty, 1),
                reason=f"Wear={self.wear:.1%} — motor degradation from usage",
            ))

        # Efficiency deduction: penalty for efficiency below design.
        if self.efficiency < 0.95:
            eff_penalty = (0.95 - self.efficiency) * 200  # up to ~10 points
            deductions.append(HealthDeduction(
                component="motor",
                metric="efficiency",
                value=round(self.efficiency, 4),
                threshold=0.95,
                points=round(eff_penalty, 1),
                reason=f"Efficiency={self.efficiency:.1%} < 95% — performance degradation",
            ))

        # Temperature deduction (uses peak temperature — thermal damage
        # is permanent, matching the one-way state machine).
        if self.peak_temperature is not None and self.peak_temperature > self.temp_warning:
            temp_excess = self.peak_temperature - self.temp_warning
            temp_penalty = min(15, temp_excess * 0.8)
            deductions.append(HealthDeduction(
                component="motor",
                metric="temperature",
                value=round(self.peak_temperature, 2),
                threshold=self.temp_warning,
                points=round(temp_penalty, 1),
                reason=f"Peak temperature={self.peak_temperature:.1f}°C > {self.temp_warning}°C — overheating stress retained",
            ))

        total_penalty = sum(d.points for d in deductions)
        score = self._clamp_score(100 - total_penalty)

        return ComponentHealthResult(
            component=self.component_name,
            score=score,
            state=self.state,
            deductions=deductions,
        )
