import { useCallback } from "react";
import { agentService } from "@/services";
import { useAgentStore } from "@/stores";
import { useUserStore } from "@/stores";

/** Hook to drive the Agent chat. */
export function useAgent() {
  const {
    messages,
    status,
    linkFacts,
    pushMessage,
    setStatus,
    setLinkFacts,
    setSessionId,
    sessionId,
    reset,
  } = useAgentStore();
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
        // 注意 trulyLive 判的是**链路**，不是"这轮回答质量"——后者只能看
        // degraded.affects_this_turn，两者不可互相推断。
        const trulyLive = Boolean(resp.llm_available) && Boolean(resp.llm_used);
        pushMessage({
          role: "assistant",
          content: resp.answer,
          closed_loop: resp.closed_loop ?? null,
          // 原样保留上游的 degraded：它非空 ⟺ 链路不可用。
          // 以前这里写 `trulyLive ? null : (resp.degraded ?? { reason: "unknown" })`，
          // 会在"链路正常但本轮走确定性路径"（llm_available=true / llm_used=false，
          // 例如合规拒答）时凭空造出一个 reason=unknown 的降级——那是假降级。
          degraded: resp.degraded ?? null,
          citations: resp.citations ?? [],
          llm_used: Boolean(resp.llm_used),
          compliance_refused: Boolean(resp.compliance_refused),
          compliance_category: resp.compliance_category ?? null,
          compliance_action: resp.compliance_action ?? null,
          safety_scrubbed: Boolean(resp.safety_scrubbed),
          safety_scrub_hits: resp.safety_scrub_hits ?? [],
          engine: resp.engine ?? "unknown",
        });
        setStatus(trulyLive ? "active" : "degraded");
        setLinkFacts({
          llmAvailable: Boolean(resp.llm_available),
          llmUsed: Boolean(resp.llm_used),
          affectsThisTurn: resp.degraded?.affects_this_turn === true,
          reason: resp.degraded?.reason ?? null,
          detail: resp.degraded?.detail ?? null,
        });
        onReply?.(resp.answer);
      } catch {
        pushMessage({
          role: "assistant",
          content: "守护引擎连接失败，请检查后端服务是否启动。",
        });
        setStatus("error");
        setLinkFacts(null);
      }
    },
    [messages, status, pushMessage, setStatus, setLinkFacts, setSessionId, sessionId, username],
  );

  return { messages, status, linkFacts, send, reset };
}
