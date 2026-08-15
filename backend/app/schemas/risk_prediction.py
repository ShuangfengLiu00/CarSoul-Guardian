"""Risk-prediction schemas — request/response contracts for the closed loop."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
#  Response models
# --------------------------------------------------------------------------- #
class RiskPredictionOut(BaseModel):
    """A single prediction record (without the heavy trace_log by default)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    triggered_by: str
    is_normal: bool
    predicted_level: str
    predicted_probability: int | None = None
    predicted_eta_hours: int | None = None
    primary_type: str | None = None
    root_cause: str | None = None
    trend: str | None = None
    explanation: str | None = None
    actions_hint: list[str] | None = None
    anomalies_count: int = 0
    alert_id: int | None = None
    status: str
    acknowledged_at: datetime | None = None
    actual_outcome: str | None = None
    outcome_notes: str | None = None
    accuracy: float | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class RiskPredictionDetail(RiskPredictionOut):
    """Prediction record WITH the full reasoning trace (for audit/replay)."""

    trace_log: list[dict[str, Any]] | None = None


class RiskPredictionList(BaseModel):
    items: list[RiskPredictionOut]
    total: int = 0


# --------------------------------------------------------------------------- #
#  Request models
# --------------------------------------------------------------------------- #
class RiskPredictRequest(BaseModel):
    """Optional payload for triggering a prediction."""

    triggered_by: str = Field(
        "user", description="触发来源: user | patrol | alert | scheduled"
    )


class RiskFeedbackRequest(BaseModel):
    """The loop-closing payload: what actually happened."""

    actual_outcome: str = Field(
        ...,
        description=(
            "实际处置结果: confirmed（风险确实发生）| false_alarm（误报）"
            " | no_event（未发生，多用于正常预测）| partial（部分发生）"
        ),
    )
    outcome_notes: str | None = Field(None, description="处置说明/备注")


# --------------------------------------------------------------------------- #
#  Accuracy stats
# --------------------------------------------------------------------------- #
class RiskAccuracyStats(BaseModel):
    """Aggregated accuracy over resolved predictions — the loop's KPI."""

    vehicle_id: int
    total_predictions: int = 0
    resolved_predictions: int = 0
    with_feedback: int = 0
    accurate: int = 0
    false_alarms: int = 0
    missed: int = 0
    accuracy_rate: float | None = Field(
        None, description="准确率 0.0–1.0（有反馈样本中正确占比）"
    )
    false_alarm_rate: float | None = Field(None, description="误报率 0.0–1.0")
    by_level: dict[str, dict[str, int]] = Field(default_factory=dict)


class PatrolSummary(BaseModel):
    """Result of a proactive patrol across all vehicles."""

    patrolled: int = 0
    predictions_made: int = 0
    alerts_generated: int = 0
    deduped: int = 0
    details: list[dict[str, Any]] = Field(default_factory=list)
