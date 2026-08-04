"""Timeline Demo Service — 'A Car's Life' narrative generator.

Generates a deterministic 3-year life story for a virtual vehicle,
covering birth (2025) → usage (2026) → anomaly (2027). Each phase
includes telemetry snapshots, memory entries, key events, and (for
the anomaly phase) agent collaboration findings.

The final health report card includes traceable items so every number
can be clicked back to its source (memory/telemetry/agent finding).

This is a self-contained demo data generator — no external simulator
or kernel dependency required. All data is deterministic (seeded).
"""
from __future__ import annotations

from app.schemas.timeline import (
    AgentCollaboration,
    AgentFinding,
    HealthReport,
    LifeStoryResponse,
    MemoryEntry,
    TelemetrySnapshot,
    TimelineEvent,
    TimelinePhase,
    TraceableItem,
    UsedCarValuation,
    VehicleInfo,
)


def generate_life_story() -> LifeStoryResponse:
    """Generate the complete 'A Car's Life' narrative response."""
    vehicle = VehicleInfo(
        vin="VFSIM-2025-00042",
        name="星辰号",
        profile="family_ev",
        brand="Tesla",
        model="Model Y",
    )

    phases = [
        _build_phase_2025_birth(),
        _build_phase_2026_usage(),
        _build_phase_2027_anomaly(),
    ]

    report = _build_health_report()

    return LifeStoryResponse(
        vehicle=vehicle,
        phases=phases,
        report=report,
        demo_mode=True,
    )


# ------------------------------------------------------------------ #
#  Phase 1: 2025 — Birth
# ------------------------------------------------------------------ #
def _build_phase_2025_birth() -> TimelinePhase:
    return TimelinePhase(
        year=2025,
        label="诞生",
        summary="数字生命诞生。电池满电 SOH 100%，一切指标完美。",
        color="#a855f7",
        telemetry=TelemetrySnapshot(
            day=1,
            mileage=0.0,
            soh=100.0,
            battery_temp=22.0,
            charging_speed_ratio=1.0,
            charge_cycles=0,
            fast_charge_ratio=0.0,
        ),
        events=[
            TimelineEvent(
                day=0,
                date="2025-01-01",
                title="数字生命诞生",
                description="车辆出厂激活，数字孪生系统初始化完成。"
                "电池 SOH 100%，所有子系统状态完美。",
                event_type="birth",
                mileage=0.0,
            ),
            TimelineEvent(
                day=1,
                date="2025-01-02",
                title="首次驾驶",
                description="车主首次启动车辆，完成 32 km 通勤。"
                "一切系统运转正常，能耗表现优秀。",
                event_type="mileage",
                mileage=32.0,
            ),
            TimelineEvent(
                day=30,
                date="2025-01-31",
                title="满月体检",
                description="首月行驶 1,200 km，电池 SOH 99.8%。"
                "系统记录首次健康快照。",
                event_type="milestone",
                mileage=1200.0,
            ),
        ],
        memories=[
            MemoryEntry(
                id="MEM-2025-001",
                event_type="event",
                summary="车辆出厂激活，数字孪生系统初始化完成",
                impact_target="system_init",
                impact_delta=0.0,
                occurred_at="2025-01-01T00:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2025-002",
                event_type="habit",
                summary="车主首次充电：慢充模式，充电区间 30-80%",
                impact_target="charging_habit",
                impact_delta=0.0,
                occurred_at="2025-01-03T22:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2025-003",
                event_type="event",
                summary="首月健康快照：SOH 99.8%，所有子系统正常",
                impact_target="health_snapshot",
                impact_delta=-0.2,
                occurred_at="2025-01-31T10:00:00",
                source="simulator",
            ),
        ],
    )


