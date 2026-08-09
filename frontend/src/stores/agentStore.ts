import { create } from "zustand";
import type { AgentCitation, AgentDegraded, ClosedLoop } from "@/services/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  closed_loop?: ClosedLoop | null;
  /**
   * 链路降级详情。**非空只代表链路不可用，不代表这条回答降级了。**
   * 判断这条回答是否真降级只能用 `degraded?.affects_this_turn === true`。
   */
  degraded?: AgentDegraded | null;
  citations?: AgentCitation[];
  llm_used?: boolean;
  compliance_refused?: boolean;
  /** 非空即代表合规闸门介入过（含不拒答的 safety_critical） */
  compliance_category?: string | null;
  /** refuse / safety_disclaim / null */
  compliance_action?: string | null;
  safety_scrubbed?: boolean;
  safety_scrub_hits?: unknown[];
  engine?: string;
}

/** 最近一轮观测到的链路事实。三个字段互相正交，任何一个都不许推断另一个。 */
export interface LinkFacts {
  llmAvailable: boolean;
  llmUsed: boolean;
  /** 本轮回答是否**真的**因链路不可用而受损。
   *  - false = 确证未受损（确定性路径：合规闸门 / 反问 / 超纲声明）
   *  - true  = 确证受损（真降级）
   *  - null  = 未证明（上游违约：llm_available=false 却没给 degraded）。
   *    此时不许当作 false——没证明没受损就不许当没受损，必须按受损处理。 */
  affectsThisTurn: boolean | null;
  reason?: string | null;
  detail?: string | null;
}

interface AgentState {
  messages: ChatMessage[];
  sessionId: string | null;
  /**
   * "degraded" = 未证明"链路可用且本轮真的调了大模型"。
   * 注意它是**链路层**判定（llm_available && llm_used），不等于"这轮回答变差了"——
   * 呈现文案必须结合 linkFacts.affectsThisTurn 才不会把合规拒答说成质量下降。
   */
  status: "idle" | "thinking" | "active" | "degraded" | "error";
  /** null = 本会话还没有过任何一轮真实观测 */
  linkFacts: LinkFacts | null;
  pushMessage: (msg: Omit<ChatMessage, "id" | "createdAt">) => void;
  setStatus: (s: AgentState["status"]) => void;
  setLinkFacts: (f: LinkFacts | null) => void;
  setSessionId: (id: string | null) => void;
  reset: () => void;
}

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export const useAgentStore = create<AgentState>((set) => ({
  messages: [],
  sessionId: null,
  status: "idle",
  linkFacts: null,
  pushMessage: (msg) =>
    set((s) => ({
      messages: [...s.messages, { ...msg, id: uid(), createdAt: Date.now() }],
    })),
  setStatus: (status) => set({ status }),
  setLinkFacts: (linkFacts) => set({ linkFacts }),
  setSessionId: (sessionId) => set({ sessionId }),
  reset: () => set({ messages: [], sessionId: null, status: "idle", linkFacts: null }),
}));
