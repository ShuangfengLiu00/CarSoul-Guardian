"""主动巡检调度器 — 让 CarSoul 真正「主动」守护 (TASK010+).

产品定位是「主动健康管理」，但如果 Agent 只在用户发消息时才运行，
"主动守护"就名不副实。本模块用 APScheduler 定时触发 ``patrol_all``，
无需用户交互即可主动发现风险、推送提醒，把"被动响应"变成"主动巡检"。

调度策略
--------
- 常规巡检：每 ``interval_minutes`` 分钟一次（默认 30，可通过环境变量配置）。
- 高风险车辆：巡检时由 ``patrol_all`` 统一处理，不在调度层做差异化频率。
- 所有巡检动作写入日志，失败不影响下一次调度。

降级策略
--------
- APScheduler 未安装 → ``init_scheduler`` 返回 False，不抛异常；
  巡检仍可通过 ``POST /api/risk/patrol`` 手动触发，后端照常启动。
- 单次巡检失败 → 记录异常日志，调度器继续运行。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database import SessionLocal
from app.services import risk_prediction_service
from app.utils.logger import logger

# 全局调度器实例（None 表示未初始化或 APScheduler 不可用）。
_scheduler: Any = None

# 巡检配置 — 可在运行时通过 ``get_scheduler_status`` 查看。
_patrol_config: dict[str, Any] = {
    "interval_minutes": 30,      # 常规巡检间隔
    "enabled": True,             # 是否启用自动巡检（False 则只注册但不执行）
}


def init_scheduler() -> bool:
    """初始化 APScheduler 并注册主动巡检任务。

    Returns:
        True 表示调度器已启动；False 表示 APScheduler 不可用，
        调用方应回退到手动巡检（POST /api/risk/patrol）。
    """
    global _scheduler
    if _scheduler is not None:
        return True

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed — 主动巡检需手动触发 "
            "(POST /api/risk/patrol)。安装 apscheduler 后重启即可自动巡检。"
        )
        return False

    try:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            _patrol_job,
            trigger=IntervalTrigger(minutes=_patrol_config["interval_minutes"]),
            id="patrol_regular",
            name="CarSoul 常规主动巡检",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        _scheduler.start()
        logger.info(
            "CarSoul 主动巡检调度器已启动（间隔 {} 分钟）",
            _patrol_config["interval_minutes"],
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("主动巡检调度器启动失败: {}", exc)
        _scheduler = None
        return False


def shutdown_scheduler() -> None:
    """关闭调度器（应用退出时调用）。"""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("CarSoul 主动巡检调度器已停止。")
        except Exception as exc:  # noqa: BLE001
            logger.debug("调度器停止异常: {}", exc)
        _scheduler = None


def _patrol_job() -> None:
    """巡检任务执行体 — 由调度器定时触发。

    每次执行都创建独立的 DB 会话并在结束时关闭，
    避免长时间运行的调度器持有过期会话。失败仅记录日志，
    不向上抛出，防止 APScheduler 因未捕获异常停止任务。
    """
    started_at = datetime.utcnow()
    logger.info("CarSoul 主动巡检开始: {}", started_at.isoformat())
    try:
        db = SessionLocal()
        try:
            result = risk_prediction_service.patrol_all(db)
            logger.info(
                "主动巡检完成：{} 辆车，{} 条预测，{} 条告警",
                result.get("patrolled", 0),
                result.get("predictions_made", 0),
                result.get("alerts_generated", 0),
            )
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        # 关键：吞掉异常，防止调度器因单次失败被移除。
        logger.exception("主动巡检任务执行失败: {}", exc)


def get_scheduler_status() -> dict[str, Any]:
    """获取调度器状态（供管理端点返回）。"""
    if _scheduler is None:
        return {
            "running": False,
            "jobs": [],
            "config": _patrol_config,
            "message": (
                "调度器未初始化（APScheduler 未安装或未启动）。"
                "可手动触发巡检：POST /api/risk/patrol"
            ),
        }

    jobs = []
    try:
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            })
    except Exception as exc:  # noqa: BLE001
        logger.debug("获取调度任务列表异常: {}", exc)

    return {
        "running": bool(getattr(_scheduler, "running", False)),
        "jobs": jobs,
        "config": _patrol_config,
        "message": "调度器运行中" if _scheduler.running else "调度器已暂停",
    }


def trigger_patrol_now() -> dict[str, Any]:
    """同步触发一次巡检（供手动触发端点复用，避免重复逻辑）。

    注意：此函数直接调用 ``_patrol_job`` 的核心逻辑，
    不依赖调度器是否已初始化。
    """
    db = SessionLocal()
    try:
        return risk_prediction_service.patrol_all(db)
    finally:
        db.close()
