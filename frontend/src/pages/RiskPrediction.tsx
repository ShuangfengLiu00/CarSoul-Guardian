import { useState, useCallback, useEffect } from "react";
import {
  Card,
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
  Select,
  Tooltip,
  Drawer,
  Timeline,
  Progress,
  Badge,
  Descriptions,
  Alert,
  message,
} from "antd";
import {
  AlertOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  SafetyCertificateOutlined,
  EyeOutlined,
  FieldTimeOutlined,
  RobotOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useCurrentVehicle, useRole, ROLE_DISCLOSURE, ROLE_LABELS } from "@/hooks";
import DemoBadge from "@/components/DemoBadge";
import { riskService } from "@/services";
import type {
  RiskPrediction,
  RiskPredictionDetail,
  RiskAccuracyStats,
  PatrolSummary,
  SchedulerStatus,
  FeedbackOutcome,
} from "@/services/riskService";

const { Title, Text, Paragraph } = Typography;

/** 风险等级 → 颜色 / 中文标签。 */
const LEVEL_META: Record<string, { color: string; label: string }> = {
  info: { color: "blue", label: "提示" },
  low: { color: "cyan", label: "低" },
  medium: { color: "gold", label: "中" },
  warning: { color: "orange", label: "警告" },
  urgent: { color: "red", label: "紧急" },
};

/** 预测状态 → 颜色 / 中文标签。 */
const STATUS_META: Record<string, { color: string; label: string }> = {
  open: { color: "processing", label: "待处理" },
  acknowledged: { color: "warning", label: "已确认" },
  resolved: { color: "success", label: "已闭环" },
  expired: { color: "default", label: "已过期" },
};

/** 触发来源 → 中文。 */
const TRIGGER_LABEL: Record<string, string> = {
  user: "用户触发",
  patrol: "主动巡检",
  alert: "告警触发",
  scheduled: "定时调度",
};

/** 反馈结果 → 中文。 */
const OUTCOME_LABEL: Record<string, string> = {
  confirmed: "风险已发生",
  false_alarm: "误报",
  no_event: "未发生",
  partial: "部分发生",
};

