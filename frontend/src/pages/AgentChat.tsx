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

  const statusTag = () => {
    switch (status) {
      case "thinking":
        return <Tag color="processing">思考中…</Tag>;
      case "active":
        return <Tag color="success">守护在线</Tag>;
      case "error":
        return <Tag color="error">连接异常</Tag>;
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
            messages.map((m) => (
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
                  <div
                    className="cs-bubble"
                    style={{
                      background: m.role === "user" ? "#eef2ff" : "#fff",
                      border: "1px solid #eef0f4",
                      borderRadius: 14,
                      padding: "12px 16px",
                      fontSize: 16,
                      whiteSpace: "pre-wrap",
                      lineHeight: 1.6,
                    }}
                  >
                    {m.content}
                  </div>
                  {m.role === "assistant" && m.closed_loop && (
                    <ClosedLoopTrace loop={m.closed_loop} compact />
                  )}
                  {m.role === "assistant" && m.closed_loop?.trip_report && (
                    <TripReportCard report={m.closed_loop.trip_report} />
                  )}
                </div>
              </div>
            ))
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
