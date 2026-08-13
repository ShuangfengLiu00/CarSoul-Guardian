import { useEffect, useState } from "react";
import {
  Card,
  List,
  Tag,
  Space,
  Select,
  InputNumber,
  Button,
  Typography,
  Alert as AntAlert,
  Form,
  Input,
  message,
  Row,
  Col,
} from "antd";
import {
  SoundOutlined,
  HeartOutlined,
  SafetyCertificateOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { cabinService } from "@/services/cabinService";
import type { CabinCard } from "@/services/cabinService";
import { useCurrentVehicle } from "@/hooks/useCurrentVehicle";

const { Title, Text } = Typography;

const LEVEL_COLOR: Record<string, string> = { info: "blue", warning: "orange", success: "green" };

export default function CabinCompanion() {
  const { vehicle } = useCurrentVehicle();
  const vehicleId = String(vehicle?.id ?? 1);

  const [cards, setCards] = useState<CabinCard[]>([]);
  const [redline, setRedline] = useState("");
  const [state, setState] = useState<Record<string, unknown>>({});
  const [timeOfDay, setTimeOfDay] = useState("evening");
  const [speed, setSpeed] = useState<number>(0);
  const [occupancy, setOccupancy] = useState(1);
  const [prefs, setPrefs] = useState<Record<string, unknown>>({});

  const loadSuggestions = () => {
    cabinService
      .suggestions(vehicleId, { time_of_day: timeOfDay, speed_kmh: speed, occupancy })
      .then((r) => {
        setCards(r.cards ?? []);
        setRedline(r.control_redline ?? "");
        setState((r.vehicle_state as Record<string, unknown>) ?? {});
      })
      .catch(() => setCards([]));
  };

  const loadPrefs = () => {
    cabinService.getPreferences(vehicleId).then((r) => setPrefs(r.preferences ?? {})).catch(() => setPrefs({}));
  };

  useEffect(() => {
    loadSuggestions();
    loadPrefs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleId]);

  const savePrefs = (v: { temperature?: number; music?: string; charging?: string }) => {
    const merged = { ...prefs, ...v };
    cabinService
      .setPreferences(vehicleId, merged)
      .then(() => {
        setPrefs(merged);
        message.success("偏好已保存");
      })
      .catch(() => message.error("保存失败"));
  };

  const soc = state.soc != null ? `${(Number(state.soc) * 100).toFixed(0)}%` : "-";
  const temp = state.temp != null ? `${Number(state.temp).toFixed(0)}°C` : "-";

  return (
    <div style={{ padding: 24, maxWidth: 1280, margin: "0 auto" }}>
      <Title level={3}>
        <SoundOutlined style={{ marginRight: 8, color: "#0EA5E9" }} />
        智能座舱陪伴
      </Title>
      <Text type="secondary">场景建议卡片 · 长期偏好记忆 —— 只建议、绝不下发车辆控制指令（AGT-205）</Text>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={14}>
          <Card title="场景建议" extra={<Button icon={<ReloadOutlined />} onClick={loadSuggestions}>刷新</Button>}>
            <Space wrap style={{ marginBottom: 16 }}>
              <Select value={timeOfDay} onChange={setTimeOfDay} style={{ width: 120 }}
                options={[
                  { value: "morning", label: "早晨" },
                  { value: "noon", label: "中午" },
                  { value: "evening", label: "傍晚" },
                  { value: "night", label: "夜间" },
                ]} />
              <span>车速 <InputNumber value={speed} onChange={(v) => setSpeed(Number(v ?? 0))} min={0} style={{ width: 90 }} /> km/h</span>
              <span>乘客 <InputNumber value={occupancy} onChange={(v) => setOccupancy(Number(v ?? 1))} min={1} max={4} style={{ width: 70 }} /> 人</span>
              <Button type="primary" onClick={loadSuggestions}>生成建议</Button>
            </Space>

            <Space style={{ marginBottom: 12 }}>
              <Tag color="blue">SOC {soc}</Tag>
              <Tag color="orange">电芯 {temp}</Tag>
            </Space>

            <List
              size="small"
              dataSource={cards}
              locale={{ emptyText: "暂无建议（服务未就绪或车辆无数据）" }}
              renderItem={(c) => (
                <List.Item>
                  <Space>
                    <Tag color={LEVEL_COLOR[c.level] ?? "default"}>{c.level === "warning" ? "提醒" : c.level === "success" ? "正常" : "提示"}</Tag>
                    <Text strong>{c.title}</Text>
                    <Text type="secondary">{c.detail}</Text>
                  </Space>
                </List.Item>
              )}
            />

            {redline && (
              <AntAlert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                message={redline}
              />
            )}
          </Card>
        </Col>

        <Col span={10}>
          <Card title="长期偏好记忆" extra={<SafetyCertificateOutlined />}>
            <Form layout="vertical" onFinish={savePrefs}>
              <Form.Item label="偏好温度 (°C)" name="temperature" initialValue={Number(prefs.temperature ?? 22)}>
                <InputNumber min={16} max={30} style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="偏好音乐类型" name="music" initialValue={String(prefs.music ?? "轻音乐")}>
                <Input placeholder="如 轻音乐 / 流行 / 古典" />
              </Form.Item>
              <Form.Item label="充电偏好" name="charging" initialValue={String(prefs.charging ?? "慢充优先")}>
                <Select options={[{ value: "慢充优先", label: "慢充优先（保护电池）" }, { value: "快充优先", label: "快充优先（省时间）" }]} />
              </Form.Item>
              <Button type="primary" htmlType="submit">保存偏好</Button>
            </Form>
            <Text type="secondary" style={{ display: "block", marginTop: 12 }}>
              偏好记忆跨会话留存，供座舱个性化建议使用
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