# ------------------------------------------------------------------ #
#  Phase 2: 2026 — Usage
# ------------------------------------------------------------------ #
def _build_phase_2026_usage() -> TimelinePhase:
    return TimelinePhase(
        year=2026,
        label="用车",
        summary="日常通勤 + 长途出行 + 冬季严寒。"
        "快充比例上升，高速行驶增多，电池开始缓慢衰减。",
        color="#00f0ff",
        telemetry=TelemetrySnapshot(
            day=365,
            mileage=14800.0,
            soh=97.2,
            battery_temp=28.0,
            charging_speed_ratio=0.98,
            charge_cycles=180,
            fast_charge_ratio=0.45,
        ),
        events=[
            TimelineEvent(
                day=60,
                date="2026-03-02",
                title="首次长途旅行",
                description="杭州 → 上海，单程 180 km。"
                "途中使用快充 2 次，电池温度峰值 38°C。",
                event_type="mileage",
                mileage=4200.0,
            ),
            TimelineEvent(
                day=120,
                date="2026-05-01",
                title="快充习惯养成",
                description="车主开始频繁使用快充（占比 45%），"
                "充电区间从 30-80% 扩展到 20-90%。",
                event_type="milestone",
                mileage=7800.0,
            ),
            TimelineEvent(
                day=180,
                date="2026-06-30",
                title="夏季高温行车",
                description="连续 2 周环境温度 >35°C，"
                "电池温度频繁触及 42°C，冷却系统高负荷运转。",
                event_type="warning",
                mileage=10500.0,
            ),
            TimelineEvent(
                day=240,
                date="2026-08-29",
                title="冬季续航骤降",
                description="环境温度 -5°C，续航从 420 km 降至 280 km。"
                "PTC 暖风高耗电，电池化学活性降低。",
                event_type="warning",
                mileage=12800.0,
            ),
            TimelineEvent(
                day=330,
                date="2026-11-28",
                title="年度保养",
                description="行驶 14,800 km，电池 SOH 97.2%。"
                "年衰减 2.6%，处于正常范围上限。",
                event_type="maintenance",
                mileage=14800.0,
            ),
        ],
        memories=[
            MemoryEntry(
                id="MEM-2026-001",
                event_type="habit",
                summary="快充比例从 15% 升至 45%，充电区间扩展至 20-90%",
                impact_target="battery_stress",
                impact_delta=-0.5,
                occurred_at="2026-05-01T14:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2026-002",
                event_type="warning",
                summary="夏季高温：电池温度连续 2 周超过 40°C",
                impact_target="thermal_stress",
                impact_delta=-0.8,
                occurred_at="2026-06-30T15:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2026-003",
                event_type="warning",
                summary="冬季续航骤降 33%，PTC 暖风高耗电",
                impact_target="cold_weather_stress",
                impact_delta=-0.3,
                occurred_at="2026-08-29T08:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2026-004",
                event_type="event",
                summary="年度保养：SOH 97.2%，年衰减 2.6%（正常上限）",
                impact_target="health_snapshot",
                impact_delta=-2.6,
                occurred_at="2026-11-28T11:00:00",
                source="simulator",
            ),
        ],
    )


# ------------------------------------------------------------------ #
#  Phase 3: 2027 — Anomaly
# ------------------------------------------------------------------ #
def _build_phase_2027_anomaly() -> TimelinePhase:
    return TimelinePhase(
        year=2027,
        label="异常",
        summary="充电速度下降 20%，电池温度波动加大。"
        "守护系统触发异常告警，Guardian 召集多 Agent 协作诊断。",
        color="#ff3860",
        telemetry=TelemetrySnapshot(
            day=730,
            mileage=26500.0,
            soh=91.5,
            battery_temp=35.0,
            charging_speed_ratio=0.80,
            charge_cycles=320,
            fast_charge_ratio=0.55,
        ),
        events=[
            TimelineEvent(
                day=400,
                date="2027-02-05",
                title="充电速度异常",
                description="快充峰值功率从 120kW 降至 96kW（-20%）。"
                "BMS 记录充电温度波动 ±8°C，超出正常 ±3°C 范围。",
                event_type="anomaly",
                mileage=16200.0,
            ),
            TimelineEvent(
                day=402,
                date="2027-02-07",
                title="守护系统触发",
                description="Guardian Agent 检测到异常信号，"
                "召集 battery / diagnosis / safety / value 四个专家 Agent 并行会诊。",
                event_type="anomaly",
                mileage=16300.0,
            ),
            TimelineEvent(
                day=405,
                date="2027-02-10",
                title="诊断结论",
                description="电芯衰减早期 + 冷却效率下降。"
                "建议降低快充比例 + 冷却系统检查 + 调整充电区间。",
                event_type="milestone",
                mileage=16500.0,
            ),
            TimelineEvent(
                day=420,
                date="2027-02-25",
                title="冷却系统检修",
                description="冷却液泵效率下降 15%，更换后电池温度波动恢复 ±3°C。"
                "充电速度部分恢复至 105kW（-12.5%）。",
                event_type="maintenance",
                mileage=17200.0,
            ),
            TimelineEvent(
                day=730,
                date="2027-12-31",
                title="年终状态",
                description="行驶 26,500 km，SOH 91.5%。"
                "在调整充电策略后，衰减速率从 5.7%/年降至 3.2%/年。",
                event_type="milestone",
                mileage=26500.0,
            ),
        ],
        memories=[
            MemoryEntry(
                id="MEM-2027-001",
                event_type="anomaly",
                summary="充电速度下降 20%（120kW→96kW），温度波动 ±8°C",
                impact_target="charging_anomaly",
                impact_delta=-2.0,
                occurred_at="2027-02-05T19:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2027-002",
                event_type="anomaly",
                summary="Guardian 触发多 Agent 协作诊断",
                impact_target="agent_collaboration",
                impact_delta=0.0,
                occurred_at="2027-02-07T09:00:00",
                source="agent",
            ),
            MemoryEntry(
                id="MEM-2027-003",
                event_type="recovery",
                summary="冷却液泵更换，温度波动恢复 ±3°C，充电速度部分恢复",
                impact_target="thermal_recovery",
                impact_delta=0.8,
                occurred_at="2027-02-25T16:00:00",
                source="simulator",
            ),
            MemoryEntry(
                id="MEM-2027-004",
                event_type="habit",
                summary="车主调整充电策略：快充比例 55%→30%，区间 20-90%→30-80%",
                impact_target="charging_habit_improved",
                impact_delta=1.2,
                occurred_at="2027-03-01T20:00:00",
                source="agent",
            ),
            MemoryEntry(
                id="MEM-2027-005",
                event_type="event",
                summary="年终 SOH 91.5%，衰减速率从 5.7%/年降至 3.2%/年",
                impact_target="health_snapshot",
                impact_delta=-5.7,
                occurred_at="2027-12-31T10:00:00",
                source="simulator",
            ),
        ],
        agent_collaboration=AgentCollaboration(
            triggered=True,
            trigger_reason="充电速度下降 20% + 电池温度波动 ±8°C 超出阈值",
            guardian_summary="检测到电池系统异常信号。Guardian 召集 4 个专家 Agent"
            "并行会诊，诊断结果：电芯衰减早期 + 冷却效率下降。"
            "建议降低快充比例 + 冷却系统检查 + 调整充电区间至 30-80%。",
            findings=[
                AgentFinding(
                    agent_name="battery",
                    skill_name="powertrain_skill",
                    severity="warning",
                    finding="电芯衰减早期迹象：SOH 下降速率从 2.6%/年加速至 5.7%/年。"
                    "快充比例 55% + 高温行车 + 宽充电区间是主要诱因。",
                    recommendation="降低快充比例至 30% 以下，"
                    "充电区间收窄至 30-80%，避免高温环境快充。",
                    confidence=0.85,
                ),
                AgentFinding(
                    agent_name="diagnosis",
                    skill_name="powertrain_skill",
                    severity="warning",
                    finding="冷却液泵效率下降 15%，导致电池温度波动从 ±3°C 扩大至 ±8°C。"
                    "冷却流道可能存在部分堵塞。",
                    recommendation="检查冷却液泵和管路，必要时更换。"
                    "清洗冷却流道，检查冷却液浓度。",
                    confidence=0.88,
                ),
                AgentFinding(
                    agent_name="safety",
                    skill_name="chassis_skill",
                    severity="info",
                    finding="当前电池温度未触及热失控阈值（60°C），"
                    "但持续高温波动将加速电芯老化，需及时干预。",
                    recommendation="避免连续快充后立即激烈驾驶，"
                    "静置 15-30 分钟散热后再充电。",
                    confidence=0.78,
                ),
                AgentFinding(
                    agent_name="value",
                    skill_name="vehicle_value_skill",
                    severity="info",
                    finding="当前车辆估值 18.0 万元。若按建议优化充电策略，"
                    "12 个月后估值预计 19.8 万元（+1.8 万），"
                    "电池衰减率可从 5.7% 降至 3.2%。",
                    recommendation="执行充电策略优化 + 冷却系统检修，"
                    "预计 12 个月后健康评分从 87 提升至 91。",
                    confidence=0.82,
                ),
            ],
        ),
    )


