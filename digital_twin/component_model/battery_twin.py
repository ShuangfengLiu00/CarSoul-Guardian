"""Battery component digital twin — state machine for battery health.

The BatteryTwin tracks the battery's state-of-health (SoH), temperature,
charge cycles, and fast-charge stress.  It transitions through four
states based on configurable thresholds:

    normal → degrading → warning → critical

State transition logic:
  - **degrading**: SoH drops below 90% or temperature exceeds warning threshold
  - **warning**: SoH drops below 75% or temperature exceeds critical threshold
  - **critical**: SoH drops below 55% or temperature persistently extreme

Each health deduction is explainable: the metric value, the threshold
that was crossed, and the points deducted are all recorded.
"""
from __future__ import annotations

from datetime import datetime

from vehicle_schema import BatteryState, ComponentStatus, TelemetryFrame

from digital_twin.component_model.base import (
    ComponentHealthResult,
    ComponentTwin,
    HealthDeduction,
    StateTransition,
)


class BatteryTwin(ComponentTwin):
    """Digital twin for the battery subsystem.

    Parameters
    ----------
    soh_warning : float
        SoH (%) below which the battery is "degrading". Default 90.
    soh_danger : float
        SoH (%) below which the battery is "warning". Default 75.
    soh_critical : float
        SoH (%) below which the battery is "critical". Default 55.
    temp_warning : float
        Temperature (°C) above which the battery is "degrading". Default 45.
    temp_critical : float
        Temperature (°C) above which the battery is "warning". Default 55.
    """

    component_name = "battery"

    def __init__(
        self,
        soh_warning: float = 90.0,
        soh_danger: float = 75.0,
        soh_critical: float = 55.0,
        temp_warning: float = 45.0,
        temp_critical: float = 55.0,
    ) -> None:
        super().__init__()
        self.soh_warning = soh_warning
        self.soh_danger = soh_danger
        self.soh_critical = soh_critical
        self.temp_warning = temp_warning
        self.temp_critical = temp_critical

        # Latest observed values.
        self.soh: float = 100.0
        self.temperature: float = 25.0
        self.peak_temperature: float = 25.0       # historical max (thermal stress is permanent)
        self.charge_cycles: int = 0
        self.fast_charge_ratio: float = 0.0
        self.soc: float | None = None

    def ingest(self, frame: TelemetryFrame) -> StateTransition | None:
        """Ingest a telemetry frame and evolve the battery state."""
        if frame.battery is None:
            return None

        self.last_ts = frame.ts
        b: BatteryState = frame.battery
        self.soh = b.soh
        self.temperature = b.temperature
        if b.temperature > self.peak_temperature:
            self.peak_temperature = b.temperature
        self.charge_cycles = b.charge_cycles
        self.fast_charge_ratio = b.fast_charge_ratio
        self.soc = b.soc

        # Determine the target state based on current metrics.
        new_state = self._evaluate_state()

        return self._transition_to(
            new_state,
            frame.ts,
            self._transition_reason(new_state),
        )

    def _evaluate_state(self) -> ComponentStatus:
        """Determine the target state from current metrics."""
        if self.soh < self.soh_critical or self.temperature > self.temp_critical + 5:
            return "critical"
        if self.soh < self.soh_danger or self.temperature > self.temp_critical:
            return "warning"
        if self.soh < self.soh_warning or self.temperature > self.temp_warning:
            return "degrading"
        return "normal"

    def _transition_reason(self, new_state: ComponentStatus) -> str:
        """Generate a human-readable reason for the state transition."""
        if new_state == "critical":
            if self.soh < self.soh_critical:
                return f"SoH={self.soh:.1f}% < {self.soh_critical}% (critical threshold)"
            return f"Temperature={self.temperature:.1f}°C > {self.temp_critical + 5}°C (critical)"
        if new_state == "warning":
            if self.soh < self.soh_danger:
                return f"SoH={self.soh:.1f}% < {self.soh_danger}% (danger threshold)"
            return f"Temperature={self.temperature:.1f}°C > {self.temp_critical}°C (critical temp)"
        if new_state == "degrading":
            if self.soh < self.soh_warning:
                return f"SoH={self.soh:.1f}% < {self.soh_warning}% (warning threshold)"
            return f"Temperature={self.temperature:.1f}°C > {self.temp_warning}°C (warning temp)"
        return "Metrics within normal range"

    def health_result(self) -> ComponentHealthResult:
        """Return the current battery health with explainable deductions."""
        deductions: list[HealthDeduction] = []

        # SoH deduction: linear scale from 100→0 as SoH goes 100→50.
        if self.soh < 100:
            soh_penalty = (100 - self.soh) * 0.8  # up to 40 points
            deductions.append(HealthDeduction(
                component="battery",
                metric="soh",
                value=round(self.soh, 2),
                threshold=self.soh_warning,
                points=round(soh_penalty, 1),
                reason=f"SoH={self.soh:.1f}% — battery health below 100%",
            ))

        # Temperature deduction: penalty for thermal stress (uses peak
        # temperature, not current, because thermal damage is permanent
        # — the state machine is one-way, so the health score must not
        # "self-heal" when temperature drops back below the threshold).
        if self.peak_temperature > self.temp_warning:
            temp_excess = self.peak_temperature - self.temp_warning
            temp_penalty = min(20, temp_excess * 1.5)
            deductions.append(HealthDeduction(
                component="battery",
                metric="temperature",
                value=round(self.peak_temperature, 2),
                threshold=self.temp_warning,
                points=round(temp_penalty, 1),
                reason=f"Peak temperature={self.peak_temperature:.1f}°C > {self.temp_warning}°C warning threshold (thermal stress retained)",
            ))

        # Fast-charge stress deduction.
        if self.fast_charge_ratio > 0.5:
            fc_penalty = (self.fast_charge_ratio - 0.5) * 20  # up to 10 points
            deductions.append(HealthDeduction(
                component="battery",
                metric="fast_charge_ratio",
                value=round(self.fast_charge_ratio, 3),
                threshold=0.5,
                points=round(fc_penalty, 1),
                reason=f"Fast-charge ratio={self.fast_charge_ratio:.1%} > 50% — accelerated wear",
            ))

        total_penalty = sum(d.points for d in deductions)
        score = self._clamp_score(100 - total_penalty)

        return ComponentHealthResult(
            component=self.component_name,
            score=score,
            state=self.state,
            deductions=deductions,
        )
