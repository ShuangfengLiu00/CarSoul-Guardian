import { Routes, Route, Navigate } from "react-router-dom";
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
  MemoryOcean,
} from "@/pages/index";

export default function App() {
  return (
    <Routes>
      {/* ===== Main routes (Ant Design layout) ===== */}
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
        {/* Unique "holographic" concept pages kept (not 3D / chat / health duplicates) */}
        <Route path="/memory" element={<MemoryOcean />} />
        <Route path="/evolution" element={<EvolutionEngine />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