# ------------------------------------------------------------------ #
#  Health Report
# ------------------------------------------------------------------ #
def _build_health_report() -> HealthReport:
    return HealthReport(
        health_score=87,
        health_grade="良好",
        battery_degradation_12m=4.0,
        charging_strategy="降低快充比例至 30%，充电区间收窄至 30-80%，"
        "避免高温环境快充，每月至少一次慢充满充校准。",
        used_car_valuation=UsedCarValuation(
            current=18.0,
            projected=19.8,
            delta=1.8,
        ),
        traceable_items=[
            TraceableItem(
                label="健康评分",
                value="87",
                source_type="telemetry",
                source_id="MEM-2027-005",
                source_description="年终 SOH 91.5%，衰减速率 5.7%/年 → 3.2%/年",
            ),
            TraceableItem(
                label="12个月电池衰减",
                value="+4.0%",
                source_type="agent",
                source_id="battery_finding",
                source_description="电芯衰减早期，快充 55% + 高温 + 宽充电区间",
            ),
            TraceableItem(
                label="当前估值",
                value="18.0 万元",
                source_type="telemetry",
                source_id="MEM-2027-005",
                source_description="行驶 26,500 km，SOH 91.5%",
            ),
            TraceableItem(
                label="优化后预计估值",
                value="19.8 万元",
                source_type="agent",
                source_id="value_finding",
                source_description="执行充电优化 + 冷却检修后估值提升",
            ),
            TraceableItem(
                label="估值提升空间",
                value="+1.8 万元",
                source_type="agent",
                source_id="value_finding",
                source_description="健康评分 87→91，衰减率 5.7%→3.2%",
            ),
            TraceableItem(
                label="充电速度下降",
                value="-20%",
                source_type="memory",
                source_id="MEM-2027-001",
                source_description="快充峰值 120kW→96kW，温度波动 ±8°C",
            ),
            TraceableItem(
                label="冷却系统修复",
                value="温度波动 ±8°C→±3°C",
                source_type="memory",
                source_id="MEM-2027-003",
                source_description="冷却液泵更换后恢复",
            ),
        ],
    )
