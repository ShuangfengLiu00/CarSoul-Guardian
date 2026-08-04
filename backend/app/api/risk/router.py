"""Risk-prediction API — the closed loop exposed over REST (TASK010).

Endpoints
---------
Per-vehicle forward path + queries:
  POST   /api/vehicle/{vehicle_id}/risk/predict          触发一次风险预测
  GET    /api/vehicle/{vehicle_id}/risk/predictions       预测历史列表
  GET    /api/vehicle/{vehicle_id}/risk/accuracy          准确率/误报率统计
  GET    /api/risk/predictions/{prediction_id}            单条预测详情（含推理轨迹）
  POST   /api/risk/predictions/{prediction_id}/acknowledge 确认预测
  POST   /api/risk/predictions/{prediction_id}/feedback   提交处置结果（闭合环路）

Proactive patrol:
  POST   /api/risk/patrol                                 全车主动巡检

Architecture note: this route contains NO AI logic — it delegates to
``app.services.risk_prediction_service``, which in turn drives the
``carsoul_agent`` workflow. The "守护非控制" boundary is preserved: the
loop only ever predicts, alerts, records, and learns — never commands.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.risk_prediction import (
    PatrolSummary,
    RiskAccuracyStats,
    RiskFeedbackRequest,
    RiskPredictionDetail,
    RiskPredictionList,
    RiskPredictionOut,
    RiskPredictRequest,
)
from app.services import risk_prediction_service

router = APIRouter()


# =========================================================================== #
#  Per-vehicle: predict / list / accuracy
# =========================================================================== #
@router.post(
    "/vehicle/{vehicle_id}/risk/predict",
    response_model=RiskPredictionOut,
    status_code=201,
    summary="触发一次风险预测（闭环正向路径）",
)
def predict_risk(
    vehicle_id: int,
    payload: RiskPredictRequest | None = None,
    db: Session = Depends(get_db),
) -> RiskPredictionOut:
    triggered_by = payload.triggered_by if payload else "user"
    try:
        pred = risk_prediction_service.run_prediction(db, vehicle_id, triggered_by)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return RiskPredictionOut.model_validate(pred)


@router.get(
    "/vehicle/{vehicle_id}/risk/predictions",
    response_model=RiskPredictionList,
    summary="预测历史列表",
)
def list_predictions(
    vehicle_id: int,
    status: str | None = Query(None, description="open|acknowledged|resolved|expired"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> RiskPredictionList:
    items = risk_prediction_service.list_predictions(db, vehicle_id, status, limit)
    out = [RiskPredictionOut.model_validate(p) for p in items]
    return RiskPredictionList(items=out, total=len(out))


@router.get(
    "/vehicle/{vehicle_id}/risk/accuracy",
    response_model=RiskAccuracyStats,
    summary="预测准确率/误报率统计（闭环 KPI）",
)
def get_accuracy(vehicle_id: int, db: Session = Depends(get_db)) -> RiskAccuracyStats:
    stats = risk_prediction_service.compute_accuracy(db, vehicle_id)
    return RiskAccuracyStats(**stats)


# =========================================================================== #
#  Single prediction: detail / acknowledge / feedback
# =========================================================================== #
@router.get(
    "/risk/predictions/{prediction_id}",
    response_model=RiskPredictionDetail,
    summary="预测详情（含完整推理轨迹）",
)
def get_prediction(
    prediction_id: int, db: Session = Depends(get_db)
) -> RiskPredictionDetail:
    pred = risk_prediction_service.get_prediction(db, prediction_id)
    if pred is None:
        raise HTTPException(404, "Prediction not found")
    return RiskPredictionDetail.model_validate(pred)


@router.post(
    "/risk/predictions/{prediction_id}/acknowledge",
    response_model=RiskPredictionOut,
    summary="确认预测（open → acknowledged）",
)
def acknowledge_prediction(
    prediction_id: int, db: Session = Depends(get_db)
) -> RiskPredictionOut:
    pred = risk_prediction_service.acknowledge_prediction(db, prediction_id)
    if pred is None:
        raise HTTPException(404, "Prediction not found or not acknowledgeable")
    return RiskPredictionOut.model_validate(pred)


@router.post(
    "/risk/predictions/{prediction_id}/feedback",
    response_model=RiskPredictionOut,
    summary="提交处置结果（闭合环路：记录实际结果并计算准确率）",
)
def submit_feedback(
    prediction_id: int,
    payload: RiskFeedbackRequest,
    db: Session = Depends(get_db),
) -> RiskPredictionOut:
    try:
        pred = risk_prediction_service.submit_feedback(
            db,
            prediction_id,
            payload.actual_outcome,
            payload.outcome_notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if pred is None:
        raise HTTPException(404, "Prediction not found")
    return RiskPredictionOut.model_validate(pred)


# =========================================================================== #
#  Proactive patrol
# =========================================================================== #
@router.post(
    "/risk/patrol",
    response_model=PatrolSummary,
    summary="全车主动巡检（为每辆活跃车辆运行一次预测）",
)
def patrol(db: Session = Depends(get_db)) -> PatrolSummary:
    summary = risk_prediction_service.patrol_all(db)
    return PatrolSummary(**summary)


# =========================================================================== #
#  Patrol scheduler management — 让"主动守护"名副其实
# =========================================================================== #
@router.get(
    "/risk/scheduler/status",
    summary="主动巡检调度器状态",
)
def scheduler_status() -> dict:
    """返回调度器运行状态、下次巡检时间和配置。

    供前端展示「主动巡检已开启」徽标，也让评委直观看到
    CarSoul 在无人交互时仍在定时守护。
    """
    from app.services.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.post(
    "/risk/scheduler/start",
    summary="启动主动巡检调度器",
)
def scheduler_start() -> dict:
    """启动定时主动巡检。

    APScheduler 未安装时返回 ``started=False`` 并提示手动巡检。
    """
    from app.services.scheduler import init_scheduler, get_scheduler_status
    started = init_scheduler()
    return {"started": started, **get_scheduler_status()}


@router.post(
    "/risk/scheduler/stop",
    summary="停止主动巡检调度器",
)
def scheduler_stop() -> dict:
    """停止定时主动巡检（不影响手动巡检端点）。"""
    from app.services.scheduler import shutdown_scheduler, get_scheduler_status
    shutdown_scheduler()
    return {"stopped": True, **get_scheduler_status()}
