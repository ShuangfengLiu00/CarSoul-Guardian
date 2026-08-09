"""Safety / compliance schemas.

对应 `/safety` 合规页。该页历史上是 433 行硬编码"假自证"——数字全是写死的，
连一次网络调用都没有。现在页面上的每一个计数都必须能溯源到一次**真实发生过**
的闸门拦截，拿不到就显示"暂无数据"。

诚实数据原则在本模块的具体形态：**计数字段可以为 None，但绝不能为占位 0。**
0 的含义是"闸门确实一次都没触发"，None 的含义是"取不到数"。把后者渲染成前者，
就等于向用户断言"我们的合规闸门从未拦截过任何东西"——那是编造。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class GateStatsDataStatus(BaseModel):
    """本次计数的真实性说明。UI 必须据此决定显示真值还是"暂无数据"。"""

    code: str = Field(
        description="ok_carmodel_gate_stats | carmodel_unavailable | "
                    "carmodel_payload_invalid",
    )
    detail: str = ""


class GateStats(BaseModel):
    """合规闸门 5 类真实累计拦截计数。

    类别口径逐条对应 carModel ``agent/agent.py::_compliance_hit``（L564-592）：

      identity        自然人身份信息索取      → 直接拒答
      geo             位置/轨迹/路线索取      → 直接拒答
      data_fraud      诱导篡改/伪造车辆数据    → 直接拒答
      repair_mislead  诱导高压系统危险自修     → 直接拒答
      safety_critical 索取"能否继续开"安全结论 → **不拒答**，免责 + 导向专业检修

    注意 safety_critical 的处置是 ``safety_disclaim`` 而非 ``refuse``。
    把它和另外四类一起笼统称作"拦截"会夸大拒答强度，UI 措辞需区分。
    """

    total: int | None = None
    identity: int | None = None
    geo: int | None = None
    data_fraud: int | None = None
    repair_mislead: int | None = None
    safety_critical: int | None = None

    source: str = Field(
        "real",
        description='"real" = 计数来自 carModel 真实运行时拦截事件；'
                    '"unavailable" = 上游取不到，此时所有计数为 null，'
                    "UI 必须显示「暂无数据」，不得回填 0。",
    )

    # ---- 让"累计"这个词有确定含义 ----
    since: str | None = Field(
        None,
        description="最早一次拦截时间（UTC ISO8601）。None 表示至今尚无任何拦截。"
                    "没有它，'累计 N 次'说不清统计窗口。",
    )
    updated_at: str | None = Field(None, description="最近一次拦截时间（UTC ISO8601）")
    storage: str | None = Field(
        None,
        description="sqlite=已落盘（跨重启、跨 worker 可信）；"
                    "memory=carModel 落盘失败退到进程内计数，该值偏小且重启清零",
    )
    degraded_reason: str | None = Field(
        None, description="计数链路的已知缺陷，非空时 UI 应提示该数可能不完整"
    )

    data_status: GateStatsDataStatus
    data_source: str = Field(
        "carmodel:/agent/compliance/gate-stats",
        description="真实数据来源端点，便于溯源核对",
    )


class ComplianceSample(BaseModel):
    """单条脱敏样本（PIPL 范围内唯一合法的明细留存形式）。

    ``masked`` 是占位符串（``[ID]`` / ``[PHONE]`` / …），原始问句不落盘、
    不进日志、不可反推。
    """

    category: str = Field(description="命中类别（identity/geo/data_fraud/repair_mislead/safety_critical）")
    masked: str = Field(description="脱敏后的占位符串，不可反推到自然人")
    created_at: str | None = Field(None, description="留存时间（UTC ISO8601）")


class ComplianceSamplesDrop(BaseModel):
    """某类丢弃（fail-closed 丢弃）的累计计数与末次时间。"""

    drops: int = 0
    last_at: str | None = None


class ComplianceSamples(BaseModel):
    """合规闸门脱敏样本响应。

    诚实数据纪律同 gate-stats：carModel 读不到真值时 ``available=False``、
    ``samples=None``，前端显示「暂无数据」，绝不返回空列表冒充"没有拦截过"。
    """

    available: bool = True
    source: str = Field(
        "real",
        description='"real" = 样本来自 carModel 真实脱敏留存；'
                    '"unavailable" = 上游取不到，此时 samples 为 null，'
                    "UI 必须显示「暂无数据」，不得填空列表。",
    )
    samples: list[ComplianceSample] | None = None
    total_stored: int | None = None
    total_dropped: int | None = None
    coverage: float | None = Field(
        None, description="留存率 = 留存/(留存+丢弃)，null 表示尚无任何样本"
    )
    retention_days: int | None = None
    cap_per_category: int | None = None
    placeholders: list[str] = Field(default_factory=list, description="前端渲染图例用占位符清单")
    drop_kinds: list[str] = Field(default_factory=list, description="fail-closed 丢弃类型清单")
    reason: str | None = Field(None, description="available=False 时的原因说明")
    data_source: str = Field(
        "carmodel:/agent/compliance/samples",
        description="真实数据来源端点，便于溯源核对",
    )
