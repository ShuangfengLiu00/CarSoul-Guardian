import { create } from "zustand";
import type { AgentCitation, AgentDegraded, ClosedLoop } from "@/services/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  closed_loop?: ClosedLoop | null;
  /** 降级详情；非空即表示该条回答未经大模型转述 */
  degraded?: AgentDegraded | null;
  citations?: AgentCitation[];
  llm_used?: boolean;
  compliance_refused?: boolean;
  engine?: string;
}

interface AgentState {
  messages: ChatMessage[];
  sessionId: string | null;
  /** "degraded" = 有应答但未经大模型转述，必须与 active 区分呈现 */
  status: "idle" | "thinking" | "active" | "degraded" | "error";
  pushMessage: (msg: Omit<ChatMessage, "id" | "createdAt">) => void;
  setStatus: (s: AgentState["status"]) => void;
  setSessionId: (id: string | null) => void;
  reset: () => void;
}

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export const useAgentStore = create<AgentState>((set) => ({
  messages: [],
  sessionId: null,
  status: "idle",
  pushMessage: (msg) =>
    set((s) => ({
      messages: [...s.messages, { ...msg, id: uid(), createdAt: Date.now() }],
    })),
  setStatus: (status) => set({ status }),
  setSessionId: (sessionId) => set({ sessionId }),
  reset: () => set({ messages: [], sessionId: null, status: "idle" }),
}));
