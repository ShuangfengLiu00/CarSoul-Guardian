"""Base classes for component-level digital twins.

Each component twin is a **state machine** that ingests TelemetryFrame
data and evolves its internal state.  The state machine has four levels:

    normal → degrading → warning → critical

Transitions are one-way (a component can degrade, but self-healing is
not modelled — maintenance resets are handled externally).

Every twin produces an **explainable** health result: a score from 0-100
plus a list of deductions, where each deduction is traceable to a
specific metric and threshold.  This is the key innovation over the old
``overall_score = average(subsystems)`` approach: every point lost can
be explained.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from vehicle_schema import ComponentStatus, TelemetryFrame


# ------------------------------------------------------------------ #
#  State transition record
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class StateTransition:
    """Records a state machine transition for a component.

    Attributes
    ----------
    component : str
        Component name (e.g. ``"battery"``, ``"motor"``, ``"chassis.brake"``).
    from_state : ComponentStatus
        Previous state.
    to_state : ComponentStatus
        New state.
    ts : datetime
        When the transition occurred (from the TelemetryFrame timestamp).
    reason : str
        Human-readable explanation of why the transition happened.
    """

    component: str
    from_state: ComponentStatus
    to_state: ComponentStatus
    ts: datetime
    reason: str

    @property
    def is_degradation(self) -> bool:
        """True if the transition represents a degradation."""
        order = {"normal": 0, "degrading": 1, "warning": 2, "critical": 3}
        return order[self.to_state] > order[self.from_state]


# ------------------------------------------------------------------ #
#  Explainable deduction
# ------------------------------------------------------------------ #
@dataclass(frozen=True)
class HealthDeduction:
    """A single explainable score deduction.

    Each deduction links a score penalty to a specific metric value and
    the threshold that triggered it, so the soul-score can be fully
    traced: "you lost 8 points because battery SoH is 82% (below the
    90% degrading threshold)".
    """

    component: str
    metric: str
    value: float
    threshold: float
    points: float
    reason: str


# ------------------------------------------------------------------ #
#  Component health result
# ------------------------------------------------------------------ #
@dataclass
class ComponentHealthResult:
    """The full health assessment for a single component.

    Attributes
    ----------
    component : str
        Component name.
    score : float
        Health score (0-100). 100 = perfect, 0 = end-of-life.
    state : ComponentStatus
        Current state-machine state.
    deductions : list[HealthDeduction]
        Explainable deductions that make up ``100 - score``.
    """

    component: str
    score: float
    state: ComponentStatus
    deductions: list[HealthDeduction] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """True if the component is in normal or degrading state."""
        return self.state in ("normal", "degrading")


# ------------------------------------------------------------------ #
#  Soul-score result (the explainable aggregate)
# ------------------------------------------------------------------ #
@dataclass
class SoulScoreResult:
    """The explainable soul-score for the entire vehicle.

    The soul-score is derived from component health, not computed as a
    simple average.  Each deduction is traceable to a specific component
    and metric, making the score fully explainable.
    """

    score: float
    grade: str
    component_scores: dict[str, float]
    deductions: list[HealthDeduction]
    transitions: list[StateTransition]
    ts: datetime | None = None

    @property
    def total_deduction(self) -> float:
        """Total points deducted from 100."""
        return sum(d.points for d in self.deductions)

    def deductions_for(self, component: str) -> list[HealthDeduction]:
        """Return deductions for a specific component."""
        return [d for d in self.deductions if d.component == component]


# ------------------------------------------------------------------ #
#  Abstract component twin
# ------------------------------------------------------------------ #
class ComponentTwin(ABC):
    """Base class for all component digital twins.

    A component twin is a state machine that:
      1. Ingests TelemetryFrame data
      2. Evolves its internal state (normal → degrading → warning → critical)
      3. Produces explainable health results

    Subclasses must implement:
      - ``ingest(frame)``: evolve state from a telemetry frame
      - ``health_result()``: return current health with deductions
    """

    component_name: str = "base"

    def __init__(self) -> None:
        self.state: ComponentStatus = "normal"
        self.last_ts: datetime | None = None
        self._transition_history: list[StateTransition] = []

    @abstractmethod
    def ingest(self, frame: TelemetryFrame) -> StateTransition | None:
        """Ingest a TelemetryFrame and evolve the component state.

        Returns a StateTransition if the state changed, None otherwise.
        """

    @abstractmethod
    def health_result(self) -> ComponentHealthResult:
        """Return the current health assessment with explainable deductions."""

    @property
    def transition_history(self) -> list[StateTransition]:
        """All state transitions recorded by this twin."""
        return list(self._transition_history)

    def _transition_to(
        self,
        new_state: ComponentStatus,
        ts: datetime,
        reason: str,
    ) -> StateTransition | None:
        """Attempt a state transition. Returns the transition if it happened."""
        if new_state == self.state:
            return None

        # States can only worsen (no self-healing).
        order = {"normal": 0, "degrading": 1, "warning": 2, "critical": 3}
        if order[new_state] < order[self.state]:
            return None

        transition = StateTransition(
            component=self.component_name,
            from_state=self.state,
            to_state=new_state,
            ts=ts,
            reason=reason,
        )
        self.state = new_state
        self._transition_history.append(transition)
        return transition

    @staticmethod
    def _clamp_score(score: float) -> float:
        """Clamp a score to [0, 100]."""
        return max(0.0, min(100.0, score))
