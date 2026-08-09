import { useRef, useState, useEffect } from "react";
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  Avatar,
  Empty,
  Spin,
  Switch,
  Tooltip,
} from "antd";
import {
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  ReloadOutlined,
  AudioOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  MutedOutlined,
  EnvironmentOutlined,
  HeartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useAgent, useSpeech } from "@/hooks";
import { useAgentStore } from "@/stores";
import { ClosedLoopTrace, TripReportCard } from "@/components";

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function AgentChat() {
  const { messages, status, linkFacts, send, reset } = useAgent();
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

  // Live-echo the recognized speech into the input box while listening.
  useEffect(() => {
    if (listening) setInput((transcript + (interim ?? "")).trimStart());
  }, [listening, transcript, interim]);

  // When recognition stops and we have a final transcript, auto-send it.
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

  // status="degraded" 只说明"未证明链路可用且本轮真的调了大模型"，它**不等于**
  // "这轮回答变差了"。两个正交事实要分开说：
  //   · linkFacts.llmAvailable   —— 链路当前是否可用
  //   · linkFacts.affectsThisTurn —— 本轮回答是否真的因此受损
  // 合规拒答 / 信息不足反问 / 超纲声明是确定性路径，本就不经大模型，链路挂了
  // 它们的输出也一模一样。给这类回答挂「降级模式」是凭空制造一个不存在的缺陷 ——
  // 与历史上把失败硬编码成「守护在线」同属失真，只是方向相反。
  const statusTag = () => {
    switch (status) {
      case "thinking":
        return <Tag color="processing">思考中…</Tag>;
      case "active":
        return <Tag color="success">守护在线</Tag>;
      case "error":
        return <Tag color="error">连接异常</Tag>;
      case "degraded": {
        // 拿不到链路事实时取"受损"这一侧：没证明没受损，就不许当作没受损。
        if (!linkFacts || linkFacts.affectsThisTurn) {
          return (
            <Tooltip title={linkFacts?.detail || "本轮回答未经大模型转述，由确定性规则/模板生成"}>
              <Tag color="warning">降级模式</Tag>
            </Tooltip>
          );
        }
        if (!linkFacts.llmAvailable) {
          return (
            <Tooltip
              title={
                linkFacts.detail ||
                "大模型链路当前不可用；但本轮走的是确定性路径（合规闸门 / 信息不足反问 / 超纲声明），回答内容不受链路状态影响。"
              }
            >
              <Tag color="default">链路不可用 · 本轮未受影响</Tag>
            </Tooltip>
          );
        }
        return (
          <Tooltip title="大模型链路可用，但本轮按设计走确定性路径（合规闸门 / 信息不足反问 / 超纲声明），未调用大模型。">
            <Tag color="default">本轮未调用大模型</Tag>
          </Tooltip>
        );
      }
      default:
        return <Tag color="default">待命</Tag>;
    }
  };

  return (
    <div className="cs-agent-page">
      <Space className="cs-agent-head" style={{ justifyContent: "space-between", width: "100%" }}>
        <Title level={3} style={{ margin: 0 }}>
          AI 守护引擎
        </Title>
        <Space size={12}>
          {statusTag()}
          {ttsSupported && (
            <Space size={6} className="cs-tts-toggle">
              {ttsEnabled ? <SoundOutlined style={{ color: "#3b82f6" }} /> : <MutedOutlined />}
              <Switch
                checked={ttsEnabled}
                onChange={toggleTts}
                checkedChildren="语音播报"
                unCheckedChildren="静音"
              />
            </Space>
          )}
          <Button icon={<ReloadOutlined />} onClick={reset}>
            新对话
          </Button>
        </Space>
      </Space>

      <Card
        className="cs-card cs-chat-card"
        styles={{ body: { padding: 0, height: "calc(100dvh - 320px)", minHeight: 360 } }}
      >
        <div
          ref={scrollRef}
          className="cs-chat-scroll"
          style={{ height: "100%", overflowY: "auto", padding: 18, WebkitOverflowScrolling: "touch" }}
        >
          {messages.length === 0 ? (
            <div style={{ padding: "40px 0", textAlign: "center" }}>
              <Empty
                image={<RobotOutlined style={{ fontSize: 48, color: "#3b82f6" }} />}
                description={
                  <span>
                    我是 CarSoul Guardian 守护引擎。
                    <br />
                    点麦克风说话，或选择下方场景快速体验。
                  </span>
                }
              />
              <div
                style={{
                  display: "flex",
                  gap: 10,
                  justifyContent: "center",
                  flexWrap: "wrap",
                  marginTop: 20,
                }}
              >
                <Button
                  type="primary"
                  icon={<EnvironmentOutlined />}
                  onClick={() => doSend("我要下周自驾800公里，帮我检查一下车辆状态")}
                  style={{
                    borderRadius: 10,
                    height: 44,
                    paddingInline: 20,
                    background: "linear-gradient(135deg, #3b82f6, #6366f1)",
                    border: "none",
                  }}
                >
                  长途出行检查（800km）
                </Button>
                <Button
                  icon={<HeartOutlined />}
                  onClick={() => doSend("我的车健康怎么样？")}
                  style={{ borderRadius: 10, height: 44, paddingInline: 20 }}
                >
                  车辆健康检查
                </Button>
                <Button
                  icon={<ThunderboltOutlined />}
                  onClick={() => doSend("电池温度正常吗？")}
                  style={{ borderRadius: 10, height: 44, paddingInline: 20 }}
                >
                  电池状态查询
                </Button>
              </div>
            </div>
          ) : (
            messages.map((m) => {
              // 本轮回答是否**真的**降级：只认 affects_this_turn === true。
              // 绝不能写成 `Boolean(m.degraded)` —— degraded 非空只代表链路不可用，
              // 合规拒答那一轮同样带 degraded，但它的回答一点没受影响。
              const turnDegraded = m.degraded?.affects_this_turn === true;
              // 闸门是否介入过：看 compliance_category 非空。
              // safety_critical 类的处置是"免责 + 导向专业检修"，compliance_refused
              // 是 false，只看 refused 会把这一整类当成没发生过。
              const gateEngaged = Boolean(m.compliance_category);
              const refused = Boolean(m.compliance_refused);
              const disclaimed = gateEngaged && !refused;
              return (
              <div
                key={m.id}
                className="cs-msg-row"
                style={{
                  display: "flex",
                  gap: 12,
                  marginBottom: 18,
                  flexDirection: m.role === "user" ? "row-reverse" : "row",
                }}
              >
                <Avatar
                  size={44}
                  style={{
                    background:
                      m.role === "user" ? "#6366f1" : "linear-gradient(135deg,#3b82f6,#10b981)",
                    flexShrink: 0,
                  }}
                  icon={m.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                />
                <div className="cs-msg-body" style={{ maxWidth: "80%" }}>
                  {/* 降级 / 合规处置 / 安全清洗都必须在气泡上可见，且互不冒充 */}
                  {m.role === "assistant" && refused && (
                    <div style={{ marginBottom: 6 }}>
                      <Tooltip title={`合规闸门类别：${m.compliance_category}`}>
                        <Tag color="red">合规拒答</Tag>
                      </Tooltip>
                    </div>
                  )}
                  {m.role === "assistant" && disclaimed && (
                    <div style={{ marginBottom: 6 }}>
                      <Tooltip
                        title={
                          `合规闸门类别：${m.compliance_category}` +
                          "；处置为免责声明并导向专业检修 —— 这**不是**拒答，" +
                          "问题已回答，只是不替代专业检修下安全结论。"
                        }
                      >
                        <Tag color="orange">安全免责 · 建议专业检修</Tag>
                      </Tooltip>
                    </div>
                  )}
                  {m.role === "assistant" && m.safety_scrubbed && (
                    <div style={{ marginBottom: 6 }}>
                      <Tooltip
                        title={
                          "答案中出现了无工具证据支撑的安全结论（安全时限 / 磨损到极限 / 立即停驶），已就地移除。" +
                          (m.safety_scrub_hits?.length
                            ? `\n被移除片段：${m.safety_scrub_hits.map((h) => String(h)).join(" / ")}`
                            : "")
                        }
                      >
                        <Tag color="volcano">已移除无证据的安全结论</Tag>
                      </Tooltip>
                    </div>
                  )}
                  {m.role === "assistant" && turnDegraded && (
                    <div style={{ marginBottom: 6 }}>
                      <Tooltip
                        title={
                          m.degraded?.detail ||
                          `降级原因：${m.degraded?.reason ?? "未知"}`
                        }
                      >
                        <Tag color="warning">
                          降级模式 · 未经大模型转述
                          {m.engine ? ` · ${m.engine}` : ""}
                        </Tag>
                      </Tooltip>
                    </div>
                  )}
                  <div
                    className="cs-bubble"
                    style={{
                      // 底色同样只认 turnDegraded，不认 "degraded 非空"：
                      // 合规拒答/反问是正常回答，不该被涂成降级的黄底。
                      background:
                        m.role === "user"
                          ? "#eef2ff"
                          : refused
                            ? "#fff1f0"
                            : turnDegraded
                              ? "#fffbe6"
                              : "#fff",
                      border: refused
                        ? "1px solid #ffa39e"
                        : m.role === "assistant" && turnDegraded
                          ? "1px dashed #f0c36d"
                          : "1px solid #eef0f4",
                      borderRadius: 14,
                      padding: "12px 16px",
                      fontSize: 16,
                      whiteSpace: "pre-wrap",
                      lineHeight: 1.6,
                    }}
                  >
                    {m.content}
                  </div>
                  {m.role === "assistant" && !!m.citations?.length && (
                    <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {m.citations.map((c, i) => (
                        <Tooltip key={c.id ?? i} title={c.source ?? ""}>
                          <Tag color="blue" style={{ fontSize: 12 }}>
                            {c.id ? `[${c.id}] ` : ""}
                            {c.title ?? "引用"}
                          </Tag>
                        </Tooltip>
                      ))}
                    </div>
                  )}
                  {m.role === "assistant" && m.closed_loop && (
                    <ClosedLoopTrace loop={m.closed_loop} compact />
                  )}
                  {m.role === "assistant" && m.closed_loop?.trip_report && (
                    <TripReportCard report={m.closed_loop.trip_report} />
                  )}
                </div>
              </div>
              );
            })
          )}
          {status === "thinking" && (
            <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
              <Avatar
                size={44}
                style={{ background: "linear-gradient(135deg,#3b82f6,#10b981)" }}
                icon={<RobotOutlined />}
              />
              <Spin size="small" style={{ marginTop: 14 }} />
            </div>
          )}
        </div>
      </Card>

      <div className="cs-input-area">
        <Space.Compact style={{ width: "100%" }} size="large">
          {recognitionSupported && (
            <Tooltip title={listening ? "停止说话" : "点击语音输入"}>
              <Button
                className={`cs-mic-btn ${listening ? "cs-mic-pulse" : ""}`}
                danger={listening}
                icon={listening ? <PauseCircleOutlined /> : <AudioOutlined />}
                onClick={toggleMic}
                style={{ height: 56, width: 56, borderRadius: "12px 0 0 12px" }}
              />
            </Tooltip>
          )}
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              listening ? "正在聆听… 请说出你的问题" : "向守护引擎提问…（Enter 发送 / 点麦克风语音输入）"
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            style={
              recognitionSupported
                ? { borderRadius: 0 }
                : { borderRadius: "12px 0 0 12px" }
            }
          />
          <Button
            type="primary"
            size="large"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={status === "thinking"}
            style={{ height: 56, borderRadius: "0 12px 12px 0", paddingInline: 28 }}
          >
            发送
          </Button>
        </Space.Compact>
        <div className="cs-input-meta">
          {listening && <Tag color="red">● 正在聆听</Tag>}
          {speaking && <Tag color="blue">播报中…</Tag>}
          <Text type="secondary" style={{ fontSize: 12 }}>
            会话 ID: {sessionId || "（新建中）"}
            {recognitionSupported ? " · 支持语音输入" : " · 当前浏览器不支持语音识别"}
          </Text>
        </div>
      </div>
    </div>
  );
}
