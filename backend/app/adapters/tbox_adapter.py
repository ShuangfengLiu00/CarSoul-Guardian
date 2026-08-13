"""T-BOX 适配层 — 62 信号注册表 + 4 级降级 + 5 频率层缓存。

基于 SPEC 附录 C（62 信号）+ 附录 D（8 DTC）+ ADR-002。
上层 Agent 不感知数据源差异，confidence 透传到 AgentResult。
MVP 阶段 _live_available=False（WARN-01），全部走 mock。
纯标准库实现，无外部依赖（架构 §4.7）。
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Optional


class DataSource(Enum):
    LIVE = "live"
    CACHED = "cached"
    MOCK = "mock"
    UNAVAILABLE = "unavailable"


@dataclass
class TelemetryReading:
    """T-BOX 信号读数信封。confidence: live=1.0/cached=0.7/mock=0.3/none=0.0。"""

    signal_id: str
    value: Any
    unit: str
    timestamp: float
    data_source: DataSource
    confidence: float
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class DTCReading:
    """DTC 异常码读数。"""

    code: str
    system: str
    severity: str
    description: str
    timestamp: float
    data_source: DataSource
    confidence: float = 0.3


# signal_id: (group, frequency_tier, (min_val, max_val, unit))
SIGNAL_REGISTRY: dict[str, tuple[str, str, tuple[float, float, str]]] = {
    # ── 电池组 (20) ──
    "battery_soh":           ("battery", "L4", (0, 100, "%")),
    "battery_soc":           ("battery", "L2", (0, 100, "%")),
    "cell_voltage_max":      ("battery", "L1", (2.5, 4.2, "V")),
    "cell_voltage_min":      ("battery", "L1", (2.5, 4.2, "V")),
    "cell_voltage_avg":      ("battery", "L1", (2.5, 4.2, "V")),
    "pack_voltage":          ("battery", "L1", (300, 450, "V")),
    "battery_current":       ("battery", "L1", (-300, 300, "A")),
    "battery_temp_max":      ("battery", "L2", (-20, 80, "degC")),
    "battery_temp_min":      ("battery", "L2", (-20, 80, "degC")),
    "battery_temp_avg":      ("battery", "L2", (-20, 80, "degC")),
    "cycle_count":           ("battery", "L4", (0, 10000, "count")),
    "charge_count_fast":     ("battery", "L4", (0, 5000, "count")),
    "charge_count_slow":     ("battery", "L4", (0, 5000, "count")),
    "internal_resistance":   ("battery", "L4", (0, 100, "mOhm")),
    "insulation_resistance": ("battery", "L4", (0, 1000, "kOhm")),
    "contactor_status":      ("battery", "L2", (0, 1, "bool")),
    "thermal_mgmt_status":   ("battery", "L2", (0, 3, "enum")),
    "balance_status":        ("battery", "L2", (0, 1, "bool")),
    "soh_trend_30d":         ("battery", "L4", (-5, 0, "%")),
    "energy_throughput":     ("battery", "L4", (0, 500000, "kWh")),
    # ── 动力系统 (15) ──
    "motor_rpm":             ("powertrain", "L1", (-15000, 15000, "rpm")),
    "motor_torque":          ("powertrain", "L1", (-400, 400, "Nm")),
    "motor_temp":            ("powertrain", "L2", (-20, 150, "degC")),
    "motor_power":           ("powertrain", "L1", (-200, 200, "kW")),
    "inverter_temp":         ("powertrain", "L2", (-20, 120, "degC")),
    "dcdc_status":           ("powertrain", "L2", (0, 1, "bool")),
    "obc_status":            ("powertrain", "L2", (0, 1, "bool")),
    "gear_position":         ("powertrain", "L1", (0, 6, "enum")),
    "accel_pedal_pos":       ("powertrain", "L1", (0, 100, "%")),
    "brake_pedal_pos":       ("powertrain", "L1", (0, 100, "%")),
    "regen_brake_power":     ("powertrain", "L1", (-100, 0, "kW")),
    "drive_mode":            ("powertrain", "L2", (0, 3, "enum")),
    "power_distribution":    ("powertrain", "L2", (0, 100, "%")),
    "torque_limit_flag":     ("powertrain", "L2", (0, 1, "bool")),
    "motor_efficiency":      ("powertrain", "L2", (0, 100, "%")),
    # ── 底盘 (10) ──
    "tire_pressure_fl":      ("chassis", "L3", (0, 5, "bar")),
    "tire_pressure_fr":      ("chassis", "L3", (0, 5, "bar")),
    "tire_pressure_rl":      ("chassis", "L3", (0, 5, "bar")),
    "tire_pressure_rr":      ("chassis", "L3", (0, 5, "bar")),
    "wheel_speed_fl":        ("chassis", "L1", (0, 300, "kmh")),
    "wheel_speed_fr":        ("chassis", "L1", (0, 300, "kmh")),
    "wheel_speed_rl":        ("chassis", "L1", (0, 300, "kmh")),
    "wheel_speed_rr":        ("chassis", "L1", (0, 300, "kmh")),
    "abs_active":            ("chassis", "L5", (0, 1, "bool")),
    "esp_active":            ("chassis", "L5", (0, 1, "bool")),
    # ── 车身 (10) ──
    "vehicle_speed":         ("body", "L1", (0, 200, "kmh")),
    "odometer":              ("body", "L3", (0, 500000, "km")),
    "door_status_fl":        ("body", "L3", (0, 1, "bool")),
    "door_status_fr":        ("body", "L3", (0, 1, "bool")),
    "door_status_rl":        ("body", "L3", (0, 1, "bool")),
    "door_status_rr":        ("body", "L3", (0, 1, "bool")),
    "window_status_fl":      ("body", "L3", (0, 100, "%")),
    "window_status_fr":      ("body", "L3", (0, 100, "%")),
    "cabin_temp":            ("body", "L3", (-20, 60, "degC")),
    "ac_target_temp":        ("body", "L3", (16, 32, "degC")),
    # ── 环境 (7) ──
    "gps_lat":               ("environment", "L3", (-90, 90, "deg")),
    "gps_lng":               ("environment", "L3", (-180, 180, "deg")),
    "altitude":              ("environment", "L3", (-500, 8000, "m")),
    "heading":               ("environment", "L3", (0, 360, "deg")),
    "ambient_temp":          ("environment", "L3", (-40, 60, "degC")),
    "ambient_humidity":      ("environment", "L4", (0, 100, "%")),
    "ambient_light":         ("environment", "L4", (0, 100000, "lux")),
}  # 合计：20 + 15 + 10 + 10 + 7 = 62 信号

# code: (system, severity, description)
DTC_REGISTRY: dict[str, tuple[str, str, str]] = {
    "P0562": ("powertrain", "warning", "System Voltage Low"),
    "P0AA6": ("powertrain", "critical", "Hybrid Battery Isolation Fault"),
    "P0AFA": ("powertrain", "warning", "Hybrid Battery System Voltage Low"),
    "B1234": ("body", "info", "Climate Control Communication Lost"),
    "C0040": ("chassis", "warning", "Tire Pressure Sensor Fault"),
    "C0110": ("chassis", "critical", "Brake Pump Motor Fault"),
    "U0100": ("network", "critical", "ECU Communication Lost"),
    "U0140": ("network", "critical", "Gateway Communication Lost"),
}  # 合计：8 DTC


class TBoxAdapter:
    """T-BOX 适配层。自动降级：live → cached → mock → unavailable。

    MVP 阶段 _live_available=False（WARN-01），全部走 mock。
    进程级共享缓存使 cached 层在无状态 API 调用间可命中。
    """

    CACHE_TTL = {"L1": 1, "L2": 5, "L3": 30, "L4": 300, "L5": float("inf")}
    _SHARED_CACHE: dict[tuple[str, str], TelemetryReading] = {}

    def __init__(self, vehicle_id: str = "CS001", conn: Any = None) -> None:
        self.vehicle_id = vehicle_id
        self._conn = conn  # reserved for Phase 2 DB-backed cache (tbox_signal_cache)
        self._live_available = False  # WARN-01: no real T-BOX in MVP

    def read(self, signal_id: str) -> TelemetryReading:
        """读取单个信号，自动降级：live → cached → mock → unavailable。"""
        if signal_id not in SIGNAL_REGISTRY:
            return TelemetryReading(
                signal_id=signal_id, value=None, unit="",
                timestamp=time.time(), data_source=DataSource.UNAVAILABLE,
                confidence=0.0, quality_flags=["unknown_signal"],
            )
        live = self._read_live(signal_id)
        if live is not None:
            self._SHARED_CACHE[(self.vehicle_id, signal_id)] = live
            return live
        cached = self._read_cached(signal_id)
        if cached is not None:
            # 返回副本，避免污染共享缓存（修复架构伪码就地改写缺陷）
            flags = list(cached.quality_flags)
            if "stale" not in flags:
                flags.append("stale")
            return replace(
                cached, data_source=DataSource.CACHED,
                confidence=0.7, quality_flags=flags,
            )
        mock = self._generate_mock(signal_id)
        self._SHARED_CACHE[(self.vehicle_id, signal_id)] = mock
        return mock

    def read_batch(self, signal_ids: list[str]) -> list[TelemetryReading]:
        """批量读取。"""
        return [self.read(sid) for sid in signal_ids]

    def read_group(self, group: str) -> list[TelemetryReading]:
        """按信号组读取（battery/powertrain/chassis/body/environment）。"""
        ids = [sid for sid, (g, _, _) in SIGNAL_REGISTRY.items() if g == group]
        return self.read_batch(ids)

    def get_dtc(self) -> list[DTCReading]:
        """读取异常码（DTC）。5% 概率生成 0-2 个仿真 DTC。"""
        return self._generate_mock_dtc()

    # ── 内部方法 ──

    def _read_live(self, signal_id: str) -> Optional[TelemetryReading]:
        """尝试读取 T-BOX 真实数据。MVP 返回 None（WARN-01）。"""
        if not self._live_available:
            return None
        return None  # 阶段 2 实现：WebSocket 连接 T-BOX 网关

    def _read_cached(self, signal_id: str) -> Optional[TelemetryReading]:
        """尝试读取缓存数据，按频率层 TTL 判过期。"""
        key = (self.vehicle_id, signal_id)
        cached = self._SHARED_CACHE.get(key)
        if cached is None:
            return None
        tier = SIGNAL_REGISTRY.get(signal_id, ("", "L3", (0, 1, "")))[1]
        ttl = self.CACHE_TTL.get(tier, 30)
        if ttl != float("inf") and time.time() - cached.timestamp > ttl:
            return None  # 缓存过期
        return cached

    def _generate_mock(self, signal_id: str) -> TelemetryReading:
        """仿真数据生成器（C-20: data_source=mock, confidence=0.3）。"""
        _, _, (min_val, max_val, unit) = SIGNAL_REGISTRY[signal_id]
        value = self._simulate_trend(signal_id, min_val, max_val, unit)
        return TelemetryReading(
            signal_id=signal_id, value=value, unit=unit,
            timestamp=time.time(), data_source=DataSource.MOCK,
            confidence=0.3, quality_flags=["simulated"],
        )

    def _generate_mock_dtc(self) -> list[DTCReading]:
        """仿真 DTC 生成器。5% 概率生成 0-2 个 DTC。"""
        if random.random() > 0.05:
            return []
        count = random.randint(1, 2)
        codes = random.sample(list(DTC_REGISTRY.keys()), count)
        now = time.time()
        return [
            DTCReading(
                code=c, system=DTC_REGISTRY[c][0], severity=DTC_REGISTRY[c][1],
                description=DTC_REGISTRY[c][2], timestamp=now,
                data_source=DataSource.MOCK, confidence=0.3,
            )
            for c in codes
        ]

    @staticmethod
    def _simulate_trend(
        signal_id: str, min_val: float, max_val: float, unit: str
    ) -> float:
        """趋势模拟：SOH 月衰减 / SOC 日周期 / 温度季节性 / 其余范围分布。"""
        now = time.time()
        if unit == "bool":
            return float(random.randint(0, 1))
        if unit == "enum":
            return float(random.randint(int(min_val), int(max_val)))
        if signal_id == "battery_soh":
            months = (now - 1700000000) / (30 * 86400)  # 从 2023-11 起算
            return round(max(70.0, 100 - months * 0.15), 2)
        if signal_id == "battery_soc":
            frac = (now % 86400) / 86400
            return round(60 + 30 * math.sin(2 * math.pi * frac), 2)
        if "temp" in signal_id:
            day = (now % 31536000) / 86400  # 年内天数 0..365
            seasonal = 15 * math.sin(2 * math.pi * day / 365)
            mid = (min_val + max_val) / 2
            return round(
                max(min_val, min(max_val, mid + seasonal + random.gauss(0, 2))), 2
            )
        if "pressure" in signal_id:
            return round(max(min_val, min(max_val, 2.4 + random.gauss(0, 0.05))), 3)
        if "voltage" in signal_id:
            mid = (min_val + max_val) / 2
            return round(mid + random.gauss(0, (max_val - min_val) / 20), 4)
        return round(random.uniform(min_val, max_val), 4)
