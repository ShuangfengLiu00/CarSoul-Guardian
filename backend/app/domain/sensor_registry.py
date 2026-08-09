"""Sensor registry — the single source of truth for the vehicle signal model.

Scope: **58 sensors / 6 domains**, taken verbatim from
``docs/arch-vehicle-data-simulation.md`` §3.3 (the committed Phase-B scope).

  battery 16 | motor 9 | chassis 14 | thermal 7 | environment 7 | can_bus 5

A second design note (``docs/vehicle_sensor_simulation_model.md``, 104 signals /
8 domains) describes a richer superset for a later phase; it is **not**
implemented here and is only used as a reference for generation realism.

This module is consumed by three call sites and must stay DB-free / import-free
of the ORM layer:

  * ``app.services.data_generator``  — mock reading generation
  * ``app.api.vehicle.router``       — ``GET /sensors/snapshot``
  * (later) what-if validation + the frontend simulation panel

Backwards-compatibility contract
--------------------------------
The 12 EV sensor names already produced by ``data_generator._ELECTRIC_SENSORS``
are preserved verbatim, together with their original ``baseline``/``jitter``:

    battery_voltage, battery_temp, battery_level, motor_temp,
    tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr,
    cabin_temp, speed, power_draw, regen_brake

``min``/``max`` are the *adjustable* (slider) range and are normally widened to
cover the ``crit`` thresholds.  For the legacy 12 they are only widened when the
old clamp was statistically unreachable (e.g. ``motor_temp`` 45±10 never hits
120).  Where the old clamp actually shaped the distribution — ``speed``,
``power_draw``, ``regen_brake`` (all baseline-at-or-below-zero with large
jitter) — the original bounds are kept so generated data does not drift.

Tyre pressure / tyre temperature keep the ``_fl/_fr/_rl/_rr`` suffix convention:
``data_generator`` derives ``meta={"position": "FL"}`` from the suffix and the
frontend matches on ``startswith("tire_pressure")``.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Sampling-rate shorthands (Hz). "event"-driven signals are 0.0 by convention.
# ---------------------------------------------------------------------------
_HZ_HOURLY = 0.000278   # 1/h
_HZ_DAILY = 0.0000116   # 1/d
_HZ_EVENT = 0.0         # event / per-trip / not applicable


@dataclass(frozen=True)
class SensorSpec:
    """Static metadata for one sensor signal."""

    sensor_type: str
    label: str
    unit: str
    domain: str
    vhs_component: str
    vhs_weight: float
    min: float
    max: float
    warn_low: float | None
    warn_high: float | None
    crit_low: float | None
    crit_high: float | None
    step: float
    sample_hz_can: float
    sample_hz_upload: float
    baseline: float
    jitter: float
    adjustable: bool


# ---------------------------------------------------------------------------
# Domains.
#
# ``vhs_weight`` is the DOMAIN weight in the existing VHS formula (§3.4):
#     VHS = 0.30·Engine + 0.25·Battery + 0.15·Chassis
#           + 0.15·Driving + 0.15·Maintenance
# Only battery / motor / chassis map onto a VHS component of their own.
# thermal / environment / can_bus have NO VHS component in this phase: they get
# weight 0.0 and borrow a ``vhs_component`` purely so the frontend can colour
# their status chips consistently (thermal → battery, environment/can_bus →
# engine).  Driving and Maintenance are not sensor-derived and stay outside the
# registry.
#
# Insertion order defines the snapshot response order.
# ---------------------------------------------------------------------------
DOMAINS: dict[str, dict] = {
    "battery": {"label": "电池系统", "vhs_component": "battery", "vhs_weight": 0.25},
    "motor": {"label": "电机/驱动", "vhs_component": "engine", "vhs_weight": 0.30},
    "chassis": {"label": "底盘/制动/轮胎", "vhs_component": "chassis", "vhs_weight": 0.15},
    "thermal": {"label": "热管理", "vhs_component": "battery", "vhs_weight": 0.0},
    "environment": {"label": "环境/定位", "vhs_component": "engine", "vhs_weight": 0.0},
    "can_bus": {"label": "CAN总线/网络健康", "vhs_component": "engine", "vhs_weight": 0.0},
}

#: Domains that actually contribute to the baseline health score.
VHS_WEIGHTED_DOMAINS: tuple[str, ...] = ("battery", "motor", "chassis")

SENSOR_REGISTRY: dict[str, SensorSpec] = {}


def _add(
    domain: str,
    sensor_type: str,
    label: str,
    unit: str,
    *,
    lo: float,
    hi: float,
    baseline: float,
    jitter: float,
    step: float,
    hz_can: float,
    hz_up: float,
    warn_low: float | None = None,
    warn_high: float | None = None,
    crit_low: float | None = None,
    crit_high: float | None = None,
    adjustable: bool = True,
) -> None:
    meta = DOMAINS[domain]
    SENSOR_REGISTRY[sensor_type] = SensorSpec(
        sensor_type=sensor_type,
        label=label,
        unit=unit,
        domain=domain,
        vhs_component=meta["vhs_component"],
        vhs_weight=meta["vhs_weight"],
        min=lo,
        max=hi,
        warn_low=warn_low,
        warn_high=warn_high,
        crit_low=crit_low,
        crit_high=crit_high,
        step=step,
        sample_hz_can=hz_can,
        sample_hz_upload=hz_up,
        baseline=baseline,
        jitter=jitter,
        adjustable=adjustable,
    )


# ---------------------------------------------------------------------------
# Domain 1 · 电池系统 battery (16) — VHS 0.25
# ---------------------------------------------------------------------------
_add("battery", "battery_voltage", "动力电池总压", "V",
     lo=320, hi=420, baseline=398, jitter=8, step=0.1, hz_can=10.0, hz_up=1.0,
     warn_low=340, warn_high=415, crit_low=320, crit_high=420)
_add("battery", "battery_current", "电池电流", "A",
     lo=-250, hi=450, baseline=45, jitter=30, step=1, hz_can=10.0, hz_up=1.0,
     warn_high=350, crit_high=400)
_add("battery", "battery_level", "电池电量 SOC", "%",
     lo=0, hi=100, baseline=70, jitter=6, step=0.5, hz_can=1.0, hz_up=0.2,
     warn_low=15, crit_low=5)
_add("battery", "battery_soh", "电池健康度 SOH", "%",
     lo=60, hi=100, baseline=94, jitter=1.5, step=0.1,
     hz_can=0.01, hz_up=_HZ_HOURLY,
     warn_low=85, crit_low=75)
_add("battery", "battery_temp", "电池包平均温度", "℃",
     lo=-20, hi=60, baseline=28, jitter=5, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=45, crit_high=55)
_add("battery", "cell_voltage_min", "单体最低电压", "V",
     lo=2.5, hi=4.3, baseline=3.78, jitter=0.06, step=0.01,
     hz_can=10.0, hz_up=1.0,
     warn_low=3.2, crit_low=2.9)
_add("battery", "cell_voltage_max", "单体最高电压", "V",
     lo=2.5, hi=4.5, baseline=3.85, jitter=0.06, step=0.01,
     hz_can=10.0, hz_up=1.0,
     warn_high=4.20, crit_high=4.30)
_add("battery", "cell_voltage_delta", "单体电压极差", "mV",
     lo=0, hi=300, baseline=32, jitter=8, step=1, hz_can=10.0, hz_up=1.0,
     warn_high=80, crit_high=150)
_add("battery", "cell_temp_min", "单体最低温度", "℃",
     lo=-30, hi=50, baseline=24, jitter=4, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_low=-5, crit_low=-15)
_add("battery", "cell_temp_max", "单体最高温度", "℃",
     lo=-20, hi=70, baseline=31, jitter=4, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=48, crit_high=58)
_add("battery", "cell_temp_delta", "单体温差", "℃",
     lo=0, hi=25, baseline=3.2, jitter=1.0, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=10, crit_high=15)
_add("battery", "internal_resistance", "电池内阻", "mΩ",
     lo=0.5, hi=6.0, baseline=1.4, jitter=0.2, step=0.01,
     hz_can=0.01, hz_up=_HZ_HOURLY,
     warn_high=2.5, crit_high=4.0)
_add("battery", "insulation_resistance", "绝缘电阻", "MΩ",
     lo=0.0, hi=100, baseline=22, jitter=5, step=0.1, hz_can=0.1, hz_up=0.1,
     warn_low=1.0, crit_low=0.5)
_add("battery", "charge_cycles", "累计等效充电循环", "次",
     lo=0, hi=3000, baseline=320, jitter=8, step=1,
     hz_can=_HZ_EVENT, hz_up=_HZ_EVENT,
     warn_high=1500, crit_high=2500)
_add("battery", "fast_charge_ratio", "快充占比", "",
     lo=0, hi=1, baseline=0.35, jitter=0.05, step=0.01,
     hz_can=_HZ_EVENT, hz_up=_HZ_DAILY,
     warn_high=0.6, crit_high=0.8)
_add("battery", "battery_power", "电池瞬时功率", "kW",
     lo=-100, hi=280, baseline=35, jitter=25, step=0.5, hz_can=10.0, hz_up=1.0,
     warn_high=200, crit_high=240)

# ---------------------------------------------------------------------------
# Domain 2 · 电机/驱动 motor (9) — VHS 0.30 (engine)
# ---------------------------------------------------------------------------
_add("motor", "motor_rpm", "电机转速", "rpm",
     lo=0, hi=16000, baseline=2600, jitter=900, step=10,
     hz_can=100.0, hz_up=10.0,
     warn_high=14000, crit_high=15500)
_add("motor", "motor_torque", "电机输出扭矩", "N·m",
     lo=-450, hi=500, baseline=90, jitter=60, step=1, hz_can=100.0, hz_up=10.0,
     warn_high=420, crit_high=450)
_add("motor", "motor_temp", "电机定子绕组温度", "℃",
     lo=0, hi=150, baseline=45, jitter=10, step=0.1, hz_can=10.0, hz_up=1.0,
     warn_high=110, crit_high=130)
_add("motor", "motor_rotor_temp", "电机转子温度", "℃",
     lo=0, hi=170, baseline=52, jitter=10, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=130, crit_high=150)
_add("motor", "inverter_temp", "逆变器 IGBT 结温", "℃",
     lo=0, hi=120, baseline=48, jitter=8, step=0.1, hz_can=10.0, hz_up=1.0,
     warn_high=85, crit_high=100)
_add("motor", "motor_efficiency", "电机效率", "%",
     lo=70, hi=100, baseline=93.5, jitter=1.2, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_low=88, crit_low=82)
_add("motor", "motor_phase_current_imbalance", "三相电流不平衡度", "%",
     lo=0, hi=20, baseline=1.1, jitter=0.4, step=0.1, hz_can=10.0, hz_up=1.0,
     warn_high=5, crit_high=10)
# NOTE: lo/hi kept at the legacy 0..150 clamp — baseline 12 ± 18 relies on it.
_add("motor", "power_draw", "整车功耗", "kW",
     lo=0, hi=150, baseline=12, jitter=18, step=0.5, hz_can=10.0, hz_up=1.0,
     warn_high=140, crit_high=150)
# NOTE: lo/hi kept at the legacy 0..50 clamp — baseline 0 ± 20 relies on it.
_add("motor", "regen_brake", "动能回收功率", "kW",
     lo=0, hi=50, baseline=0, jitter=20, step=0.5, hz_can=10.0, hz_up=1.0)

# ---------------------------------------------------------------------------
# Domain 3 · 底盘/制动/轮胎 chassis (14) — VHS 0.15
# ---------------------------------------------------------------------------
for _pos, _cn, _tp_base in (
    ("fl", "左前", 2.5),
    ("fr", "右前", 2.5),
    ("rl", "左后", 2.4),
    ("rr", "右后", 2.4),
):
    _add("chassis", f"tire_pressure_{_pos}", f"{_cn}胎压", "bar",
         lo=1.5, hi=3.5, baseline=_tp_base, jitter=0.1, step=0.05,
         hz_can=0.1, hz_up=0.02,
         warn_low=2.0, warn_high=3.0, crit_low=1.8, crit_high=3.2)
for _pos, _cn in (("fl", "左前"), ("fr", "右前"), ("rl", "左后"), ("rr", "右后")):
    _add("chassis", f"tire_temp_{_pos}", f"{_cn}胎温", "℃",
         lo=0, hi=110, baseline=34, jitter=6, step=0.5,
         hz_can=0.1, hz_up=0.02,
         warn_high=75, crit_high=90)
del _pos, _cn, _tp_base

_add("chassis", "brake_pad_wear_front", "前制动片磨损率", "%",
     lo=0, hi=100, baseline=32, jitter=4, step=1,
     hz_can=_HZ_EVENT, hz_up=_HZ_EVENT,
     warn_high=70, crit_high=85)
_add("chassis", "brake_pad_wear_rear", "后制动片磨损率", "%",
     lo=0, hi=100, baseline=26, jitter=4, step=1,
     hz_can=_HZ_EVENT, hz_up=_HZ_EVENT,
     warn_high=70, crit_high=85)
_add("chassis", "brake_fluid_level", "制动液液位", "%",
     lo=0, hi=100, baseline=88, jitter=3, step=1, hz_can=1.0, hz_up=0.2,
     warn_low=50, crit_low=30)
_add("chassis", "suspension_travel_var", "悬架行程方差", "mm",
     lo=0, hi=100, baseline=18, jitter=5, step=0.5, hz_can=10.0, hz_up=1.0,
     warn_high=55, crit_high=70)
_add("chassis", "steering_angle", "方向盘转角", "°",
     lo=-540, hi=540, baseline=0, jitter=45, step=1, hz_can=100.0, hz_up=10.0)
_add("chassis", "wheel_speed_delta", "轮速差", "km/h",
     lo=0, hi=15, baseline=0.6, jitter=0.3, step=0.1, hz_can=100.0, hz_up=10.0,
     warn_high=4, crit_high=8)

# ---------------------------------------------------------------------------
# Domain 4 · 热管理 thermal (7) — no VHS weight
# ---------------------------------------------------------------------------
_add("thermal", "coolant_temp_inlet", "电池冷却入口温度", "℃",
     lo=0, hi=80, baseline=29, jitter=4, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=50, crit_high=60)
_add("thermal", "coolant_temp_outlet", "电池冷却出口温度", "℃",
     lo=0, hi=85, baseline=34, jitter=4, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=55, crit_high=65)
_add("thermal", "coolant_flow_rate", "冷却液流量", "L/min",
     lo=0, hi=30, baseline=12, jitter=2, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_low=4, crit_low=2)
_add("thermal", "compressor_power", "空调压缩机功耗", "kW",
     lo=0, hi=8, baseline=1.8, jitter=0.8, step=0.1, hz_can=1.0, hz_up=0.2,
     warn_high=5.5, crit_high=6.5)
# 0=off 1=cool 2=heat 3=defrost
_add("thermal", "heat_pump_mode", "热泵工作模式", "",
     lo=0, hi=3, baseline=1, jitter=0.6, step=1, hz_can=0.1, hz_up=0.1)
_add("thermal", "chiller_active", "电池主动冷却启停", "",
     lo=0, hi=1, baseline=0, jitter=0.4, step=1, hz_can=0.1, hz_up=0.1)
_add("thermal", "cabin_temp", "座舱温度", "℃",
     lo=0, hi=40, baseline=23, jitter=3, step=0.1, hz_can=0.1, hz_up=0.1)

# ---------------------------------------------------------------------------
# Domain 5 · 环境/定位 environment (7) — no VHS weight
# GPS signals are compliance-sensitive (§6) and are NOT panel-adjustable.
# ---------------------------------------------------------------------------
# NOTE: lo/hi kept at the legacy 0..200 clamp — baseline 0 ± 60 relies on it.
_add("environment", "speed", "车速", "km/h",
     lo=0, hi=200, baseline=0, jitter=60, step=1, hz_can=10.0, hz_up=1.0,
     warn_high=120, crit_high=160)
_add("environment", "gps_latitude", "GPS 纬度", "°",
     lo=-90, hi=90, baseline=31.2304, jitter=0.05, step=0.0001,
     hz_can=1.0, hz_up=0.1, adjustable=False)
_add("environment", "gps_longitude", "GPS 经度", "°",
     lo=-180, hi=180, baseline=121.4737, jitter=0.05, step=0.0001,
     hz_can=1.0, hz_up=0.1, adjustable=False)
_add("environment", "gps_altitude", "GPS 海拔", "m",
     lo=-100, hi=5500, baseline=12, jitter=6, step=1,
     hz_can=1.0, hz_up=0.1, adjustable=False)
_add("environment", "heading", "航向角", "°",
     lo=0, hi=360, baseline=180, jitter=90, step=1,
     hz_can=1.0, hz_up=0.1, adjustable=False)
_add("environment", "ambient_temp", "环境温度", "℃",
     lo=-40, hi=55, baseline=22, jitter=6, step=0.1, hz_can=0.1, hz_up=0.1,
     warn_low=-25, warn_high=45, crit_low=-35, crit_high=50)
_add("environment", "ambient_humidity", "环境湿度", "%",
     lo=0, hi=100, baseline=58, jitter=10, step=1, hz_can=0.1, hz_up=0.1,
     warn_high=90)

# ---------------------------------------------------------------------------
# Domain 6 · CAN 总线/网络健康 can_bus (5) — no VHS weight
# ---------------------------------------------------------------------------
_add("can_bus", "can_bus_load", "CAN 总线负载率", "%",
     lo=0, hi=100, baseline=38, jitter=6, step=1, hz_can=1.0, hz_up=0.2,
     warn_high=75, crit_high=90)
_add("can_bus", "can_error_frames", "CAN 错误帧计数", "帧/min",
     lo=0, hi=500, baseline=1, jitter=1, step=1, hz_can=1.0, hz_up=0.2,
     warn_high=20, crit_high=100)
_add("can_bus", "can_node_timeouts", "CAN 节点掉线次数", "次/min",
     lo=0, hi=50, baseline=0, jitter=0.4, step=1, hz_can=1.0, hz_up=0.2,
     warn_high=3, crit_high=10)
_add("can_bus", "dtc_active_count", "活跃故障码数", "个",
     lo=0, hi=30, baseline=1, jitter=0.8, step=1,
     hz_can=_HZ_EVENT, hz_up=_HZ_EVENT,
     warn_high=5, crit_high=10)
_add("can_bus", "gateway_latency", "网关转发时延", "ms",
     lo=1, hi=300, baseline=8, jitter=3, step=1, hz_can=1.0, hz_up=0.2,
     warn_high=50, crit_high=120)


#: The 12 EV sensors that existed before the registry (kept for regression
#: checks and for callers that need the legacy subset).
LEGACY_EV_SENSORS: tuple[str, ...] = (
    "battery_voltage", "battery_temp", "battery_level", "motor_temp",
    "tire_pressure_fl", "tire_pressure_fr", "tire_pressure_rl",
    "tire_pressure_rr", "cabin_temp", "speed", "power_draw", "regen_brake",
)

#: The 12 legacy fuel sensors (``data_generator._FUEL_SENSORS``).  Only the
#: entries that also exist in ``SENSOR_REGISTRY`` can be served with spec
#: metadata — combustion-only signals (engine_temp, rpm, fuel_level, …) are
#: intentionally out of the 58-sensor EV scope and keep using the legacy
#: blueprint inside ``data_generator``.
LEGACY_FUEL_SENSORS: tuple[str, ...] = (
    "engine_temp", "coolant_temp", "oil_pressure", "rpm", "fuel_level",
    "battery_voltage", "tire_pressure_fl", "tire_pressure_fr",
    "tire_pressure_rl", "tire_pressure_rr", "intake_air_temp", "speed",
)


def get_registry(energy_type: str) -> list[SensorSpec]:
    """Return the sensor specs to generate / expose for an energy type.

    ``electric`` → all 58 registry entries (in domain order).
    Anything else (``fuel`` / ``hybrid`` / ``plug_in_hybrid`` / unknown) →
    the subset of :data:`LEGACY_FUEL_SENSORS` that the registry can describe.
    """
    if energy_type == "electric":
        return list(SENSOR_REGISTRY.values())
    return [
        SENSOR_REGISTRY[name]
        for name in LEGACY_FUEL_SENSORS
        if name in SENSOR_REGISTRY
    ]


def get_domain_specs(domains: list[str] | None = None) -> dict[str, list[SensorSpec]]:
    """Group EV specs by domain, optionally filtered to ``domains``."""
    keys = [d for d in DOMAINS if domains is None or d in domains]
    return {
        key: [s for s in SENSOR_REGISTRY.values() if s.domain == key]
        for key in keys
    }


def classify(spec: SensorSpec, value: float) -> str:
    """Return ``"normal"`` | ``"warn"`` | ``"crit"`` for a reading."""
    if spec.crit_low is not None and value <= spec.crit_low:
        return "crit"
    if spec.crit_high is not None and value >= spec.crit_high:
        return "crit"
    if spec.warn_low is not None and value <= spec.warn_low:
        return "warn"
    if spec.warn_high is not None and value >= spec.warn_high:
        return "warn"
    return "normal"
