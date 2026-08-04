/**
 * Holographic AI Chat Page — 全息风格 AI 对话
 *
 * Replaces the Ant Design white-style AgentChat with a holographic
 * cockpit version that matches the deep-space aesthetic.
 */
import { useRef, useState, useEffect } from "react";
import { useAgent, useSpeech } from "@/hooks";
import { useAgentStore } from "@/stores";
import { ClosedLoopTrace, TripReportCard } from "@/components";
import { GlassPanel, HologramCore } from "@/components/hologram";

export default function AgentChatHolo() {
  const { messages, status, send, reset } = useAgent();
  const sessionId = useAgentStore((s) => s.sessionId);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const fromVoiceRef = useRef(false);

  const {
    recognitionSupported,
    listening,
    transcript,
    interim,
    startListening,
    stopListening,
    resetTranscript,
    ttsSupported,
    speaking,
    ttsEnabled,
    setTtsEnabled,
    speak,
    cancelSpeak,
  } = useSpeech();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (listening) setInput((transcript + (interim ?? "")).trimStart());
  }, [listening, transcript, interim]);

  useEffect(() => {
    if (!listening && fromVoiceRef.current) {
      fromVoiceRef.current = false;
      const text = transcript.trim();
      if (text) {
        setInput(text);
        doSend(text);
      }
      resetTranscript();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listening]);

  const doSend = (text: string) => {
    const t = text.trim();
    if (!t || status === "thinking") return;
    send(t, (answer) => speak(answer));
    setInput("");
  };

  const handleSend = () => doSend(input);

  const toggleMic = () => {
    if (!recognitionSupported) return;
    if (listening) {
      fromVoiceRef.current = true;
      stopListening();
    } else {
      setInput("");
      resetTranscript();
      startListening();
    }
  };

  const toggleTts = (v: boolean) => {
    setTtsEnabled(v);
    if (!v) cancelSpeak();
  };

  const statusText = () => {
    switch (status) {
      case "thinking": return { text: "思考中", color: "var(--holo-amber)" };
      case "active": return { text: "守护在线", color: "var(--holo-green)" };
      case "error": return { text: "连接异常", color: "var(--holo-red)" };
      default: return { text: "待命", color: "var(--holo-text-dim)" };
    }
  };

  const st = statusText();

  const quickActions = [
    { icon: "🛣️", label: "长途出行检查（800km）", primary: true, text: "我要下周自驾800公里，帮我检查一下车辆状态" },
    { icon: "💚", label: "车辆健康检查", primary: false, text: "我的车健康怎么样？" },
    { icon: "⚡", label: "电池状态查询", primary: false, text: "电池温度正常吗？" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)", gap: 8 }}>
      {/* Header bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <HologramCore size={44} active={status === "thinking"} />
          <div>
            <div className="holo-text-bright" style={{ fontSize: 20, fontWeight: 700 }}>
              AI 守护引擎
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: st.color,
                  boxShadow: `0 0 8px ${st.color}`,
                  animation: status === "thinking" ? "holoPulse 1s ease-in-out infinite" : "none",
                }}
              />
              <span className="holo-text-dim" style={{ fontSize: 13 }}>{st.text}</span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {ttsSupported && (
            <button
              onClick={() => toggleTts(!ttsEnabled)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 14px",
                borderRadius: 10,
                border: "1px solid rgba(255,255,255,0.12)",
                background: ttsEnabled ? "rgba(0,240,255,0.1)" : "rgba(255,255,255,0.04)",
                color: ttsEnabled ? "var(--holo-cyan)" : "var(--holo-text-dim)",
                fontSize: 13,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {ttsEnabled ? "🔊" : "🔇"} {ttsEnabled ? "语音播报" : "静音"}
            </button>
          )}
          <button
            onClick={reset}
            className="holo-btn-ghost holo-btn"
            style={{ padding: "8px 16px", fontSize: 13 }}
          >
            ↻ 新对话
          </button>
        </div>
      </div>

      {/* Chat area */}
      <GlassPanel className="holo-anim-fade-in" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: "auto",
            padding: 20,
            minHeight: 0,
          }}
        >
          {messages.length === 0 ? (
            /* Empty state */
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 20, textAlign: "center" }}>
              <div className="holo-anim-float">
                <HologramCore size={80} active />
              </div>
              <div>
                <div className="holo-text-bright" style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
                  我是 CarSoul Guardian 守护引擎
                </div>
                <div className="holo-text-dim" style={{ fontSize: 14 }}>
                  点麦克风说话，或选择下方场景快速体验
                </div>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center", maxWidth: 600 }}>
                {quickActions.map((qa) => (
                  <button
                    key={qa.label}
                    onClick={() => doSend(qa.text)}
                    className={qa.primary ? "holo-btn" : "holo-btn holo-btn-ghost"}
                    style={{ padding: "10px 18px", fontSize: 13 }}
                  >
                    {qa.icon} {qa.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message list */
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {messages.map((m) => (
                <div
                  key={m.id}
                  className="holo-anim-fade-in"
                  style={{
                    display: "flex",
                    gap: 12,
                    flexDirection: m.role === "user" ? "row-reverse" : "row",
                  }}
                >
                  {/* Avatar */}
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                      background: m.role === "user"
                        ? "rgba(99,102,241,0.15)"
                        : "linear-gradient(135deg, rgba(0,240,255,0.15), rgba(168,85,247,0.15))",
                      border: m.role === "user"
                        ? "1px solid rgba(99,102,241,0.3)"
                        : "1px solid rgba(0,240,255,0.3)",
                      boxShadow: m.role === "user"
                        ? "0 0 12px rgba(99,102,241,0.2)"
                        : "0 0 12px rgba(0,240,255,0.2)",
                    }}
                  >
                    {m.role === "user" ? "🧑" : "🤖"}
                  </div>

                  {/* Message body */}
                  <div style={{ maxWidth: "75%" }}>
                    <div
                      style={{
                        background: m.role === "user"
                          ? "rgba(99,102,241,0.08)"
                          : "rgba(0,240,255,0.06)",
                        border: m.role === "user"
                          ? "1px solid rgba(99,102,241,0.2)"
                          : "1px solid rgba(0,240,255,0.15)",
                        borderRadius: m.role === "user" ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                        padding: "12px 18px",
                        fontSize: 15,
                        lineHeight: 1.7,
                        color: "var(--holo-text)",
                        whiteSpace: "pre-wrap",
                        backdropFilter: "blur(10px)",
                      }}
                    >
                      {m.content}
                    </div>

                    {/* Closed loop trace */}
                    {m.role === "assistant" && m.closed_loop && (
                      <ClosedLoopTrace loop={m.closed_loop} compact />
                    )}
                    {m.role === "assistant" && m.closed_loop?.trip_report && (
                      <TripReportCard report={m.closed_loop.trip_report} />
                    )}
                  </div>
                </div>
              ))}

              {/* Thinking indicator */}
              {status === "thinking" && (
                <div style={{ display: "flex", gap: 12 }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                      background: "linear-gradient(135deg, rgba(0,240,255,0.15), rgba(168,85,247,0.15))",
                      border: "1px solid rgba(0,240,255,0.3)",
                    }}
                  >
                    🤖
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      padding: "12px 20px",
                      background: "rgba(0,240,255,0.06)",
                      border: "1px solid rgba(0,240,255,0.15)",
                      borderRadius: "4px 16px 16px 16px",
                    }}
                  >
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: "var(--holo-cyan)",
                          animation: `holoBreathe 1s ease-in-out infinite`,
                          animationDelay: `${i * 0.2}s`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input area — integrated into the same panel for visual continuity */}
        <div
          style={{
            borderTop: "1px solid rgba(255,255,255,0.08)",
            padding: 12,
            background: "rgba(0,0,0,0.2)",
          }}
        >
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          {/* Mic button */}
          {recognitionSupported && (
            <button
              onClick={toggleMic}
              style={{
                width: 48,
                height: 48,
                borderRadius: 12,
                border: listening
                  ? "1px solid var(--holo-red)"
                  : "1px solid rgba(0,240,255,0.3)",
                background: listening
                  ? "rgba(255,56,96,0.1)"
                  : "rgba(0,240,255,0.08)",
                color: listening ? "var(--holo-red)" : "var(--holo-cyan)",
                fontSize: 20,
                cursor: "pointer",
                flexShrink: 0,
                transition: "all 0.2s",
                animation: listening ? "holoPulseRed 1s ease-in-out infinite" : "none",
              }}
              title={listening ? "停止说话" : "点击语音输入"}
            >
              {listening ? "⏹" : "🎤"}
            </button>
          )}

          {/* Text input */}
          <div style={{ flex: 1, position: "relative" }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={listening ? "正在聆听… 请说出你的问题" : "向守护引擎提问…（Enter 发送 / 点麦克风语音输入）"}
              rows={1}
              style={{
                width: "100%",
                minHeight: 48,
                maxHeight: 120,
                padding: "12px 16px",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(255,255,255,0.04)",
                color: "var(--holo-text-bright)",
                fontSize: 15,
                lineHeight: 1.5,
                resize: "none",
                outline: "none",
                fontFamily: "inherit",
                transition: "border-color 0.2s",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "rgba(0,240,255,0.4)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "rgba(255,255,255,0.12)";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
          </div>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={status === "thinking" || !input.trim()}
            style={{
              height: 48,
              padding: "0 28px",
              fontSize: 15,
              fontWeight: 700,
              color: "#ffffff",
              borderRadius: 12,
              border: "1px solid rgba(0,240,255,0.5)",
              background: status === "thinking" || !input.trim()
                ? "rgba(0,240,255,0.08)"
                : "linear-gradient(135deg, rgba(0,240,255,0.25), rgba(0,200,255,0.15))",
              boxShadow: status === "thinking" || !input.trim()
                ? "none"
                : "0 0 16px rgba(0,240,255,0.2), inset 0 1px 0 rgba(255,255,255,0.1)",
              textShadow: "0 1px 4px rgba(0,0,0,0.3)",
              cursor: status === "thinking" || !input.trim() ? "not-allowed" : "pointer",
              flexShrink: 0,
              transition: "all 0.2s",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {status === "thinking" ? "⏳" : "➤"} 发送
          </button>
        </div>

        {/* Status bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
          {listening && (
            <span className="holo-chip holo-chip-red">● 正在聆听</span>
          )}
          {speaking && (
            <span className="holo-chip holo-chip-purple">🔊 播报中</span>
          )}
          <span className="holo-text-dim" style={{ fontSize: 12 }}>
            会话 ID: {sessionId || "（新建中）"}
            {recognitionSupported ? " · 支持语音输入" : " · 当前浏览器不支持语音识别"}
          </span>
        </div>
      </div>
      </GlassPanel>
    </div>
  );
}
