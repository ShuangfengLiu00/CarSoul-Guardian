/**
 * Page 03 - Digital Twin View (数字孪生)
 *
 * 3D vehicle with clickable component selector buttons (电池/电机/制动/轮胎/底盘).
 * Detail panel shows the selected component data from vehicleTwin. Battery shows
 * 12 cells; tire shows 4 tires with prediction. EnergyRing per component health.
 */
import { useState } from "react";
import { HoloCanvas, SpaceBackground, Vehicle3D } from "@/components/three";
import { GlassPanel, EnergyRing } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { vehicleTwin, getHealthColor, getHealthLabel } from "@/services/holoData";

type ComponentKey = "battery" | "motor" | "brake" | "tire" | "chassis";

const COMPONENTS: { key: ComponentKey; label: string; icon: string }[] = [
  { key: "battery", label: "电池", icon: "🔋" },
  { key: "motor", label: "电机", icon: "⚡" },
  { key: "brake", label: "制动", icon: "🛑" },
  { key: "tire", label: "轮胎", icon: "🛞" },
  { key: "chassis", label: "底盘", icon: "🔩" },
];

export default function DigitalTwinView() {
  const [selected, setSelected] = useState<ComponentKey>("battery");

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        数字孪生 · {vehicleTwin.name}
      </h2>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "1fr 420px",
          gap: 16,
          minHeight: "calc(100vh - 110px)",
        }}
      >
        {/* Left: 3D + selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <GlassPanel className="holo-anim-fade-scale holo-corners" style={{ padding: 0, overflow: "hidden", flex: 1, minHeight: 420, position: "relative" }}>
            <HoloCanvas cameraPosition={[0, 1.5, 6]}>
              <SpaceBackground />
              <Vehicle3D autoRotate rotationSpeed={0.5} scale={1} highlightPart={selected} onPartClick={(p) => setSelected(p as ComponentKey)} />
            </HoloCanvas>
            <div className="holo-text-dim" style={{ position: "absolute", bottom: 12, left: 16, fontSize: 12, zIndex: 2 }}>
              点击下方部件或直接交互 3D 模型查看详情
            </div>
          </GlassPanel>

          {/* Component selector */}
          <div className="holo-anim-fade-in" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {COMPONENTS.map((c, i) => {
              const isActive = selected === c.key;
              const health = getHealth(c.key);
              return (
                <button
                  key={c.key}
                  className={`holo-anim-fade-in ${isActive ? "holo-btn" : "holo-btn holo-btn-ghost"}`}
                  style={{ animationDelay: `${i * 0.08}s`, flex: 1, minWidth: 110 }}
                  onClick={() => setSelected(c.key)}
                >
                  <span style={{ fontSize: 18 }}>{c.icon}</span>
                  <span>{c.label}</span>
                  <span className="holo-text-dim" style={{ fontSize: 11, opacity: 0.8 }}>
                    {health}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Detail panel */}
        <GlassPanel className="holo-anim-slide-right holo-corners" style={{ overflowY: "auto" }}>
          <ComponentDetail component={selected} />
        </GlassPanel>
      </div>
    </div>
  );
}

function getHealth(key: ComponentKey): number {
  switch (key) {
    case "battery": return vehicleTwin.battery.health;
    case "motor": return vehicleTwin.motor.health;
    case "brake": return vehicleTwin.brake.health;
    case "tire": return vehicleTwin.tire.health;
    case "chassis": return vehicleTwin.chassis.health;
  }
}

function ComponentDetail({ component }: { component: ComponentKey }) {
  const health = getHealth(component);
  const color = getHealthColor(health);
  const meta = COMPONENTS.find((c) => c.key === component)!;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <EnergyRing value={health} size={100} color={color} label={getHealthLabel(health)} />
        <div>
          <div style={{ fontSize: 22, fontWeight: 800 }} className="holo-text-bright">
            {meta.icon} {meta.label}
          </div>
          <div className="holo-text-dim" style={{ fontSize: 13, marginTop: 4 }}>
            健康度 <span style={{ color }}>{health}%</span> · {getHealthLabel(health)}
          </div>
        </div>
      </div>

      <div className="holo-divider" />

      {component === "battery" && <BatteryDetail />}
      {component === "motor" && <MotorDetail />}
      {component === "brake" && <BrakeDetail />}
      {component === "tire" && <TireDetail />}
      {component === "chassis" && <ChassisDetail />}
    </div>
  );
}

function MetricRow({ label, value, unit, accent }: { label: string; value: string | number; unit?: string; accent?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0" }}>
      <span className="holo-text-dim" style={{ fontSize: 13 }}>{label}</span>
      <span className="holo-text-bright" style={{ fontSize: 15, fontWeight: 600, color: accent }}>
        {value}
        {unit && <span className="holo-text-dim" style={{ fontSize: 12, marginLeft: 3, fontWeight: 400 }}>{unit}</span>}
      </span>
    </div>
  );
}

function SubTitle({ children }: { children: React.ReactNode }) {
  return <div className="holo-section-title" style={{ fontSize: 15, marginTop: 8 }}>{children}</div>;
}

