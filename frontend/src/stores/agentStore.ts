import { create } from "zustand";
import type { ClosedLoop } from "@/services/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  closed_loop?: ClosedLoop | null;
}

interface AgentState {
  messages: ChatMessage[];
  sessionId: string | null;
  status: "idle" | "thinking" | "active" | "error";
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
