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
        pushMessage({
          role: "assistant",
          content: resp.answer,
          closed_loop: resp.closed_loop ?? null,
        });
        setStatus("active");
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
