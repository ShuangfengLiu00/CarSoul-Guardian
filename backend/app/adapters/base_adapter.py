"""外部服务统一适配层基类。

所有第三方服务（充电/车险/DMS）继承此基类。
自动降级：live API → mock data → unavailable。
每次调用落账 external_service_audit（经 kernel.actionstore_guardian）。
MVP 阶段 _live_available=False（WARN-03），全部走 mock。

注意：架构设计文档原始伪码引用了 log_external_call / log_external_result，
但 actionstore_guardian.py 中这两个函数并不存在（幻觉依赖）。
此处改用真实存在的 log_agent_event，语义等价（C-15 审计含 data_source/confidence）。
"""
from __future__ import annotations

import time
import uuid


class ExternalServiceAdapter:
    """外部服务统一适配层基类。

    子类须实现 _call_live / _call_mock。call() 统一入口自动降级。
    """

    service_name: str = "base"

    def __init__(self) -> None:
        self._live_available: bool = False  # WARN-03: MVP 外部服务暂不可用
        self._dispatch_id: str = ""

    def call(self, method: str, params: dict) -> dict:
        """统一调用入口。自动降级 live → mock → unavailable。"""
        t0 = time.perf_counter()
        self._dispatch_id = uuid.uuid4().hex
        self._audit_call(method, params)

        if self._live_available:
            try:
                result = self._call_live(method, params)
                latency = int((time.perf_counter() - t0) * 1000)
                result["_data_source"] = "live"
                result["_confidence"] = 1.0
                self._audit_result(method, params, result, "live", 1.0, latency)
                return result
            except Exception:
                pass  # 降级到 mock

        # 降级 mock
        try:
            result = self._call_mock(method, params)
            latency = int((time.perf_counter() - t0) * 1000)
            result["_data_source"] = "mock"
            result["_confidence"] = 0.3
            self._audit_result(method, params, result, "mock", 0.3, latency)
            return result
        except Exception:
            latency = int((time.perf_counter() - t0) * 1000)
            unavailable = {
                "_data_source": "unavailable",
                "_confidence": 0.0,
                "degrade_code": "unavailable",
            }
            self._audit_result(
                method, params, unavailable, "unavailable", 0.0, latency)
            return unavailable

    def _call_live(self, method: str, params: dict) -> dict:
        """调用真实 API。子类实现。MVP 返回 NotImplementedError。"""
        raise NotImplementedError(f"{self.service_name}._call_live 未实现")

    def _call_mock(self, method: str, params: dict) -> dict:
        """仿真回退。子类必须实现。"""
        raise NotImplementedError(f"{self.service_name}._call_mock 未实现")

    def _audit_call(self, method: str, params: dict) -> None:
        """记录调用意图（不含敏感参数）。"""
        try:
            from app.kernel.actionstore_guardian import log_agent_event
            log_agent_event(
                dispatch_id=self._dispatch_id,
                agent_name=self.service_name,
                event_type="model-call",
                tool_name=method,
                result={"phase": "initiated", "param_keys": list(params.keys())},
            )
        except Exception:  # noqa: BLE001 — 审计不得拖垮主链路
            pass

    def _audit_result(self, method: str, params: dict, result: dict,
                      data_source: str, confidence: float,
                      latency_ms: int) -> None:
        """记录调用结果（C-15: 含 data_source + confidence）。"""
        try:
            from app.kernel.actionstore_guardian import log_agent_event
            log_agent_event(
                dispatch_id=self._dispatch_id,
                agent_name=self.service_name,
                event_type="model-call",
                tool_name=method,
                result={
                    "phase": "completed",
                    "data_source": data_source,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                },
            )
        except Exception:  # noqa: BLE001
            pass
