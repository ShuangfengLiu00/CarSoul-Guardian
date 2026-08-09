import { useCallback } from "react";
import { agentService } from "@/services";
import { useAgentStore } from "@/stores";
import { useUserStore } from "@/stores";

/** Hook to drive the Agent chat. */
export function useAgent() {
  const { messages, status, pushMessage, setStatus, setSessionId, sessionId, reset } =
    useAgentStore();
  const username = useUserStore((s) => s.username) || "guest";

  const send = useCallback(
    async (text: string, onReply?: (answer: string) => void) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      pushMessage({ role: "user", content: trimmed });
      setStatus("thinking");
      try {
        const resp = await agentService.chat({
          user: username,
          message: trimmed,
          session_id: sessionId || undefined,
        });
        if (resp.session_id) setSessionId(resp.session_id);
        // 诚实降级：未证明"链路可用且本轮真的调了大模型"即视为降级。
        // 这里刻意不信任 resp.agent_status 之外的任何默认值，也不再无条件 active。
        const trulyLive = Boolean(resp.llm_available) && Boolean(resp.llm_used);
        pushMessage({
          role: "assistant",
          content: resp.answer,
          closed_loop: resp.closed_loop ?? null,
          degraded: trulyLive ? null : (resp.degraded ?? { reason: "unknown" }),
          citations: resp.citations ?? [],
          llm_used: Boolean(resp.llm_used),
          compliance_refused: Boolean(resp.compliance_refused),
          engine: resp.engine ?? "unknown",
        });
        setStatus(trulyLive ? "active" : "degraded");
        onReply?.(resp.answer);
      } catch {
        pushMessage({
          role: "assistant",
          content: "守护引擎连接失败，请检查后端服务是否启动。",
        });
        setStatus("error");
      }
    },
    [messages, status, pushMessage, setStatus, setSessionId, sessionId, username],
  );

  return { messages, status, send, reset };
}
