import { useEffect, useState } from "react";
import {
  Card,
  Tabs,
  Table,
  Form,
  InputNumber,
  Select,
  Button,
  Space,
  Tag,
  Typography,
  Alert as AntAlert,
  Descriptions,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import { CarOutlined, BulbOutlined, SwapOutlined } from "@ant-design/icons";
import { buyService } from "@/services/buyService";
import type { BuyVehicle } from "@/services/buyService";

const { Title, Text } = Typography;
const { Option } = Select;

const CHEM_COLORS: Record<string, string> = { LFP: "green", NCA: "blue", NMC: "purple" };

export default function BuyAdvisor() {
  const [catalog, setCatalog] = useState<BuyVehicle[]>([]);
  const [recs, setRecs] = useState<BuyVehicle[]>([]);
  const [recNote, setRecNote] = useState("");
  const [compareA, setCompareA] = useState<string | undefined>();
  const [compareB, setCompareB] = useState<string | undefined>();
  const [cmp, setCmp] = useState<{ a: BuyVehicle; b: BuyVehicle; keys: string[] } | null>(null);

  const loadCatalog = () => {
    buyService.catalog().then((r) => setCatalog(r.items ?? [])).catch(() => setCatalog([]));
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  const doRecommend = (v: { max_budget?: number; chemistry?: string; purpose?: string }) => {
    buyService
      .recommend({ max_budget: v.max_budget ?? null, preferred_chemistry: v.chemistry ?? null, purpose: v.purpose ?? null, top_k: 5 })
      .then((r) => {
        setRecs(r.items ?? []);
        setRecNote(r.note ?? "");
        if (r.budget_note) message.warning(r.budget_note);
      })
      .catch(() => setRecs([]));
  };

  const doCompare = () => {
    if (!compareA || !compareB) {
      message.warning("请选择两款车型对比");
      return;
    }
    buyService.compare(compareA, compareB).then(setCmp).catch(() => setCmp(null));
  };

  const modelName = (v: BuyVehicle) => `${v.brand} ${v.model}`;
  const catalogOptions = catalog.map((v) => ({ value: modelName(v), label: modelName(v) }));

  const catalogCols: TableColumnsType<BuyVehicle> = [
    { title: "品牌", dataIndex: "brand", key: "brand", width: 100 },
    { title: "车型", dataIndex: "model", key: "model" },
    { title: "化学体系", dataIndex: "chemistry", key: "chemistry", width: 100, render: (v) => <Tag color={CHEM_COLORS[v] ?? "default"}>{v}</Tag> },
    { title: "电池(kWh)", dataIndex: "capacity_kwh", key: "capacity", width: 100 },
    { title: "续航(km)", dataIndex: "range_km", key: "range", width: 100 },
    { title: "保值评分", dataIndex: "value_score", key: "value", width: 100, render: (v) => (v * 100).toFixed(0) },
  ];

  const recCols: TableColumnsType<BuyVehicle> = [
    { title: "排名", key: "rank", width: 60, render: (_, __, i) => <Text strong>{i + 1}</Text> },
    { title: "品牌", dataIndex: "brand", key: "brand", width: 100 },
    { title: "车型", dataIndex: "model", key: "model" },
    { title: "化学", dataIndex: "chemistry", key: "chemistry", width: 90, render: (v) => <Tag color={CHEM_COLORS[v] ?? "default"}>{v}</Tag> },
    { title: "续航", dataIndex: "range_km", key: "range", width: 90 },
    { title: "推荐分", dataIndex: "score", key: "score", width: 90, render: (v) => <Text style={{ color: "#2563EB", fontWeight: "bold" }}>{v}</Text> },
    { title: "说明", dataIndex: "chem_note", key: "note", ellipsis: true },
  ];

  const cmpRows =
    cmp?.keys.map((k) => ({
      key: k,
      field: k,
      a: String(cmp.a[k as keyof BuyVehicle] ?? "-"),
      b: String(cmp.b[k as keyof BuyVehicle] ?? "-"),
    })) ?? [];

  return (
    <div style={{ padding: 24, maxWidth: 1280, margin: "0 auto" }}>
      <Title level={3}>
        <CarOutlined style={{ marginRight: 8, color: "#2563EB" }} />
        智能购车顾问
      </Title>
      <Text type="secondary">车型推荐 · 配置对比 · 购车方案 —— 基于真实在售 EV 车型库（AGT-209）</Text>

      <Tabs
        style={{ marginTop: 16 }}
        items={[
          {
            key: "catalog",
            label: (<Space><CarOutlined />车型库</Space>),
            children: (
              <Card>
                <Table rowKey={(r) => `${r.brand}${r.model}`} columns={catalogCols} dataSource={catalog} size="small" pagination={false} />
              </Card>
            ),
          },
          {
            key: "recommend",
            label: (<Space><BulbOutlined />智能推荐</Space>),
            children: (
              <Card>
                <Form layout="inline" onFinish={doRecommend} style={{ marginBottom: 16 }}>
                  <Form.Item name="max_budget" label="预算(万元)">
                    <InputNumber min={0} placeholder="如 25" style={{ width: 130 }} />
                  </Form.Item>
                  <Form.Item name="chemistry" label="偏好化学">
                    <Select allowClear placeholder="不限" style={{ width: 130 }}>
                      <Option value="LFP">LFP</Option>
                      <Option value="NCA">NCA</Option>
                      <Option value="NMC">NMC</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item name="purpose" label="用途">
                    <Select allowClear placeholder="不限" style={{ width: 120 }}>
                      <Option value="代步">代步</Option>
                      <Option value="家用">家用</Option>
                      <Option value="长途">长途</Option>
                    </Select>
                  </Form.Item>
                  <Button type="primary" htmlType="submit">开始推荐</Button>
                </Form>
                <AntAlert type="info" showIcon style={{ marginBottom: 12 }} message={recNote || "评分 = 续航40% + 化学30% + 品牌保值30%；演示推荐，非购车结论"} />
                <Table rowKey={(r) => `${r.brand}${r.model}`} columns={recCols} dataSource={recs} size="small" pagination={false} locale={{ emptyText: "设置条件后点击「开始推荐」" }} />
              </Card>
            ),
          },
          {
            key: "compare",
            label: (<Space><SwapOutlined />配置对比</Space>),
            children: (
              <Card>
                <Space wrap style={{ marginBottom: 16 }}>
                  <Select showSearch style={{ width: 200 }} placeholder="车型 A" options={catalogOptions} value={compareA} onChange={setCompareA} />
                  <Select showSearch style={{ width: 200 }} placeholder="车型 B" options={catalogOptions} value={compareB} onChange={setCompareB} />
                  <Button type="primary" onClick={doCompare}>对比</Button>
                </Space>
                {cmp && (
                  <Table rowKey="key" size="small" pagination={false}
                    columns={[
                      { title: "字段", dataIndex: "field", key: "field", width: 140 },
                      { title: cmp.a.model, dataIndex: "a", key: "a" },
                      { title: cmp.b.model, dataIndex: "b", key: "b" },
                    ]}
                    dataSource={cmpRows} />
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
