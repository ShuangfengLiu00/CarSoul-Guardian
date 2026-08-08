import { Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import { MainLayout } from "@/layouts/index";
import {
  Dashboard,
  AgentChat,
  VehicleArchive,
  VehicleLifeHome,
  StoryMode,
  KnowledgeBase,
  VehicleSimulator,
  MyCarSoul,
  RiskPrediction,
  SafetyCompliance,
  Governance,
  EvolutionEngine,
  TimelineDemo,
  Console,
} from "@/pages/index";
import {
  UniverseEntry,
  VehicleUniverse,
  DigitalTwinView,
  HealthDashboard,
  BatteryCenter,
  AgentGalaxyPage,
  MemoryOcean,
  PredictionCenter,
  SafetyGuardian,
  VehicleTimeline,
  AgentChatHolo,
} from "@/pages/hologram/index";
import { HoloLayout } from "@/components/hologram/index";

/** Wrapper that provides HoloLayout with automatic activePath detection */
function HoloLayoutWrapper() {
  const location = useLocation();
  return (
    <HoloLayout activePath={location.pathname}>
      <Outlet />
    </HoloLayout>
  );
}

export default function App() {
  return (
    <Routes>
      {/* ===== Legacy routes (Ant Design layout) ===== */}
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/agent" element={<AgentChat />} />
        <Route path="/vehicle" element={<VehicleArchive />} />
        <Route path="/life" element={<VehicleLifeHome />} />
        <Route path="/soul" element={<MyCarSoul />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/risk" element={<RiskPrediction />} />
        <Route path="/safety" element={<SafetyCompliance />} />
        <Route path="/story" element={<StoryMode />} />
        <Route path="/simulator" element={<VehicleSimulator />} />
        <Route path="/governance" element={<Governance />} />
        <Route path="/timeline" element={<TimelineDemo />} />
        <Route path="/portal" element={<Console />} />
      </Route>

      {/* ===== Holographic Cockpit routes ===== */}
      {/* Full-screen entry (no sidebar) */}
      <Route path="/holo" element={<UniverseEntry />} />

      {/* Holographic pages with sidebar layout */}
      <Route element={<HoloLayoutWrapper />}>
        <Route path="/holo/universe" element={<VehicleUniverse />} />
        <Route path="/holo/twin" element={<DigitalTwinView />} />
        <Route path="/holo/health" element={<HealthDashboard />} />
        <Route path="/holo/battery" element={<BatteryCenter />} />
        <Route path="/holo/agents" element={<AgentGalaxyPage />} />
        <Route path="/holo/memory" element={<MemoryOcean />} />
        <Route path="/holo/prediction" element={<PredictionCenter />} />
        <Route path="/holo/safety" element={<SafetyGuardian />} />
        <Route path="/holo/timeline" element={<VehicleTimeline />} />
        <Route path="/holo/evolution" element={<EvolutionEngine />} />
        <Route path="/holo/chat" element={<AgentChatHolo />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
