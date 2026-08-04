/**
 * Page 01 - Universe Entry (宇宙入口)
 *
 * Full-screen deep space entry page. Features a Three.js canvas with
 * SpaceBackground + Vehicle3D (auto-rotating) + DataParticles, a breathing
 * AI core orb, gradient title and a large ENTER button that navigates to
 * /holo/universe.
 */
import { useNavigate } from "react-router-dom";
import { HoloCanvas, Vehicle3D, DataParticles } from "@/components/three";
import { HologramCore } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { vehicleTwin, getHealthColor } from "@/services/holoData";

export default function UniverseEntry() {
  const navigate = useNavigate();

  return (
    <div className="holo-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <DemoBadge />
      {/* Deep space 3D background — HoloCanvas includes SpaceBackground by default */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0 }}>
        <HoloCanvas cameraPosition={[0, 1.5, 6]} enableBackground>
          <DataParticles count={30} />
          <Vehicle3D autoRotate rotationSpeed={0.4} scale={1.1} />
        </HoloCanvas>
      </div>

      {/* Dark vignette overlay for text readability — strong center darkening */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 1,
          background:
            "radial-gradient(ellipse 70% 60% at center, rgba(3,0,10,0.7) 0%, rgba(3,0,10,0.45) 35%, transparent 65%), radial-gradient(ellipse at center, transparent 50%, rgba(5,8,22,0.75) 85%, rgba(5,8,22,0.95) 100%)",
          pointerEvents: "none",
        }}
      />

      {/* Foreground content */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
          textAlign: "center",
        }}
      >
        {/* Breathing AI core orb */}
        <div className="holo-anim-fade-in" style={{ animationDelay: "0.1s", marginBottom: 28 }}>
          <HologramCore size={96} />
        </div>

        {/* Brand badge */}
        <div
          className="holo-anim-fade-in holo-text-dim"
          style={{
            animationDelay: "0.3s",
            fontSize: 12,
            letterSpacing: "0.4em",
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          CarSoul Guardian System
        </div>

        {/* Title */}
        <h1
          className="holo-gradient-text holo-anim-glow-text holo-anim-fade-in"
          style={{
            animationDelay: "0.5s",
            fontSize: "clamp(40px, 8vw, 84px)",
            fontWeight: 900,
            letterSpacing: "0.06em",
            margin: "0 0 16px",
            lineHeight: 1.1,
            textShadow: "0 2px 20px rgba(0,0,0,0.6), 0 0 40px rgba(0,240,255,0.15)",
          }}
        >
          CARSOUL GUARDIAN
        </h1>

        {/* Subtitle */}
        <p
          className="holo-anim-fade-in"
          style={{
            animationDelay: "0.7s",
            fontSize: "clamp(15px, 2.5vw, 20px)",
            margin: "0 0 40px",
            letterSpacing: "0.08em",
            color: "rgba(230,238,255,0.95)",
            textShadow: "0 1px 8px rgba(0,0,0,0.8), 0 0 20px rgba(0,0,0,0.5)",
          }}
        >
          你的座驾已经觉醒
        </p>

        {/* Vehicle info card */}
        <div
          className="holo-corners holo-anim-fade-scale"
          style={{
            animationDelay: "0.9s",
            padding: "24px 40px",
            borderRadius: 16,
            display: "flex",
            alignItems: "center",
            gap: 40,
            flexWrap: "wrap",
            justifyContent: "center",
            marginBottom: 40,
            background: "linear-gradient(135deg, #080c1c, #050814)",
            border: "1px solid rgba(0,240,255,0.15)",
            boxShadow: "0 4px 30px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06)",
          }}
        >
          <InfoBlock label="车辆名称" value={vehicleTwin.name} />
          <Divider />
          <InfoBlock label="车型" value={vehicleTwin.model} />
          <Divider />
          <InfoBlock label="陪伴时长" value={`${vehicleTwin.age} 天`} />
          <Divider />
          <InfoBlock
            label="健康度"
            value={`${vehicleTwin.health}%`}
            color={getHealthColor(vehicleTwin.health)}
          />
        </div>

        {/* ENTER button */}
        <button
          className="holo-btn holo-anim-fade-in holo-anim-pulse"
          style={{
            animationDelay: "1.1s",
            padding: "16px 64px",
            fontSize: 18,
            letterSpacing: "0.3em",
          }}
          onClick={() => navigate("/holo/universe")}
        >
          ENTER&nbsp;&nbsp;进入
        </button>

        {/* Footer hint */}
        <div
          className="holo-text-dim holo-anim-fade-in"
          style={{
            animationDelay: "1.4s",
            marginTop: 60,
            fontSize: 12,
            letterSpacing: "0.2em",
            opacity: 0.6,
          }}
        >
          深空全息座舱 · 数字生命守护
        </div>
      </div>
    </div>
  );
}

function InfoBlock({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 11, letterSpacing: "0.15em", textTransform: "uppercase", color: "rgba(180,190,210,0.9)", textShadow: "0 1px 4px rgba(0,0,0,0.5)" }}>
        {label}
      </span>
      <span
        style={{ fontSize: 20, fontWeight: 700, color: color ?? "#ffffff", textShadow: color ? `0 0 12px ${color}` : "0 1px 6px rgba(0,0,0,0.5)" }}
      >
        {value}
      </span>
    </div>
  );
}

function Divider() {
  return <span style={{ width: 1, height: 36, background: "rgba(255,255,255,0.12)" }} />;
}
