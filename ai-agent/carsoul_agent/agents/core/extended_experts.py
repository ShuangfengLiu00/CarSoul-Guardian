"""Extended multi-agent expert panel for the AI Vehicle Doctor.

This module extends the core five-specialist panel (see ``experts.py``)
with five additional domain experts, broadening the multi-agent
consultation coverage:

  6. VehicleValueExpert          — 车辆价值 (折旧 / 保值率 / 残值)
  7. EnvironmentAdaptationExpert — 环境适应 (温度 / 天气 / 路况)
  8. ChargingIntelligenceExpert  — 充电智能 (SOC / 充电策略)
  9. EnergyOptimizationExpert   — 能耗优化 (驾驶风格 / 能效)
 10. UserCompanionExpert        — 用户陪伴 (偏好 / 个性化建议)

Each expert inherits from :class:`ExpertAgent` and follows the exact
same contract (``consult`` → ``_analyse`` → ``_recommendation``) so it
can be dropped into the existing panel orchestration without changes.

The experts are intentionally pure-Python and offline-capable. When an
LLM client is configured, each expert can enrich its opinion with
natural-language reasoning via the inherited ``_llm_enrich`` hook;
otherwise rule-based / domain-signal mode is used.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from carsoul_agent.agents.core.experts import ExpertAgent, build_expert_panel
from carsoul_agent.agents.core.state import AgentState

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def _years_since(date_val: Any) -> float:
    """Return the number of years between *date_val* and now.

    Accepts ``YYYY-MM-DD``, ``YYYY/MM/DD``, ``YYYYMMDD`` strings or
    ``datetime`` objects. Returns ``0.0`` when the input is missing or
    cannot be parsed — callers should treat ``0.0`` as "unknown age".
    """
    if date_val is None:
        return 0.0
    if isinstance(date_val, datetime):
        return max((datetime.now() - date_val).total_seconds() / (365.25 * 86400), 0.0)
    if isinstance(date_val, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                dt = datetime.strptime(date_val.strip(), fmt)
                return max((datetime.now() - dt).total_seconds() / (365.25 * 86400), 0.0)
            except ValueError:
                continue
    return 0.0


# ------------------------------------------------------------------ #
#  6. 车辆价值专家
# ------------------------------------------------------------------ #
class VehicleValueExpert(ExpertAgent):
    """车辆价值专家 — 折旧 / 保值率 / 残值.

    Estimates the current vehicle value by applying annual depreciation
    (petrol ~8 %/yr, EV ~10 %/yr), mileage depreciation (~3-5 % per
    10 000 km), and a health-score penalty when ``health_score`` < 60.
    """

    name = "value_expert"
    specialty = "车辆价值"
    categories = ("value", "depreciation", "asset")
    description = "评估车辆折旧、保值率与残值，基于里程、车龄、健康分与能源类型估算当前估值。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        vehicle = state.get("vehicle_state", {})
        purchase_price = vehicle.get("purchase_price")
        purchase_date = vehicle.get("purchase_date")
        mileage = vehicle.get("mileage")
        health_score = vehicle.get("health_score")
        energy_type = vehicle.get("energy_type", "petrol")

        is_ev = energy_type in ("ev", "electric", "bev")
        annual_rate = 0.10 if is_ev else 0.08
        years = _years_since(purchase_date)

        # --- current value estimation --------------------------------
        estimated_value = None
        value_components: dict[str, Any] = {}

        if isinstance(purchase_price, (int, float)) and purchase_price > 0:
            current_value = float(purchase_price)

            # Annual depreciation.
            if years > 0:
                annual_depreciation = current_value * annual_rate * years
                current_value -= annual_depreciation
                value_components["years_owned"] = round(years, 1)
                value_components["annual_rate"] = annual_rate
                value_components["annual_depreciation"] = round(annual_depreciation, 2)

            # Mileage depreciation: ~3-5 % per 10 000 km (4 % midpoint).
            if isinstance(mileage, (int, float)) and mileage > 0:
                mileage_blocks = int(mileage) // 10000
                mileage_rate = 0.04
                mileage_depreciation = current_value * mileage_rate * mileage_blocks
                current_value -= mileage_depreciation
                value_components["mileage"] = mileage
                value_components["mileage_blocks"] = mileage_blocks
                value_components["mileage_rate"] = mileage_rate
                value_components["mileage_depreciation"] = round(mileage_depreciation, 2)

            # Health-score penalty: 5 % (60-40) or 10 % (<40).
            if isinstance(health_score, (int, float)) and health_score < 60:
                penalty_rate = 0.10 if health_score < 40 else 0.05
                penalty_value = current_value * penalty_rate
                current_value -= penalty_value
                value_components["health_score"] = health_score
                value_components["health_penalty_rate"] = penalty_rate
                value_components["health_penalty"] = round(penalty_value, 2)

            estimated_value = max(current_value, 0.0)
            value_components["estimated_value"] = round(estimated_value, 2)
            value_components["purchase_price"] = purchase_price

            findings.append({
                "type": "vehicle_valuation",
                "root_cause": "车辆价值评估",
                "severity": "info",
                "description": (
                    f"当前估算价值约 {round(estimated_value, 0):.0f} 元"
                    f"（原价 {purchase_price} 元），能源类型 {energy_type}，"
                    f"已使用 {value_components.get('years_owned', 0)} 年。"
                ),
                "recommendation": "定期关注残值变化，适时评估置换或出售时机。",
                "evidence": value_components,
                "confidence": 0.7,
                "source": "domain_signal",
            })

        # --- high depreciation rate (EV) -----------------------------
        if years > 0 and is_ev:
            findings.append({
                "type": "high_depreciation_rate",
                "root_cause": "电动车折旧率较高",
                "severity": "low",
                "description": (
                    f"电动车年折旧率约 {annual_rate * 100:.0f}%，"
                    f"保值率低于燃油车，已使用 {round(years, 1)} 年。"
                ),
                "recommendation": "关注电池健康与续航，电池衰减将加速残值下降。",
                "evidence": {"annual_rate": annual_rate, "years_owned": round(years, 1)},
                "confidence": 0.75,
                "source": "domain_signal",
            })

        # --- health-score penalty ------------------------------------
        if isinstance(health_score, (int, float)) and health_score < 60:
            penalty_desc = "额外折旧5-10%" if health_score >= 40 else "额外折旧10%以上"
            findings.append({
                "type": "health_penalty_depreciation",
                "root_cause": "健康分偏低导致额外折旧",
                "severity": "medium" if health_score < 40 else "low",
                "description": (
                    f"综合健康分 {health_score}/100，低于60，残值存在{penalty_desc}。"
                ),
                "recommendation": "修复高风险子系统以提升健康分，减缓残值下降。",
                "evidence": {"health_score": health_score},
                "confidence": 0.7,
                "source": "domain_signal",
            })

        # --- high mileage depreciation -------------------------------
        if isinstance(mileage, (int, float)) and mileage >= 100000:
            findings.append({
                "type": "high_mileage_depreciation",
                "root_cause": "高里程加速折旧",
                "severity": "low",
                "description": (
                    f"累计里程 {int(mileage)} km，超过 10 万公里，"
                    "每增加 1 万 km 价值下降约 3-5%。"
                ),
                "recommendation": "高里程车辆关注核心部件状态，评估置换时机。",
                "evidence": {"mileage": mileage},
                "confidence": 0.65,
                "source": "domain_signal",
            })

        return findings


# ------------------------------------------------------------------ #
#  7. 环境适应专家
# ------------------------------------------------------------------ #
class EnvironmentAdaptationExpert(ExpertAgent):
    """环境适应专家 — 温度 / 天气 / 路况.

    Evaluates how ambient temperature affects the vehicle, especially
    battery range (cold <0 ℃: −15~30 %; hot >35 ℃: thermal-management
    stress). Long trips amplify the environmental impact.
    """

    name = "environment_expert"
    specialty = "环境适应"
    categories = ("environment", "weather", "temperature", "road")
    description = "分析环境温度与路况对车辆（特别是电池与续航）的影响，长途出行时放大评估。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        sensor_window = state.get("sensor_window", [])
        trip_context = state.get("trip_context", {})

        # Derive the latest ambient temperature from sensor readings.
        ambient_temp = None
        if sensor_window:
            latest = sensor_window[-1] if sensor_window else {}
            ambient_temp = latest.get("ambient_temp") or latest.get("environment_temp")

        # Determine whether this is a long trip (amplifies impact).
        distance_km = trip_context.get("distance_km")
        is_long_trip = isinstance(distance_km, (int, float)) and distance_km > 200

        # --- cold-temperature impact (< 0 ℃) ------------------------
        if isinstance(ambient_temp, (int, float)) and ambient_temp < 0:
            range_loss = 30 if ambient_temp < -10 else 15
            amplification = ""
            if is_long_trip:
                amplification = "长途出行时影响进一步放大，建议增加中途充电/休息频次。"
            findings.append({
                "type": "cold_temperature_impact",
                "root_cause": "低温环境导致电池续航下降",
                "severity": "medium",
                "description": (
                    f"当前环境温度 {ambient_temp}°C，"
                    f"电池续航预计下降约 {range_loss}%。{amplification}"
                ),
                "recommendation": (
                    "低温环境下提前规划充电，减少空调制热功率，"
                    "停车尽量选择室内或避风处。"
                ),
                "evidence": {
                    "ambient_temp": ambient_temp,
                    "range_loss_pct": range_loss,
                    "is_long_trip": is_long_trip,
                },
                "confidence": 0.8,
                "source": "domain_signal",
            })

        # --- high-temperature impact (> 35 ℃) -----------------------
        if isinstance(ambient_temp, (int, float)) and ambient_temp > 35:
            amplification = ""
            if is_long_trip:
                amplification = "长途出行热管理压力增大，建议增加中途冷却休息。"
            findings.append({
                "type": "high_temperature_impact",
                "root_cause": "高温环境增加电池热管理压力",
                "severity": "medium",
                "description": (
                    f"当前环境温度 {ambient_temp}°C，"
                    f"电池热管理系统负荷升高。{amplification}"
                ),
                "recommendation": (
                    "高温天气避免长时间暴晒后立即快充，"
                    "行驶中注意水温/电池温度报警。"
                ),
                "evidence": {
                    "ambient_temp": ambient_temp,
                    "is_long_trip": is_long_trip,
                },
                "confidence": 0.75,
                "source": "domain_signal",
            })

        # --- long-trip amplification (no extreme temp) --------------
        if is_long_trip and not findings:
            findings.append({
                "type": "long_trip_environment_note",
                "root_cause": "长途出行需关注环境适应",
                "severity": "info",
                "description": (
                    f"长途出行距离 {distance_km} km，"
                    "建议出发前确认天气与路况，沿途规划补给点。"
                ),
                "recommendation": "出发前检查轮胎、雨刮、灯光及冷却液状态。",
                "evidence": {"distance_km": distance_km},
                "confidence": 0.6,
                "source": "domain_signal",
            })

        return findings


# ------------------------------------------------------------------ #
#  8. 充电智能专家
# ------------------------------------------------------------------ #
class ChargingIntelligenceExpert(ExpertAgent):
    """充电智能专家 — SOC / 充电策略.

    Inspects the state-of-charge (SOC) trajectory and charging habits,
    flagging low SOC (<20 %), frequent fast-charging, and habitual
    100 % charging. Recommends the 20-80 % optimal charging window.
    """

    name = "charging_expert"
    specialty = "充电智能"
    categories = ("charging", "energy", "soc")
    description = "分析充电习惯与SOC状态，给出充电策略建议（最佳区间20%-80%）。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        sensor_window = state.get("sensor_window", [])
        vehicle = state.get("vehicle_state", {})

        # Collect SOC trajectory from sensor window.
        latest_soc = None
        soc_values: list[float] = []
        if sensor_window:
            for reading in sensor_window:
                soc = reading.get("soc")
                if isinstance(soc, (int, float)):
                    soc_values.append(float(soc))
            if soc_values:
                latest_soc = soc_values[-1]

        # --- low SOC detection (< 20 %) ------------------------------
        if isinstance(latest_soc, (int, float)) and latest_soc < 20:
            severity = "high" if latest_soc < 10 else "medium"
            findings.append({
                "type": "low_soc_warning",
                "root_cause": "电量过低",
                "severity": severity,
                "description": (
                    f"当前 SOC 仅 {latest_soc}%，"
                    "低于安全阈值 20%，深度放电将损害电池寿命。"
                ),
                "recommendation": "立即充电至 20% 以上，避免长时间低电量停放。",
                "evidence": {"soc": latest_soc},
                "confidence": 0.85,
                "source": "domain_signal",
            })

        # --- habitual full charging (SOC frequently >= 95 %) --------
        if soc_values:
            full_charge_count = sum(1 for s in soc_values if s >= 95)
            full_charge_ratio = full_charge_count / len(soc_values)
            if full_charge_ratio >= 0.6:
                findings.append({
                    "type": "frequent_full_charge",
                    "root_cause": "频繁充至满电",
                    "severity": "low",
                    "description": (
                        f"近期 {full_charge_count}/{len(soc_values)} 次读数"
                        " SOC≥95%，长期满充加速电池循环衰减。"
                    ),
                    "recommendation": "日常使用建议充至 80% 即可，长途出行前再充满。",
                    "evidence": {
                        "full_charge_ratio": round(full_charge_ratio, 2),
                        "sample_count": len(soc_values),
                    },
                    "confidence": 0.7,
                    "source": "domain_signal",
                })

        # --- frequent fast-charging pattern -------------------------
        charging_pattern = vehicle.get("charging_pattern")
        if charging_pattern == "frequent_fast_charge":
            findings.append({
                "type": "frequent_fast_charge",
                "root_cause": "频繁使用快充",
                "severity": "medium",
                "description": "频繁快充会加速电池热应力与化学老化。",
                "recommendation": "日常通勤使用慢充，快充仅用于长途或紧急补电场景。",
                "evidence": {"charging_pattern": charging_pattern},
                "confidence": 0.7,
                "source": "domain_signal",
            })

        # --- SOC within optimal range (positive feedback) ----------
        if isinstance(latest_soc, (int, float)) and 20 <= latest_soc <= 80 and not findings:
            findings.append({
                "type": "soc_optimal_range",
                "root_cause": "电量处于最佳区间",
                "severity": "info",
                "description": f"当前 SOC {latest_soc}%，处于 20%-80% 最佳区间。",
                "recommendation": "保持当前充电习惯，有利于延长电池寿命。",
                "evidence": {"soc": latest_soc},
                "confidence": 0.8,
                "source": "domain_signal",
            })

        return findings


# ------------------------------------------------------------------ #
#  9. 能耗优化专家
# ------------------------------------------------------------------ #
class EnergyOptimizationExpert(ExpertAgent):
    """能耗优化专家 — 驾驶风格 / 能效.

    Correlates driving style with energy waste. Aggressive driving
    adds ~15-25 % energy consumption; the expert gives tailored
    eco-driving recommendations based on the driver profile.
    """

    name = "energy_expert"
    specialty = "能耗优化"
    categories = ("energy", "consumption", "efficiency")
    description = "结合驾驶风格评估能耗浪费，给出节能驾驶建议（激烈风格增加15-25%能耗）。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        profile = state.get("driver_profile", {})
        style = profile.get("driving_style", "balanced")
        eco_score = profile.get("eco_score")

        # --- driving-style energy impact -----------------------------
        if style == "aggressive":
            energy_increase = 25
            findings.append({
                "type": "aggressive_driving_energy_waste",
                "root_cause": "激烈驾驶风格导致能耗增加",
                "severity": "medium",
                "description": (
                    f"激烈驾驶（急加速/高速行驶）预计增加约 {energy_increase}% 能耗，"
                    "同时加剧刹车与轮胎磨损。"
                ),
                "recommendation": (
                    "平稳加速、预判减速、保持经济时速（60-80 km/h）"
                    "可降低 15-25% 能耗。"
                ),
                "evidence": {"driving_style": style, "energy_increase_pct": energy_increase},
                "confidence": 0.8,
                "source": "domain_signal",
            })
        elif style == "sporty":
            energy_increase = 15
            findings.append({
                "type": "sporty_driving_energy_waste",
                "root_cause": "运动风格驾驶增加能耗",
                "severity": "low",
                "description": (
                    f"运动风格驾驶预计增加约 {energy_increase}% 能耗。"
                ),
                "recommendation": "适当切换经济模式，在高速路段使用定速巡航。",
                "evidence": {"driving_style": style, "energy_increase_pct": energy_increase},
                "confidence": 0.75,
                "source": "domain_signal",
            })
        elif style == "eco":
            findings.append({
                "type": "eco_driving_efficient",
                "root_cause": "节能驾驶习惯良好",
                "severity": "info",
                "description": "节能驾驶风格，能耗利用率高，对部件寿命友好。",
                "recommendation": "保持当前驾驶习惯，定期检查胎压进一步优化能耗。",
                "evidence": {"driving_style": style},
                "confidence": 0.8,
                "source": "domain_signal",
            })

        # --- low eco score ------------------------------------------
        if isinstance(eco_score, (int, float)) and eco_score < 70:
            severity = "medium" if eco_score < 50 else "low"
            findings.append({
                "type": "low_eco_score",
                "root_cause": "节能评分偏低",
                "severity": severity,
                "description": (
                    f"近期节能评分 {eco_score}/100，"
                    "存在可优化的能耗浪费行为（如怠速过长、空调过冷）。"
                ),
                "recommendation": (
                    "减少长时间怠速，合理使用空调，"
                    "规划路线避免拥堵路段。"
                ),
                "evidence": {"eco_score": eco_score},
                "confidence": 0.7,
                "source": "domain_signal",
            })

        return findings


# ------------------------------------------------------------------ #
#  10. 用户陪伴专家
# ------------------------------------------------------------------ #
class UserCompanionExpert(ExpertAgent):
    """用户陪伴专家 — 偏好 / 个性化建议.

    Provides personalised, user-centric guidance based on driving
    style and stated preferences. Tailors the emphasis (safety,
    economy, or convenience) to each user's profile.
    """

    name = "companion_expert"
    specialty = "用户陪伴"
    categories = ("user", "preference", "companion")
    description = "基于驾驶风格与用户偏好提供个性化陪伴建议，关注安全、经济、便利等维度。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        profile = state.get("driver_profile", {})
        style = profile.get("driving_style", "balanced")
        safety_score = profile.get("safety_score")
        eco_score = profile.get("eco_score")
        preference = profile.get("preference") or profile.get("concern")
        vehicle = state.get("vehicle_state", {})
        energy_type = vehicle.get("energy_type", "petrol")

        # --- style-based personalised advice ------------------------
        if style == "eco":
            ev_note = (
                "电动车用户建议利用动能回收提升能效。"
                if energy_type in ("ev", "electric", "bev")
                else "燃油车用户建议保持合理转速降低油耗。"
            )
            findings.append({
                "type": "eco_user_companion",
                "root_cause": "节能型用户陪伴",
                "severity": "info",
                "description": (
                    "您偏好节能驾驶，当前习惯有助于延长续航与部件寿命。"
                    f"{ev_note}"
                ),
                "recommendation": "继续保持节能习惯，可关注能耗趋势榜单获取正向反馈。",
                "evidence": {"driving_style": style, "energy_type": energy_type},
                "confidence": 0.8,
                "source": "domain_signal",
            })
        elif style == "aggressive":
            findings.append({
                "type": "aggressive_user_companion",
                "root_cause": "激烈型用户安全陪伴",
                "severity": "medium",
                "description": (
                    "激烈驾驶风格下安全风险上升，急刹与高速工况对车辆损耗较大。"
                ),
                "recommendation": (
                    "建议在市区采用平稳模式，激烈驾驶留至赛道或封闭场地。"
                    "关注安全评分变化趋势。"
                ),
                "evidence": {"driving_style": style},
                "confidence": 0.75,
                "source": "domain_signal",
            })
        elif style == "sporty":
            findings.append({
                "type": "sporty_user_companion",
                "root_cause": "运动型用户陪伴",
                "severity": "low",
                "description": "运动风格驾驶带来乐趣，但需关注能耗与磨损。",
                "recommendation": "建议定期检查刹车与轮胎状态，合理使用运动模式。",
                "evidence": {"driving_style": style},
                "confidence": 0.7,
                "source": "domain_signal",
            })
        else:
            # balanced
            findings.append({
                "type": "balanced_user_companion",
                "root_cause": "均衡型用户陪伴",
                "severity": "info",
                "description": "均衡驾驶风格，在安全与经济之间取得良好平衡。",
                "recommendation": "保持当前习惯，可尝试节能驾驶技巧进一步优化。",
                "evidence": {"driving_style": style},
                "confidence": 0.8,
                "source": "domain_signal",
            })

        # --- preference-based dimension focus -----------------------
        if preference:
            if preference in ("safety", "安全"):
                if isinstance(safety_score, (int, float)) and safety_score < 80:
                    findings.append({
                        "type": "safety_focused_companion",
                        "root_cause": "用户关注安全，当前评分需提升",
                        "severity": "medium",
                        "description": (
                            f"您关注安全维度，当前安全评分 {safety_score}/100，"
                            "建议关注急刹与超速事件。"
                        ),
                        "recommendation": "开启安全驾驶提醒，减少急刹与分心驾驶。",
                        "evidence": {"preference": preference, "safety_score": safety_score},
                        "confidence": 0.75,
                        "source": "domain_signal",
                    })
            elif preference in ("economy", "经济", "cost", "成本"):
                if isinstance(eco_score, (int, float)) and eco_score < 80:
                    findings.append({
                        "type": "economy_focused_companion",
                        "root_cause": "用户关注经济，能耗仍有优化空间",
                        "severity": "low",
                        "description": (
                            f"您关注经济维度，当前节能评分 {eco_score}/100，"
                            "存在能耗优化空间。"
                        ),
                        "recommendation": "参考节能驾驶建议，预计可降低 10-15% 油耗/电耗。",
                        "evidence": {"preference": preference, "eco_score": eco_score},
                        "confidence": 0.7,
                        "source": "domain_signal",
                    })
            elif preference in ("convenience", "便利", "comfort", "舒适"):
                findings.append({
                    "type": "convenience_focused_companion",
                    "root_cause": "用户关注便利维度",
                    "severity": "info",
                    "description": "您关注出行便利，建议利用智能规划减少等待时间。",
                    "recommendation": "使用预约充电/预热功能，提前规划出行路线。",
                    "evidence": {"preference": preference},
                    "confidence": 0.65,
                    "source": "domain_signal",
                })

        return findings


# ------------------------------------------------------------------ #
#  Extended panel orchestration
# ------------------------------------------------------------------ #
def build_extended_expert_panel(
    llm_client: Any | None = None,
    model_name: str = "gpt-4o-mini",
) -> list[ExpertAgent]:
    """Instantiate the five extended specialist agents for a consultation.

    Returns the five experts defined in this module:
    VehicleValue, EnvironmentAdaptation, ChargingIntelligence,
    EnergyOptimization, UserCompanion.
    """
    return [
        VehicleValueExpert(llm_client=llm_client, model_name=model_name),
        EnvironmentAdaptationExpert(llm_client=llm_client, model_name=model_name),
        ChargingIntelligenceExpert(llm_client=llm_client, model_name=model_name),
        EnergyOptimizationExpert(llm_client=llm_client, model_name=model_name),
        UserCompanionExpert(llm_client=llm_client, model_name=model_name),
    ]


def build_full_expert_panel(
    llm_client: Any | None = None,
    model_name: str = "gpt-4o-mini",
) -> list[ExpertAgent]:
    """Instantiate the full ten-expert panel (core + extended).

    Combines the original five specialists from ``experts.py``
    (Powertrain, Chassis, Electrical, DrivingBehavior, Maintenance)
    with the five extended experts defined in this module, yielding a
    ten-expert consultation panel.
    """
    return (
        build_expert_panel(llm_client=llm_client, model_name=model_name)
        + build_extended_expert_panel(llm_client=llm_client, model_name=model_name)
    )