export default function RiskPrediction() {
  const { vehicle, loading: vehicleLoading } = useCurrentVehicle();
  const [predictions, setPredictions] = useState<RiskPrediction[]>([]);
  const [accuracy, setAccuracy] = useState<RiskAccuracyStats | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [accLoading, setAccLoading] = useState(false);
  const [patrolling, setPatrolling] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<RiskPredictionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<RiskPrediction | null>(null);
  const [feedbackOutcome, setFeedbackOutcome] = useState<FeedbackOutcome>("confirmed");
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const vehicleId = vehicle?.id;

  // 全局客户角色 → 差异化披露策略（切换角色后本页字段集随之变化）
  const { role } = useRole();
  const d = ROLE_DISCLOSURE[role];

  /** 拉取预测列表。 */
  const fetchPredictions = useCallback(async () => {
    if (!vehicleId) return;
    setListLoading(true);
    try {
      const res = await riskService.listPredictions(vehicleId, statusFilter);
      setPredictions(res.items);
    } catch {
      setPredictions([]);
    } finally {
      setListLoading(false);
    }
  }, [vehicleId, statusFilter]);

  /** 拉取准确率。 */
  const fetchAccuracy = useCallback(async () => {
    if (!vehicleId) return;
    setAccLoading(true);
    try {
      const res = await riskService.getAccuracy(vehicleId);
      setAccuracy(res);
    } catch {
      setAccuracy(null);
    } finally {
      setAccLoading(false);
    }
  }, [vehicleId]);

  /** 拉取调度器状态。 */
  const fetchScheduler = useCallback(async () => {
    try {
      const res = await riskService.schedulerStatus();
      setScheduler(res);
    } catch {
      setScheduler(null);
    }
  }, []);

  useEffect(() => {
    fetchPredictions();
    fetchAccuracy();
    fetchScheduler();
  }, [fetchPredictions, fetchAccuracy, fetchScheduler]);

  /** 手动触发单车主预测。 */
  const handlePredict = useCallback(async () => {
    if (!vehicleId) return;
    setPredicting(true);
    try {
      await riskService.triggerPrediction(vehicleId);
      message.success("已触发一次风险预测");
      fetchPredictions();
      fetchAccuracy();
    } catch {
      /* 全局拦截器已提示 */
    } finally {
      setPredicting(false);
    }
  }, [vehicleId, fetchPredictions, fetchAccuracy]);

  /** 手动触发全车巡检。 */
  const handlePatrol = useCallback(async () => {
    setPatrolling(true);
    try {
      const res: PatrolSummary = await riskService.patrol();
      message.success(
        `巡检完成：${res.patrolled} 辆车，${res.predictions_made} 条预测，${res.alerts_generated} 条告警`,
      );
      fetchPredictions();
      fetchAccuracy();
    } catch {
      /* 全局拦截器已提示 */
    } finally {
      setPatrolling(false);
    }
  }, [fetchPredictions, fetchAccuracy]);

  /** 查看预测详情（含推理轨迹）。 */
  const handleViewDetail = useCallback(async (id: number) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await riskService.getPrediction(id);
      setDetail(res);
    } catch {
      /* 全局拦截器已提示 */
    } finally {
      setDetailLoading(false);
    }
  }, []);

  /** 确认预测。 */
  const handleAcknowledge = useCallback(
    async (id: number) => {
      try {
        await riskService.acknowledge(id);
        message.success("已确认该预测");
        fetchPredictions();
      } catch {
        /* 全局拦截器已提示 */
      }
    },
    [fetchPredictions],
  );

  /** 打开反馈弹窗。 */
  const openFeedback = (pred: RiskPrediction) => {
    setFeedbackTarget(pred);
    setFeedbackOutcome("confirmed");
    setFeedbackNotes("");
  };

  /** 提交反馈（闭合环路）。 */
  const handleSubmitFeedback = useCallback(async () => {
    if (!feedbackTarget) return;
    setSubmitting(true);
    try {
      await riskService.submitFeedback(
        feedbackTarget.id,
        feedbackOutcome,
        feedbackNotes || undefined,
      );
      message.success("反馈已提交，准确率已更新");
      setFeedbackTarget(null);
      fetchPredictions();
      fetchAccuracy();
    } catch {
      /* 全局拦截器已提示 */
    } finally {
      setSubmitting(false);
    }
  }, [feedbackTarget, feedbackOutcome, feedbackNotes, fetchPredictions, fetchAccuracy]);

  if (vehicleLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" tip="加载车辆信息…" />
      </div>
    );
  }

  if (!vehicle) {
    return (
      <Card className="cs-card">
        <Empty description="暂无车辆，请先在车辆档案中添加车辆" />
      </Card>
    );
  }

  const accRate = accuracy?.accuracy_rate;
  const farRate = accuracy?.false_alarm_rate;

  return (
    <div>
      {/* Header */}
      <Space
        style={{ justifyContent: "space-between", width: "100%", marginBottom: 16 }}
        wrap
      >
        <Space align="center">
          <AlertOutlined style={{ fontSize: 28, color: "#3b82f6" }} />
          <Title level={3} style={{ margin: 0 }}>
            风险预测闭环
          </Title>
          {/* 当前车辆为 seed 持久虚构车「小白」，预测基于演示数据 — 挂 L2b 角标修复 GOAI 红线2 正向失真。
              TODO: 待后端 provenance 信封（R-01）落地后改为 level={provenance.badge_level} 驱动，不再硬编码。 */}
          <DemoBadge level="L2b" inline />
          {scheduler?.running ? (
            <Badge status="processing" text="主动巡检运行中" />
          ) : (
            <Badge status="warning" text="手动巡检模式" />
          )}
        </Space>
        <Space wrap>
          <Tooltip title="为当前车辆触发一次预测">
            <Button
              icon={<ExperimentOutlined />}
              onClick={handlePredict}
              loading={predicting}
            >
              触发预测
            </Button>
          </Tooltip>
          <Tooltip title="为所有活跃车辆运行一次主动巡检">
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handlePatrol}
              loading={patrolling}
            >
              主动巡检
            </Button>
          </Tooltip>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchPredictions();
              fetchAccuracy();
              fetchScheduler();
            }}
          >
            刷新
          </Button>
        </Space>
      </Space>

      {/* 客户角色视角横幅：切换角色后文案与下方字段集同步变化 */}
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={`当前视角：${ROLE_LABELS[role]}`}
        description={d.perspective}
      />

      {/* 调度器状态卡（演示"主动守护"真实性） */}
      {scheduler && (
        <Card className="cs-card" size="small" style={{ marginBottom: 16 }}>
          <Space size="large" wrap>
            <Space size={6}>
              <SafetyCertificateOutlined style={{ color: scheduler.running ? "#52c41a" : "#faad14" }} />
              <Text strong>{scheduler.running ? "主动巡检已开启" : "主动巡检未开启"}</Text>
            </Space>
            {scheduler.jobs[0]?.next_run_time && (
              <Text type="secondary" style={{ fontSize: 13 }}>
                <FieldTimeOutlined /> 下次巡检：{new Date(scheduler.jobs[0].next_run_time).toLocaleString("zh-CN")}
              </Text>
            )}
            <Text type="secondary" style={{ fontSize: 13 }}>
              {scheduler.message}
            </Text>
          </Space>
        </Card>
      )}

      {/* 准确率看板 — 闭环 KPI */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card className="cs-card" loading={accLoading}>
            <Statistic
              title="预测总数"
              value={accuracy?.total_predictions ?? 0}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        {d.showInternalKpi && (
        <Col xs={12} md={6}>
          <Card className="cs-card" loading={accLoading}>
            <Statistic
              title="准确率"
              value={accRate != null ? `${(accRate * 100).toFixed(1)}%` : "—"}
              valueStyle={{ color: accRate != null && accRate >= 0.8 ? "#3f8600" : "#cf1322" }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        )}
        {d.showInternalKpi && (
        <Col xs={12} md={6}>
          <Card className="cs-card" loading={accLoading}>
            <Statistic
              title="误报率"
              value={farRate != null ? `${(farRate * 100).toFixed(1)}%` : "—"}
              valueStyle={{ color: farRate != null && farRate <= 0.2 ? "#3f8600" : "#cf1322" }}
            />
          </Card>
        </Col>
        )}
        {d.showInternalKpi && (
        <Col xs={12} md={6}>
          <Card className="cs-card" loading={accLoading}>
            <Statistic
              title="已反馈样本"
              value={accuracy?.with_feedback ?? 0}
              suffix={`/ ${accuracy?.resolved_predictions ?? 0}`}
            />
          </Card>
        </Col>
        )}
      </Row>

      {/* 筛选 + 预测列表 */}
      <Card
        className="cs-card"
        title={
          <Space>
            <AlertOutlined />
            <Text strong>预测历史</Text>
            <Tag>{predictions.length}</Tag>
          </Space>
        }
        extra={
          <Select
            allowClear
            placeholder="按状态筛选"
            style={{ width: 140 }}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v)}
            options={Object.entries(STATUS_META).map(([value, { label }]) => ({
              value,
              label,
            }))}
          />
        }
      >
        {listLoading ? (
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spin size="large" tip="加载预测记录…" />
          </div>
        ) : predictions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                暂无预测记录。
                <br />
                点击「触发预测」或「主动巡检」开始。
              </span>
            }
          />
        ) : (
          <div>
            {predictions.map((p) => {
              const lm = LEVEL_META[p.predicted_level] || LEVEL_META.info;
              const sm = STATUS_META[p.status] || STATUS_META.open;
              return (
                <Card
                  key={p.id}
                  className="cs-card"
                  size="small"
                  style={{ marginBottom: 12 }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <Space size={6} wrap style={{ marginBottom: 6 }}>
                        <Tag color={lm.color}>{lm.label}</Tag>
                        <Tag color={sm.color}>{sm.label}</Tag>
                        <Tag>{TRIGGER_LABEL[p.triggered_by] || p.triggered_by}</Tag>
                        {p.is_normal && <Tag color="green">正常</Tag>}
                        {d.showProbability && p.predicted_probability != null && (
                          <Tag color={p.predicted_probability >= 60 ? "red" : "orange"}>
                            风险 {p.predicted_probability}%
                          </Tag>
                        )}
                        {p.predicted_eta_hours != null && (
                          <Tag>
                            <FieldTimeOutlined /> ETA {p.predicted_eta_hours}h
                          </Tag>
                        )}
                      </Space>
                      <Paragraph
                        className="cs-selectable"
                        style={{ margin: 0, fontWeight: 600 }}
                      >
                        {p.root_cause || (p.is_normal ? "未发现异常" : "需进一步诊断")}
                      </Paragraph>
                      {p.explanation && (
                        <Paragraph
                          className="cs-selectable"
                          type="secondary"
                          style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.6 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {p.explanation}
                        </Paragraph>
                      )}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(p.created_at).toLocaleString("zh-CN")}
                        {d.showOutcome && p.actual_outcome && (
                          <span>
                            {" · "}反馈：{OUTCOME_LABEL[p.actual_outcome] || p.actual_outcome}
                            {d.showInternalKpi && p.accuracy != null && `（${(p.accuracy * 100).toFixed(0)}%）`}
                          </span>
                        )}
                      </Text>
                    </div>
                    <Space direction="vertical" size={6}>
                      {d.showTechnical && (
                      <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleViewDetail(p.id)}
                      >
                        推理轨迹
                      </Button>
                      )}
                      {p.status === "open" && (
                        <Button
                          size="small"
                          type="primary"
                          ghost
                          onClick={() => handleAcknowledge(p.id)}
                        >
                          确认
                        </Button>
                      )}
                      {(p.status === "acknowledged" || p.status === "open") && (
                        <Button
                          size="small"
                          onClick={() => openFeedback(p)}
                        >
                          提交反馈
                        </Button>
                      )}
                    </Space>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </Card>

      {/* 推理轨迹 Drawer */}
      <Drawer
        title={
          <Space>
            <RobotOutlined />
            <Text strong>预测推理轨迹</Text>
            {detail && <Tag>#{detail.id}</Tag>}
          </Space>
        }
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={520}
      >
        {detailLoading ? (
          <div style={{ textAlign: "center", padding: 60 }}>
            <Spin size="large" />
          </div>
        ) : detail ? (
          <div>
            <Descriptions
              column={1}
              size="small"
              bordered
              style={{ marginBottom: 16 }}
            >
              <Descriptions.Item label="根因">
                {detail.root_cause || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="风险等级">
                <Tag color={(LEVEL_META[detail.predicted_level] || LEVEL_META.info).color}>
                  {(LEVEL_META[detail.predicted_level] || LEVEL_META.info).label}
                </Tag>
                {detail.predicted_probability != null && ` ${detail.predicted_probability}%`}
              </Descriptions.Item>
              <Descriptions.Item label="趋势">{detail.trend || "—"}</Descriptions.Item>
              {d.showTechnical && (
              <Descriptions.Item label="异常数">{detail.anomalies_count}</Descriptions.Item>
              )}
              {detail.actions_hint && detail.actions_hint.length > 0 && (
                <Descriptions.Item label="建议动作">
                  {detail.actions_hint.join("；")}
                </Descriptions.Item>
              )}
            </Descriptions>

            {detail.explanation && (
              <Card className="cs-card" size="small" style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>Agent 解释</Text>
                <Paragraph style={{ margin: "4px 0 0", whiteSpace: "pre-wrap" }}>
                  {detail.explanation}
                </Paragraph>
              </Card>
            )}

            <Text strong style={{ display: "block", marginBottom: 12 }}>
              <EyeOutlined /> 推理轨迹（Trace Log）
            </Text>
            {d.showTechnical && detail.trace_log && detail.trace_log.length > 0 ? (
              <Timeline
                items={detail.trace_log.map((t, i) => {
                  const step = String(t.step || t.agent || `步骤 ${i + 1}`);
                  const agent = t.agent ? String(t.agent) : "";
                  const detailText = t.detail ? String(t.detail) : "";
                  return {
                    color:
                      step === "act"
                        ? "green"
                        : step === "reason"
                          ? "orange"
                          : "blue",
                    children: (
                      <div>
                        <Space size={6} wrap>
                          <Tag>{step}</Tag>
                          {agent && <Text type="secondary" style={{ fontSize: 12 }}>{agent}</Text>}
                        </Space>
                        {detailText && (
                          <Paragraph style={{ margin: "4px 0 0", fontSize: 13 }}>
                            {detailText}
                          </Paragraph>
                        )}
                      </div>
                    ),
                  };
                })}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无推理轨迹" />
            )}
          </div>
        ) : (
          <Empty description="加载失败" />
        )}
      </Drawer>

      {/* 反馈弹窗 */}
      <Modal
        title="提交处置结果（闭合环路）"
        open={!!feedbackTarget}
        onCancel={() => setFeedbackTarget(null)}
        onOk={handleSubmitFeedback}
        confirmLoading={submitting}
        okText="提交反馈"
        cancelText="取消"
      >
        {feedbackTarget && (
          <div>
            <Card className="cs-card" size="small" style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>预测内容</Text>
              <Paragraph style={{ margin: "4px 0 0", fontWeight: 600 }}>
                {feedbackTarget.root_cause || "—"}
              </Paragraph>
              <Space size={6} style={{ marginTop: 4 }}>
                <Tag color={(LEVEL_META[feedbackTarget.predicted_level] || LEVEL_META.info).color}>
                  {(LEVEL_META[feedbackTarget.predicted_level] || LEVEL_META.info).label}
                </Tag>
                {feedbackTarget.predicted_probability != null && (
                  <Tag>风险 {feedbackTarget.predicted_probability}%</Tag>
                )}
              </Space>
            </Card>
            <Text strong style={{ display: "block", marginBottom: 8 }}>
              实际处置结果
            </Text>
            <Select
              value={feedbackOutcome}
              onChange={setFeedbackOutcome}
              style={{ width: "100%", marginBottom: 16 }}
              options={(Object.keys(OUTCOME_LABEL) as FeedbackOutcome[]).map((k) => ({
                value: k,
                label: OUTCOME_LABEL[k],
              }))}
            />
            <Text strong style={{ display: "block", marginBottom: 8 }}>
              备注（可选）
            </Text>
            <Select
              allowClear
              placeholder="选择或输入备注"
              mode="tags"
              maxCount={1}
              style={{ width: "100%" }}
              value={feedbackNotes ? [feedbackNotes] : []}
              onChange={(v) => setFeedbackNotes(v[0] || "")}
              options={[
                { value: "已联系服务中心处理", label: "已联系服务中心处理" },
                { value: "车主自行检查无异常", label: "车主自行检查无异常" },
                { value: "已安排保养", label: "已安排保养" },
              ]}
            />
            <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
              提交后系统将自动计算准确率并关闭关联告警，完成"预测 → 反馈 → 自校准"闭环。
            </Paragraph>
          </div>
        )}
      </Modal>
    </div>
  );
}
