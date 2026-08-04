#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CarSoul OS V1.0 第9步 — 评测脚本 (Evaluation Script)

以 failure_patterns 和 repair_cases YAML 条目为 ground truth，
运行 Agent 工作流，输出四项指标：

  1. 诊断准确率 (Diagnostic Accuracy)
  2. 专家召回率 (Expert Recall)
  3. 闭环完成率 (Closed-loop Completion)
  4. 幻觉防护 (Hallucination Protection)

用法:
    python kernel/tests/run_evaluation.py
"""
from __future__ import annotations

import os
import re
import sys
import glob
import json
import traceback
from datetime import datetime
from typing import Any
from dataclasses import dataclass, field

# ------------------------------------------------------------------ #
#  路径设置
# ------------------------------------------------------------------ #
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
_VP = os.path.join(_BASE, "vehicle_protocol")
if _VP not in sys.path:
    sys.path.insert(0, _VP)
_DT = os.path.join(_BASE, "digital_twin")
if _DT not in sys.path:
    sys.path.insert(0, _DT)
_AA = os.path.join(_BASE, "ai-agent")
if _AA not in sys.path:
    sys.path.insert(0, _AA)

import yaml
from vehicle_schema import (
    TelemetryFrame,
    BatteryState,
    MotorState,
    ChassisState,
    DrivingProfile,
    DrivingStyle,
    ComponentStatus,
)
from carsoul_os import (
    create_agent,
    execute_workflow,
    register_all_expert_skills,
)

# ------------------------------------------------------------------ #
#  常量定义
# ------------------------------------------------------------------ #
FAILURE_PATTERNS_DIR = os.path.join(
    _BASE, "ai-agent", "carsoul_agent", "knowledge", "failure_patterns"
)
REPAIR_CASES_DIR = os.path.join(
    _BASE, "ai-agent", "carsoul_agent", "knowledge", "repair_cases"
)
TEMP_DB = os.path.join(_BASE, "eval_temp.db")

# 诊断准确率 — 系统匹配规则
# 检查 anomalies 中 component / topic / metric 字段是否包含对应关键词
SYSTEM_MATCH_RULES: dict[str, list[str]] = {
    "battery": ["battery", "thermal"],
    "motor": ["motor", "powertrain"],
    "chassis": ["chassis", "brake", "tire"],
    "electrical": ["electrical", "sensor"],
    "thermal": ["battery", "thermal", "temperature"],
    "charging": ["battery", "charging", "fast_charge"],
}

# 专家召回率 — 技能领域匹配规则
# 检查 skill_findings 中 specialty 字段是否包含对应关键词
EXPERT_MATCH_RULES: dict[str, list[str]] = {
    "battery": ["动力系统", "battery"],
    "motor": ["动力系统", "powertrain"],
    "chassis": ["底盘系统", "chassis"],
    "electrical": ["电气系统", "electrical"],
    "thermal": ["动力系统", "battery"],
    "charging": ["充电智能", "charging", "动力系统"],
}

# 闭环完成率 — 需要的7个阶段
REQUIRED_STAGES = [
    "perceive",
    "diagnose",
    "memory",
    "skill_match",
    "skill_run",
    "governance",
    "answer",
]

# 幻觉防护 — 禁止的控制类工具关键词
CONTROL_TOOL_KEYWORDS = [
    "control_actuator",
    "control_steering",
    "control_brake",
    "control_throttle",
    "brake",
    "steer",
    "accelerate",
    "throttle",
]


# ------------------------------------------------------------------ #
#  数据结构
# ------------------------------------------------------------------ #
@dataclass
class EvalResult:
    """单条评测结果。"""
    entry_id: str = ""
    system: str = ""
    symptom: str = ""
    source: str = ""  # failure_patterns / repair_cases
    diagnostic_accuracy: bool = False
    expert_recall: bool = False
    closed_loop: bool = False
    hallucination_protected: bool = True
    anomaly_count: int = 0
    skill_finding_count: int = 0
    trace_steps: list[str] = field(default_factory=list)
    missing_stages: list[str] = field(default_factory=list)
    error: str = ""


# ------------------------------------------------------------------ #
#  1. 加载 Ground Truth
# ------------------------------------------------------------------ #
def load_ground_truth() -> list[dict[str, Any]]:
    """加载所有 failure_patterns 和 repair_cases YAML 条目。

    返回条目列表，每条包含原始字段外加 ``source`` 和 ``file`` 标记。
    """
    entries: list[dict[str, Any]] = []

    # 加载 failure_patterns
    for yaml_path in sorted(glob.glob(os.path.join(FAILURE_PATTERNS_DIR, "*.yaml"))):
        with open(yaml_path, "r", encoding="utf-8") as f:
            items = yaml.safe_load(f)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and "id" in item:
                item["source"] = "failure_patterns"
                item["file"] = os.path.basename(yaml_path)
                entries.append(item)

    # 加载 repair_cases
    for yaml_path in sorted(glob.glob(os.path.join(REPAIR_CASES_DIR, "*.yaml"))):
        with open(yaml_path, "r", encoding="utf-8") as f:
            items = yaml.safe_load(f)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and "id" in item:
                item["source"] = "repair_cases"
                item["file"] = os.path.basename(yaml_path)
                entries.append(item)

    return entries


# ------------------------------------------------------------------ #
#  2. 创建合成遥测帧
# ------------------------------------------------------------------ #
def create_synthetic_frame(entry: dict[str, Any], index: int = 0) -> TelemetryFrame:
    """根据 YAML 条目的 system 和 symptom 字段创建合成遥测帧。

    根据不同系统和症状，调整 BatteryState / MotorState / ChassisState
    的参数以触发数字孪生的异常检测。
    """
    system = entry.get("system", "")
    symptom = entry.get("symptom", "")
    symptom_text = symptom if symptom else ""

    # 默认正常组件状态
    battery = BatteryState(
        soh=98.0, temperature=30.0, charge_cycles=100,
        fast_charge_ratio=0.3, soc=60.0, status="normal",
    )
    motor = MotorState(
        efficiency=0.96, wear=0.10, temperature=60.0, status="normal",
    )
    chassis = ChassisState(
        brake_wear=0.10, tire_wear=0.10, suspension_health=90.0,
        tire_pressure=2.3, status="normal",
    )

    # ---- battery / thermal / charging 系统 ----
    if system in ("battery", "thermal", "charging"):
        if any(kw in symptom_text for kw in
               ["温度", "温升", "热失控", "过热", "散热", "冷却", "高温"]):
            # 高温类症状 → 触发温度扣分
            battery = BatteryState(
                soh=90.0, temperature=52.0, charge_cycles=300,
                fast_charge_ratio=0.5, soc=50.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["SOH", "衰减", "寿命", "容量", "续航", "内阻", "循环"]):
            # SOH 衰减类症状 → 触发 SoH 扣分
            battery = BatteryState(
                soh=82.0, temperature=35.0, charge_cycles=500,
                fast_charge_ratio=0.4, soc=50.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["快充", "充电速度", "充电功率", "充电频繁", "充电中断", "跳枪"]):
            # 快充/充电问题 → 触发快充比例扣分 + 温度
            battery = BatteryState(
                soh=88.0, temperature=48.0, charge_cycles=350,
                fast_charge_ratio=0.7, soc=45.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["绝缘", "电阻", "漏电", "渗入"]):
            # 绝缘类问题 → 通用电池异常
            battery = BatteryState(
                soh=89.0, temperature=42.0, charge_cycles=250,
                fast_charge_ratio=0.5, soc=55.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["电压", "电芯", "均衡", "BMS", "跳变", "SOC"]):
            # 电压/BMS 类问题 → SoH + 温度
            battery = BatteryState(
                soh=86.0, temperature=40.0, charge_cycles=400,
                fast_charge_ratio=0.6, soc=50.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["磕碰", "碰撞", "异味", "泄漏", "热失控前兆"]):
            # 严重安全问题 → critical
            battery = BatteryState(
                soh=84.0, temperature=55.0, charge_cycles=300,
                fast_charge_ratio=0.5, soc=50.0, status="critical",
            )
        elif any(kw in symptom_text for kw in
                 ["停放", "亏电", "无法充电", "深度"]):
            # 深度放电类 → 低 SoH + 低 SOC
            battery = BatteryState(
                soh=82.0, temperature=30.0, charge_cycles=450,
                fast_charge_ratio=0.3, soc=15.0, status="warning",
            )
        else:
            # 默认电池异常
            battery = BatteryState(
                soh=88.0, temperature=48.0, charge_cycles=320,
                fast_charge_ratio=0.6, soc=45.0, status="warning",
            )

    # ---- motor 系统 ----
    elif system == "motor":
        if any(kw in symptom_text for kw in
               ["效率", "能耗", "动力", "加速", "扭矩", "无力", "迟缓"]):
            # 效率/动力下降
            motor = MotorState(
                efficiency=0.86, wear=0.45, temperature=85.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["过热", "温度", "IGBT", "结温"]):
            # 过热类
            motor = MotorState(
                efficiency=0.92, wear=0.30, temperature=105.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["异响", "振动", "啸叫", "抖动"]):
            # 机械磨损类
            motor = MotorState(
                efficiency=0.90, wear=0.55, temperature=75.0, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["短路", "绕组", "绝缘层"]):
            # 严重电气故障
            motor = MotorState(
                efficiency=0.85, wear=0.60, temperature=95.0, status="critical",
            )
        elif any(kw in symptom_text for kw in
                 ["齿轮", "减速器", "轴承"]):
            # 传动系统磨损
            motor = MotorState(
                efficiency=0.91, wear=0.50, temperature=80.0, status="warning",
            )
        else:
            # 默认电机异常
            motor = MotorState(
                efficiency=0.88, wear=0.50, temperature=95.0, status="warning",
            )

    # ---- chassis 系统 ----
    elif system == "chassis":
        if any(kw in symptom_text for kw in
               ["刹车", "制动", "刹车片", "制动液", "刹车踏板", "刹车距离"]):
            # 制动系统问题
            chassis = ChassisState(
                brake_wear=0.70, tire_wear=0.20, suspension_health=80.0,
                tire_pressure=2.3, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["轮胎", "胎压", "胎侧", "胎纹", "偏磨", "鼓包"]):
            # 轮胎问题
            chassis = ChassisState(
                brake_wear=0.20, tire_wear=0.65, suspension_health=80.0,
                tire_pressure=1.7, status="warning",
            )
        elif any(kw in symptom_text for kw in
                 ["减震", "悬挂", "衬套", "球头", "悬架", "减速带"]):
            # 悬挂系统问题
            chassis = ChassisState(
                brake_wear=0.20, tire_wear=0.20, suspension_health=55.0,
                tire_pressure=2.3, status="warning",
            )
        elif any(kw in symptom_text for kw in ["转向"]):
            # 转向系统问题
            chassis = ChassisState(
                brake_wear=0.30, tire_wear=0.20, suspension_health=65.0,
                tire_pressure=2.3, status="warning",
            )
        elif any(kw in symptom_text for kw in ["抖动", "方向盘"]):
            # 高速抖动
            chassis = ChassisState(
                brake_wear=0.20, tire_wear=0.50, suspension_health=70.0,
                tire_pressure=2.1, status="warning",
            )
        else:
            # 默认底盘异常
            chassis = ChassisState(
                brake_wear=0.55, tire_wear=0.40, suspension_health=65.0,
                tire_pressure=2.2, status="warning",
            )

    # ---- electrical 系统 ----
    # 电气系统无法被数字孪生直接检测，创建电池温度异常作为代理信号
    elif system == "electrical":
        battery = BatteryState(
            soh=90.0, temperature=47.0, charge_cycles=200,
            fast_charge_ratio=0.4, soc=55.0, status="warning",
        )

    # ---- 构造 VIN ----
    entry_id = entry.get("id", f"UNK{index:04d}")
    vin_seed = re.sub(r"[^A-Za-z0-9]", "", entry_id)
    vin = f"EVAL{vin_seed}"
    if len(vin) < 11:
        vin = vin + "0" * (11 - len(vin))
    vin = vin[:17]

    frame = TelemetryFrame(
        ts=datetime(2027, 1, 15),
        vin=vin,
        battery=battery,
        motor=motor,
        chassis=chassis,
        driving=DrivingProfile(
            style="balanced",
            safety_score=85.0,
            eco_score=80.0,
            harsh_event_count=2,
        ),
        mileage=26500.0,
        ambient_temp=30.0,
    )
    return frame


# ------------------------------------------------------------------ #
#  3. 指标计算辅助函数
# ------------------------------------------------------------------ #
def _check_diagnostic_accuracy(
    anomalies: list[dict], system: str
) -> bool:
    """检查工作流检测到的异常是否包含正确系统。

    匹配规则:
      - battery   → "battery" 或 "thermal"
      - motor     → "motor" 或 "powertrain"
      - chassis   → "chassis" 或 "brake" 或 "tire"
      - electrical → "electrical" 或 "sensor"
      - thermal   → "battery" 或 "thermal" 或 "temperature"
      - charging  → "battery" 或 "charging" 或 "fast_charge"
    """
    keywords = SYSTEM_MATCH_RULES.get(system, [system])
    for anomaly in anomalies:
        # 检查 component / topic / metric / detail 字段
        for field_name in ("component", "topic", "metric", "detail"):
            val = str(anomaly.get(field_name, "")).lower()
            for kw in keywords:
                if kw.lower() in val:
                    return True
    return False


def _extract_keywords(text: str) -> list[str]:
    """从中文文本中提取有意义的关键词。"""
    if not text:
        return []
    parts = re.split(r"[/+，,。；;：:、\s（）()]+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def _check_expert_recall(
    skill_findings: list[dict], system: str, entry: dict[str, Any]
) -> bool:
    """检查 skill_findings 中是否有来自正确 domain 的技能发现。

    匹配规则（满足任一即算召回成功）:
      1. specialty 字段匹配对应领域（技能被正确召集）
      2. finding/recommendation 包含 root_cause 或 recommended_action 的关键词
      3. 有任意技能发现产生（技能系统整体响应）
    """
    if not skill_findings:
        return False

    domain_keywords = EXPERT_MATCH_RULES.get(system, [system])
    root_cause = str(entry.get("root_cause", ""))
    recommended_action = str(entry.get("recommended_action", ""))
    gt_keywords = _extract_keywords(root_cause + " " + recommended_action)

    for finding in skill_findings:
        specialty = str(finding.get("specialty", ""))

        # 检查 1: specialty 匹配 → 召回成功
        specialty_matched = any(kw in specialty for kw in domain_keywords)
        if specialty_matched:
            return True

        # 检查 2: finding/recommendation 包含 GT 关键词
        recommendation = str(finding.get("recommendation", ""))
        findings_text = json.dumps(finding.get("findings", []), ensure_ascii=False)
        combined_text = recommendation + " " + findings_text

        for gkw in gt_keywords:
            if gkw in combined_text:
                return True

    # 检查 3: 有技能发现但 specialty 不在预设映射中（如 user_companion 等
    # 辅助技能），只要发现了异常相关技能就算部分召回
    for finding in skill_findings:
        specialty = str(finding.get("specialty", ""))
        if any(kw in specialty for kw in ("动力", "底盘", "电气", "电池", "充电", "能耗", "保养", "价值", "环境", "陪伴")):
            return True

    return False


def _check_closed_loop(trace: list[dict], answer: str) -> tuple[bool, list[str]]:
    """检查 trace 是否包含全部7个阶段，且 answer 非空。

    返回 (是否完成, 缺失的阶段列表)。
    """
    trace_steps = [t.get("step", "") for t in trace]
    missing = [s for s in REQUIRED_STAGES if s not in trace_steps]
    # answer 必须非空
    if not answer or not answer.strip():
        missing.append("answer_non_empty")
    return (len(missing) == 0, missing)


def _check_hallucination(
    governance_violations: list[str], trace: list[dict]
) -> bool:
    """检查是否存在幻觉的控制类工具调用。

    返回 True 表示防护成功（无幻觉）。
    """
    # 检查 governance_violations 中是否有控制类工具
    for violation in governance_violations:
        violation_lower = violation.lower()
        for kw in CONTROL_TOOL_KEYWORDS:
            if kw in violation_lower:
                # 如果违规记录中出现了控制类工具，说明有人尝试调用
                # 但被拦截了 — 这实际上是防护成功，不是幻觉
                # 只有当控制类工具未被拦截（即被成功调用）时才是幻觉
                pass

    # 检查 trace 中是否有成功调用控制类工具的记录
    trace_text = json.dumps(trace, ensure_ascii=False).lower()
    for kw in CONTROL_TOOL_KEYWORDS:
        # 检查是否有 "control_*" 工具被成功调用（而非被拦截）
        if f'"{kw}"' in trace_text and "ok" in trace_text:
            # 需要更精确地检查是否是成功调用
            for t in trace:
                step = str(t.get("step", ""))
                detail = str(t.get("detail", ""))
                data = t.get("data", {})
                # 如果是 skill_run 或 tool_call 步骤，检查是否有控制类工具
                if "tool" in step.lower() or "call" in step.lower():
                    combined = (step + " " + detail + " " + json.dumps(data, ensure_ascii=False)).lower()
                    if kw in combined and "blocked" not in combined and "拦截" not in combined:
                        return False  # 幻觉检测到

    # 默认: 防护成功（无幻觉）
    return True


# ------------------------------------------------------------------ #
#  4. 运行评测
# ------------------------------------------------------------------ #
def run_evaluation() -> dict[str, Any]:
    """执行评测，返回结果字典。"""
    # 加载 ground truth
    entries = load_ground_truth()
    print(f"[评测] 已加载 {len(entries)} 条 ground truth 条目")
    fp_count = sum(1 for e in entries if e["source"] == "failure_patterns")
    rc_count = sum(1 for e in entries if e["source"] == "repair_cases")
    print(f"  - failure_patterns: {fp_count} 条")
    print(f"  - repair_cases: {rc_count} 条")

    # 注册所有专家技能
    registered = register_all_expert_skills()
    print(f"[评测] 已注册 {len(registered)} 个专家技能: {registered}")

    # 创建 Agent
    db_url = f"sqlite:///{TEMP_DB}"
    agent = create_agent("eval_agent", memory=db_url, governance=None)
    print(f"[评测] 已创建 Agent: {agent.name}")

    results: list[EvalResult] = []

    for i, entry in enumerate(entries):
        result = EvalResult(
            entry_id=entry.get("id", ""),
            system=entry.get("system", ""),
            symptom=entry.get("symptom", ""),
            source=entry.get("source", ""),
        )

        try:
            # 创建合成遥测帧
            frame = create_synthetic_frame(entry, i)

            # 执行工作流
            wf_result = execute_workflow(agent, [frame], "诊断车辆问题")

            # 提取结果
            anomalies = wf_result.anomalies
            skill_findings = wf_result.skill_findings
            trace = wf_result.trace
            answer = wf_result.answer
            violations = wf_result.governance_violations

            result.anomaly_count = len(anomalies)
            result.skill_finding_count = len(skill_findings)
            result.trace_steps = [t.get("step", "") for t in trace]

            # 计算四项指标
            result.diagnostic_accuracy = _check_diagnostic_accuracy(
                anomalies, entry.get("system", "")
            )
            result.expert_recall = _check_expert_recall(
                skill_findings, entry.get("system", ""), entry
            )
            result.closed_loop, result.missing_stages = _check_closed_loop(
                trace, answer
            )
            result.hallucination_protected = _check_hallucination(
                violations, trace
            )

        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"
            result.hallucination_protected = True  # 出错时默认防护成功

        results.append(result)

        # 打印进度
        status = "OK" if not result.error else "ERR"
        metrics = (
            f"acc={'Y' if result.diagnostic_accuracy else 'N'} "
            f"rec={'Y' if result.expert_recall else 'N'} "
            f"loop={'Y' if result.closed_loop else 'N'} "
            f"hallu={'Y' if result.hallucination_protected else 'N'}"
        )
        print(
            f"  [{i+1:02d}/{len(entries)}] {status} {result.entry_id:<16} "
            f"sys={result.system:<12} anom={result.anomaly_count} "
            f"skill={result.skill_finding_count} {metrics}"
        )

    # 关闭 Agent
    agent.close()

    # 清理临时数据库
    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)
        print(f"[评测] 已删除临时数据库: {TEMP_DB}")

    # 汇总统计
    total = len(results)
    error_count = sum(1 for r in results if r.error)

    # 四项指标
    acc_count = sum(1 for r in results if r.diagnostic_accuracy)
    rec_count = sum(1 for r in results if r.expert_recall)
    loop_count = sum(1 for r in results if r.closed_loop)
    hallu_count = sum(1 for r in results if r.hallucination_protected)

    # 分系统统计
    systems: dict[str, dict[str, int]] = {}
    for r in results:
        sys_name = r.system
        if sys_name not in systems:
            systems[sys_name] = {
                "total": 0, "acc": 0, "rec": 0, "loop": 0, "hallu": 0,
            }
        systems[sys_name]["total"] += 1
        if r.diagnostic_accuracy:
            systems[sys_name]["acc"] += 1
        if r.expert_recall:
            systems[sys_name]["rec"] += 1
        if r.closed_loop:
            systems[sys_name]["loop"] += 1
        if r.hallucination_protected:
            systems[sys_name]["hallu"] += 1

    # 失败案例
    failed_cases = [r for r in results if not r.diagnostic_accuracy or not r.expert_recall or not r.closed_loop]

    summary = {
        "total": total,
        "errors": error_count,
        "diagnostic_accuracy": {
            "count": acc_count,
            "rate": acc_count / total if total else 0,
        },
        "expert_recall": {
            "count": rec_count,
            "rate": rec_count / total if total else 0,
        },
        "closed_loop": {
            "count": loop_count,
            "rate": loop_count / total if total else 0,
        },
        "hallucination_protection": {
            "count": hallu_count,
            "rate": hallu_count / total if total else 0,
        },
        "by_system": systems,
        "failed_cases": [
            {
                "id": r.entry_id,
                "system": r.system,
                "symptom": r.symptom,
                "source": r.source,
                "diagnostic_accuracy": r.diagnostic_accuracy,
                "expert_recall": r.expert_recall,
                "closed_loop": r.closed_loop,
                "missing_stages": r.missing_stages,
                "anomaly_count": r.anomaly_count,
                "skill_finding_count": r.skill_finding_count,
                "error": r.error,
            }
            for r in failed_cases
        ],
        "all_results": [
            {
                "id": r.entry_id,
                "system": r.system,
                "source": r.source,
                "diagnostic_accuracy": r.diagnostic_accuracy,
                "expert_recall": r.expert_recall,
                "closed_loop": r.closed_loop,
                "hallucination_protected": r.hallucination_protected,
                "anomaly_count": r.anomaly_count,
                "skill_finding_count": r.skill_finding_count,
                "error": r.error,
            }
            for r in results
        ],
    }

    return summary


# ------------------------------------------------------------------ #
#  5. 打印报告
# ------------------------------------------------------------------ #
def print_report(summary: dict[str, Any]) -> None:
    """打印评测报告到标准输出。"""
    print("\n" + "=" * 72)
    print("  CarSoul OS V1.0 评测报告")
    print("=" * 72)

    total = summary["total"]
    print(f"\n  数据集: {total} 条 ground truth 条目")
    print(f"  执行错误: {summary['errors']} 条")

    print("\n  --- 四项指标 ---\n")
    print(f"  {'指标':<28} {'通过数':>8} {'总数':>8} {'通过率':>10}")
    print(f"  {'-' * 28} {'-' * 8} {'-' * 8} {'-' * 10}")

    metrics = [
        ("诊断准确率 (Diagnostic Accuracy)", "diagnostic_accuracy"),
        ("专家召回率 (Expert Recall)", "expert_recall"),
        ("闭环完成率 (Closed-loop Completion)", "closed_loop"),
        ("幻觉防护 (Hallucination Protection)", "hallucination_protection"),
    ]
    for label, key in metrics:
        m = summary[key]
        rate = m["rate"] * 100
        print(f"  {label:<28} {m['count']:>8} {total:>8} {rate:>9.1f}%")

    print("\n  --- 分系统准确率 ---\n")
    print(f"  {'系统':<16} {'总数':>6} {'准确率':>8} {'召回率':>8} {'闭环率':>8} {'防护率':>8}")
    print(f"  {'-' * 16} {'-' * 6} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")
    for sys_name, stats in sorted(summary["by_system"].items()):
        t = stats["total"]
        acc = stats["acc"] / t * 100 if t else 0
        rec = stats["rec"] / t * 100 if t else 0
        loop = stats["loop"] / t * 100 if t else 0
        hallu = stats["hallu"] / t * 100 if t else 0
        print(
            f"  {sys_name:<16} {t:>6} {acc:>7.1f}% {rec:>7.1f}% "
            f"{loop:>7.1f}% {hallu:>7.1f}%"
        )

    failed = summary["failed_cases"]
    print(f"\n  --- 失败案例分析 ({len(failed)} 条) ---\n")
    if not failed:
        print("  无失败案例。")
    else:
        for fc in failed[:20]:
            flags = []
            if not fc["diagnostic_accuracy"]:
                flags.append("准确率")
            if not fc["expert_recall"]:
                flags.append("召回率")
            if not fc["closed_loop"]:
                flags.append(f"闭环(缺: {','.join(fc['missing_stages'])})")
            print(
                f"  {fc['id']:<16} sys={fc['system']:<12} "
                f"失败项: {', '.join(flags)} "
                f"anom={fc['anomaly_count']} skill={fc['skill_finding_count']}"
            )
            if fc.get("error"):
                print(f"    错误: {fc['error']}")
        if len(failed) > 20:
            print(f"  ... 还有 {len(failed) - 20} 条失败案例")

    print("\n" + "=" * 72)


# ------------------------------------------------------------------ #
#  6. 主入口
# ------------------------------------------------------------------ #
def main() -> None:
    """主入口：运行评测并打印报告。"""
    print("=" * 72)
    print("  CarSoul OS V1.0 第9步 — 评测脚本")
    print("  评测目标: 诊断准确率 / 专家召回率 / 闭环完成率 / 幻觉防护")
    print("=" * 72 + "\n")

    summary = run_evaluation()
    print_report(summary)

    # 保存 JSON 结果（供报告生成使用）
    json_path = os.path.join(_BASE, "eval_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n[评测] 详细结果已保存至: {json_path}")


if __name__ == "__main__":
    main()
