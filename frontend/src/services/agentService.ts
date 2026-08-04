import { post } from "@/utils/request";
import type { AgentChatRequest, AgentChatResponse } from "./types";

export const agentService = {
  chat: (body: AgentChatRequest) => post<AgentChatResponse>("/api/agent/chat", body),
};
