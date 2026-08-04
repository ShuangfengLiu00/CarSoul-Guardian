import { useState, useCallback, useEffect } from "react";
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  Modal,
  Form,
  Select,
  Tooltip,
  Divider,
  message,
} from "antd";
import {
  SearchOutlined,
  BookOutlined,
  DatabaseOutlined,
  PlusOutlined,
  ReloadOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { knowledgeService } from "@/services";
import type {
  KnowledgeChunk,
  KnowledgeStats,
  KnowledgeSearchResponse,
} from "@/services/types";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

/** Category → color mapping for visual consistency. */
const CATEGORY_COLORS: Record<string, string> = {
  maintenance: "blue",
  fault_diagnosis: "red",
  ev_battery: "green",
  driving_tips: "cyan",
  tire_brake: "orange",
  insurance_law: "purple",
  new_car_guide: "geekblue",
  used_car: "volcano",
  general: "default",
};

const CATEGORY_LABELS: Record<string, string> = {
  maintenance: "保养维护",
  fault_diagnosis: "故障诊断",
  ev_battery: "新能源电池",
  driving_tips: "驾驶技巧",
  tire_brake: "轮胎刹车",
  insurance_law: "保险法规",
  new_car_guide: "新车指南",
  used_car: "二手车",
  general: "通用",
};

/** Suggested queries for quick search. */
const SUGGESTIONS = [
  "机油多久换一次？",
  "发动机故障灯亮了怎么办？",
  "新能源车冬季续航下降怎么解决？",
  "刹车片什么时候需要更换？",
  "新车磨合期注意事项",
  "买二手车怎么检查车况？",
  "轮胎花纹磨损到什么程度需要换？",
  "车险应该买哪些险种？",
];

export default function KnowledgeBase() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<KnowledgeChunk[]>([]);
  const [searched, setSearched] = useState(false);
  const [context, setContext] = useState("");
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [ingestOpen, setIngestOpen] = useState(false);
  const [ingestForm] = Form.useForm();
  const [ingesting, setIngesting] = useState(false);

  /** Fetch knowledge base stats. */
  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const s = await knowledgeService.stats();
      setStats(s);
    } catch {
      /* error handled by global interceptor */
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  /** Execute a knowledge base search. */
  const handleSearch = useCallback(
    async (q?: string) => {
      const searchText = (q ?? query).trim();
      if (!searchText) return;
      if (q) setQuery(q);
      setLoading(true);
      setSearched(true);
      try {
        const res: KnowledgeSearchResponse = await knowledgeService.search({
          query: searchText,
          top_k: topK,
        });
        setResults(res.results);
        setContext(res.context);
      } catch {
        setResults([]);
        setContext("");
      } finally {
        setLoading(false);
      }
    },
    [query, topK],
  );

  /** Rebuild the knowledge base index. */
  const handleRebuild = useCallback(async () => {
    setRebuilding(true);
    try {
      const res = await knowledgeService.rebuild();
      message.success(res.message || `知识库已重建，共 ${res.chunks} 个片段`);
      fetchStats();
    } catch {
      /* handled globally */
    } finally {
      setRebuilding(false);
    }
  }, [fetchStats]);

  /** Submit the ingest form. */
  const handleIngest = useCallback(async () => {
    try {
      const values = await ingestForm.validateFields();
      setIngesting(true);
      const res = await knowledgeService.ingest({
        title: values.title,
        category: values.category,
        content: values.content,
        source: values.source || "web-ui",
      });
      message.success(res.message || `成功导入 ${res.chunks_added} 个片段`);
      ingestForm.resetFields();
      setIngestOpen(false);
      fetchStats();
    } catch {
      /* validation or API error */
    } finally {
      setIngesting(false);
    }
  }, [ingestForm, fetchStats]);

  /** Score → color for the relevance tag. */
  const scoreColor = (score: number) => {
    if (score >= 0.7) return "green";
    if (score >= 0.4) return "blue";
    if (score >= 0.2) return "orange";
    return "default";
  };

  return (
    <div>
      {/* Header */}
      <Space
        style={{ justifyContent: "space-between", width: "100%", marginBottom: 16 }}
      >
        <Space align="center">
          <BookOutlined style={{ fontSize: 28, color: "#3b82f6" }} />
          <Title level={3} style={{ margin: 0 }}>
            汽车知识库
          </Title>
          {stats?.ready && (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已就绪
            </Tag>
          )}
        </Space>
        <Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => setIngestOpen(true)}
          >
            导入文档
          </Button>
          <Tooltip title="从内置文档重建索引">
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRebuild}
              loading={rebuilding}
            >
              重建索引
            </Button>
          </Tooltip>
        </Space>
      </Space>

      {/* Stats Bar */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card className="cs-card" loading={statsLoading}>
            <Statistic
              title="知识片段"
              value={stats?.chunk_count ?? 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="cs-card" loading={statsLoading}>
            <Statistic
              title="向量后端"
              value={stats?.backend ?? "—"}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="cs-card" loading={statsLoading}>
            <Statistic
              title="嵌入模型"
              value={stats?.embedder ?? "—"}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="cs-card" loading={statsLoading}>
            <Statistic
              title="状态"
              value={stats?.ready ? "就绪" : "未就绪"}
              valueStyle={{ color: stats?.ready ? "#3f8600" : "#cf1322" }}
            />
          </Card>
        </Col>
      </Row>

      {/* Search Bar */}
      <Card className="cs-card" style={{ marginBottom: 16 }}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入汽车相关问题或关键词…（如：机油多久换一次）"
            size="large"
            onPressEnter={() => handleSearch()}
            prefix={<SearchOutlined style={{ color: "#9ca3af" }} />}
            style={{ borderRadius: "10px 0 0 10px" }}
          />
          <Select
            value={topK}
            onChange={setTopK}
            size="large"
            style={{ width: 100 }}
            options={[
              { value: 3, label: "Top 3" },
              { value: 5, label: "Top 5" },
              { value: 10, label: "Top 10" },
              { value: 15, label: "Top 15" },
            ]}
          />
          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={() => handleSearch()}
            loading={loading}
            style={{ borderRadius: "0 10px 10px 0" }}
          >
            检索
          </Button>
        </Space.Compact>

        {/* Quick suggestions */}
        {!searched && (
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              热门问题：
            </Text>
            <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 8 }}>
              {SUGGESTIONS.map((s) => (
                <Tag
                  key={s}
                  style={{ cursor: "pointer", padding: "4px 12px", fontSize: 13 }}
                  onClick={() => handleSearch(s)}
                >
                  {s}
                </Tag>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Search Results */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Spin size="large" tip="正在检索知识库…" />
        </div>
      ) : searched ? (
        results.length > 0 ? (
          <div>
            <Space style={{ marginBottom: 12 }}>
              <Text strong>检索到 {results.length} 条结果</Text>
              <Text type="secondary" style={{ fontSize: 13 }}>
                查询：「{query}」
              </Text>
            </Space>
            {results.map((chunk, idx) => (
              <Card
                key={idx}
                className="cs-card"
                style={{ marginBottom: 12 }}
                size="small"
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: 8,
                  }}
                >
                  <Space size={6} wrap>
                    <FileTextOutlined style={{ color: "#3b82f6" }} />
                    <Text strong>{chunk.title}</Text>
                    {chunk.heading && (
                      <Text type="secondary">· {chunk.heading}</Text>
                    )}
                  </Space>
                  <Space size={6}>
                    <Tag color={CATEGORY_COLORS[chunk.category] || "default"}>
                      {CATEGORY_LABELS[chunk.category] || chunk.category}
                    </Tag>
                    <Tag color={scoreColor(chunk.score)}>
                      相关度 {(chunk.score * 100).toFixed(0)}%
                    </Tag>
                    <Tag>{chunk.backend}</Tag>
                  </Space>
                </div>
                <Paragraph
                  className="cs-selectable"
                  style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.7 }}
                >
                  {chunk.text}
                </Paragraph>
                {chunk.source && (
                  <Text
                    type="secondary"
                    style={{ fontSize: 12, marginTop: 8, display: "block" }}
                  >
                    来源：{chunk.source}
                  </Text>
                )}
              </Card>
            ))}

            {/* Context preview (collapsible) */}
            {context && (
              <Card
                className="cs-card"
                style={{ marginTop: 8 }}
                size="small"
                title={
                  <Space>
                    <DatabaseOutlined />
                    <Text strong>RAG 上下文（注入 LLM 的检索结果）</Text>
                  </Space>
                }
              >
                <Paragraph
                  className="cs-selectable"
                  style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6, color: "#6b7280" }}
                >
                  {context}
                </Paragraph>
              </Card>
            )}
          </div>
        ) : (
          <Card className="cs-card">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span>
                  未找到相关知识。
                  <br />
                  试试换个关键词，或
                  <Button type="link" size="small" onClick={() => setIngestOpen(true)}>
                    导入新文档
                  </Button>
                </span>
              }
            />
          </Card>
        )
      ) : (
        <Card className="cs-card">
          <Empty
            image={<BookOutlined style={{ fontSize: 48, color: "#3b82f6" }} />}
            description={
              <span>
                汽车知识库已就绪。
                <br />
                输入问题或点击热门话题开始检索。
              </span>
            }
          />
        </Card>
      )}

      {/* Ingest Modal */}
      <Modal
        title="导入知识文档"
        open={ingestOpen}
        onCancel={() => setIngestOpen(false)}
        onOk={handleIngest}
        confirmLoading={ingesting}
        okText="导入"
        cancelText="取消"
        width={640}
        destroyOnHidden
      >
        <Divider style={{ margin: "12px 0 20px" }} />
        <Form form={ingestForm} layout="vertical">
          <Form.Item
            name="title"
            label="文档标题"
            rules={[{ required: true, message: "请输入标题" }]}
          >
            <Input placeholder="如：冬季轮胎使用指南" />
          </Form.Item>
          <Form.Item
            name="category"
            label="类别"
            rules={[{ required: true, message: "请选择类别" }]}
          >
            <Select
              placeholder="选择文档类别"
              options={Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="content"
            label="文档内容（Markdown / 纯文本）"
            rules={[{ required: true, message: "请输入内容" }]}
          >
            <TextArea
              rows={8}
              placeholder="输入文档内容…支持 Markdown 格式。内容将被自动分块、嵌入向量并索引到知识库。"
              showCount
            />
          </Form.Item>
          <Form.Item name="source" label="来源标识（可选）">
            <Input placeholder="如：web-ui、用户贡献、官方手册" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