function BatteryDetail() {
  const b = vehicleTwin.battery;
  return (
    <div className="holo-anim-fade-in">
      <MetricRow label="健康度" value={b.health} unit="%" accent={getHealthColor(b.health)} />
      <MetricRow label="温度" value={b.temperature} unit="°C" />
      <MetricRow label="容量保持" value={b.capacity} unit="%" />
      <MetricRow label="循环次数" value={`${b.cycle} / ${b.maxCycles}`} />
      <MetricRow label="电压" value={b.voltage} unit="V" />
      <MetricRow label="电流" value={b.current} unit="A" />
      <MetricRow label="剩余寿命" value={b.remainingLife} unit="年" accent="#00ff9d" />

      <SubTitle>12 电芯状态</SubTitle>
      <div className="holo-grid holo-grid-3" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        {b.cells.map((cell, i) => (
          <div
            key={cell.id}
            className="holo-glass holo-glass-hover holo-anim-fade-in"
            style={{ animationDelay: `${i * 0.05}s`, padding: "8px 6px", borderRadius: 8, textAlign: "center" }}
          >
            <div className="holo-text-dim" style={{ fontSize: 10 }}>#{cell.id}</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: getHealthColor(cell.health) }}>{cell.voltage.toFixed(2)}V</div>
            <div className="holo-text-dim" style={{ fontSize: 10 }}>{cell.temp.toFixed(1)}°C</div>
          </div>
        ))}
      </div>

      <div className="holo-chip holo-chip-green" style={{ marginTop: 14 }}>
        AI 预测：状态健康 · 剩余 {b.remainingLife} 年
      </div>
    </div>
  );
}

function MotorDetail() {
  const m = vehicleTwin.motor;
  return (
    <div className="holo-anim-fade-in">
      <MetricRow label="健康度" value={m.health} unit="%" accent={getHealthColor(m.health)} />
      <MetricRow label="温度" value={m.temperature} unit="°C" />
      <MetricRow label="功率" value={m.power} unit="kW" />
      <MetricRow label="效率" value={m.efficiency} unit="%" accent="#00f0ff" />
      <MetricRow label="扭矩" value={m.torque} unit="N·m" />
      <MetricRow label="转速" value={m.rpm} unit="RPM" />
      <div className="holo-chip holo-chip-green" style={{ marginTop: 14 }}>电机效率稳定，状态优异</div>
    </div>
  );
}

function BrakeDetail() {
  const br = vehicleTwin.brake;
  return (
    <div className="holo-anim-fade-in">
      <MetricRow label="健康度" value={br.health} unit="%" accent={getHealthColor(br.health)} />
      <MetricRow label="前刹车片" value={br.frontPad} unit="%" accent="#ffb800" />
      <MetricRow label="后刹车片" value={br.rearPad} unit="%" />
      <MetricRow label="制动液位" value={br.fluidLevel} unit="%" />
      <MetricRow label="前片预测更换" value={br.frontPadPrediction} unit="天" accent="#ff3860" />
      <div className="holo-chip holo-chip-amber" style={{ marginTop: 14 }}>
        前刹车片磨损达 55%，建议 45 天内更换
      </div>
    </div>
  );
}

function TireDetail() {
  const t = vehicleTwin.tire;
  return (
    <div className="holo-anim-fade-in">
      <MetricRow label="整体健康" value={t.health} unit="%" accent={getHealthColor(t.health)} />
      <MetricRow label="平均胎压" value={t.pressure} unit="bar" />
      <MetricRow label="平均胎纹" value={t.treadDepth} unit="mm" />

      <SubTitle>四轮状态</SubTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {t.tires.map((tire, i) => (
          <div
            key={tire.position}
            className="holo-glass holo-glass-hover holo-anim-fade-in"
            style={{ animationDelay: `${i * 0.08}s`, padding: 12, borderRadius: 10 }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="holo-text-bright" style={{ fontSize: 14, fontWeight: 700 }}>{tire.position}</span>
              <span style={{ fontSize: 16, fontWeight: 800, color: getHealthColor(tire.health) }}>{tire.health}%</span>
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 6 }} className="holo-text-dim">
              <span style={{ fontSize: 12 }}>胎压 {tire.pressure}bar</span>
              <span style={{ fontSize: 12 }}>温度 {tire.temp}°C</span>
              <span style={{ fontSize: 12 }}>胎纹 {tire.tread}mm</span>
            </div>
            <div className="holo-energy-bar" style={{ marginTop: 8 }}>
              <div className="holo-energy-bar__fill" style={{ width: `${tire.health}%`, background: getHealthColor(tire.health) }} />
            </div>
            <div className="holo-text-dim" style={{ fontSize: 11, marginTop: 6 }}>{tire.prediction}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChassisDetail() {
  const c = vehicleTwin.chassis;
  return (
    <div className="holo-anim-fade-in">
      <MetricRow label="健康度" value={c.health} unit="%" accent={getHealthColor(c.health)} />
      <MetricRow label="悬挂系统" value={c.suspension} unit="%" />
      <MetricRow label="转向系统" value={c.steering} unit="%" />
      <MetricRow label="四轮定位" value={c.alignment} unit="%" />
      <div className="holo-chip holo-chip-green" style={{ marginTop: 14 }}>底盘状态稳定，各项指标正常</div>
    </div>
  );
}
