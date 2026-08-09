/**
 * Agent 进化引擎仪表盘 — 全息驾驶舱版
 * Experience → Knowledge → Skill → Intelligence 永续循环
 *
 * 五个 Tab:
 *  1. 进化总览     — Dashboard
 *  2. 经验挖掘     — Experience Mining
 *  3. 反思引擎     — Reflection Engine
 *  4. 技能进化     — Skill Evolution
 *  5. 进化时间线   — Evolution Timeline
 */
import { useState, useCallback, useEffect } from "react";
import {
  Tabs,
  Table,
  Timeline,
  message,
  Input,
  Empty,
  Spin,
} from "antd";
import {
  RocketOutlined,
  ExperimentOutlined,
  BulbOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  SearchOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  StarOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { GlassPanel, StatCard, EnergyRing, DataStream, CosmicAlert } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { evolutionService } from "@/services/evolutionService";
import type {
  EvolutionDashboard,
  ExperienceCase,
  ExperiencePattern,
  ReflectionReport,
  SkillMutationProposal,
  EvolutionTimelineEntry,
  CycleResult,
} from "@/services/evolutionService";

// ================================================================
// Shared holographic helpers
// ================================================================

/** Holographic chip — replacement for antd Tag in holographic context */
function HoloChip({
  children,
  color = "cyan",
}: {
  children: React.ReactNode;
  color?: "cyan" | "amber" | "red" | "green" | "purple" | "blue";
}) {
  const cls = `holo-chip holo-chip-${color === "blue" ? "" : color}`;
  return <span className={cls.trim()}>{children}</span>;
}

/** Holographic detail row */
function HoloDetailRow({
  label,
  value,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  accent?: string;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span className="holo-text-dim" style={{ fontSize: 12 }}>{label}</span>
      <span
        className="holo-text-bright"
        style={{ fontSize: 13, fontWeight: 600, color: accent, textShadow: accent ? `0 0 8px ${accent}55` : undefined }}
      >
        {value}
      </span>
    </div>
  );
}

/** Holographic action button */
function HoloButton({
  children,
  onClick,
  loading,
  variant = "cyan",
  icon,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  loading?: boolean;
  variant?: "cyan" | "purple" | "ghost";
  icon?: React.ReactNode;
}) {
  const cls = variant === "purple" ? "holo-btn holo-btn-purple" : variant === "ghost" ? "holo-btn holo-btn-ghost" : "holo-btn";
  return (
    <button
      type="button"
      className={cls}
      onClick={onClick}
      disabled={loading}
      style={{ opacity: loading ? 0.5 : 1, cursor: loading ? "not-allowed" : "pointer" }}
    >
      {loading ? <SyncOutlined spin /> : icon}
      {children}
    </button>
  );
}

// ================================================================
// Tab 1: 进化总览
// ================================================================

function DashboardTab({
  dashboard,
  loading,
  onRunCycle,
  onSeedDemo,
  running,
}: {
  dashboard: EvolutionDashboard | null;
  loading: boolean;
  onRunCycle: () => void;
  onSeedDemo: () => void;
  running: boolean;
}) {
  if (loading && !dashboard) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }
  if (!dashboard) {
    return (
      <GlassPanel corners scanline style={{ textAlign: "center", padding: 60 }}>
        <Empty description={<span className="holo-text-dim">暂无数据，请先种子演示数据</span>} />
      </GlassPanel>
    );
  }

  // 子对象在 EvolutionDashboard 中均为必填，桩默认返回 {}（各字段可选），
  // 此处不再写 `|| {}`，避免产生 `Stats | {}` 联合类型导致属性访问报错。
  const exp = dashboard.experience;
  const refl = dashboard.reflection;
  const skill = dashboard.skill_evolution;
  const evalSum = dashboard.evaluation;
  const mem = dashboard.evolution_memory;

  const successRate = Math.round((refl.success_rate ?? 0) * 100);
  const avgConfidence = Math.round((exp.avg_confidence ?? 0) * 100);

  return (
    <div>
      {/* 操作栏 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <HoloButton variant="cyan" icon={<PlayCircleOutlined />} onClick={onRunCycle} loading={running}>
          运行进化周期
        </HoloButton>
        <HoloButton variant="purple" icon={<ExperimentOutlined />} onClick={onSeedDemo} loading={running}>
          种子演示数据
        </HoloButton>
        <HoloChip color={dashboard.engine_enabled ? "green" : "cyan"}>
          引擎状态: {dashboard.engine_enabled ? "运行中" : "未启用"}
        </HoloChip>
        <HoloChip color="purple">总周期数: {dashboard.total_cycles ?? 0}</HoloChip>
      </div>

      {/* 核心指标卡片 */}
      <div className="holo-grid holo-grid-4" style={{ marginBottom: 16 }}>
        <StatCard
          label="经验案例"
          value={exp.total_cases ?? 0}
          unit={`/ ${exp.total_patterns ?? 0} 模式`}
          sub={`置信度 ${avgConfidence}%`}
          color="var(--holo-amber)"
          icon={<BulbOutlined />}
        />
        <StatCard
          label="反思报告"
          value={refl.total_reflections ?? 0}
          unit={`/ 成功率 ${successRate}%`}
          sub={`高优先级: ${refl.high_priority_count ?? 0} · Agent: ${refl.agents_reflected ?? 0}`}
          color="var(--holo-cyan)"
          icon={<SyncOutlined />}
        />
        <StatCard
          label="技能版本"
          value={skill.total_versions ?? 0}
          unit={`/ ${skill.tracked_skills ?? 0} 技能`}
          sub={`待审批: ${skill.pending_proposals ?? 0} · 已部署: ${skill.deployed_versions ?? 0}`}
          color="var(--holo-purple)"
          icon={<ThunderboltOutlined />}
        />
        <StatCard
          label="评估总数"
          value={evalSum.total_evaluations ?? 0}
          sub={`反馈: ${evalSum.feedback_count ?? 0} · 里程碑: ${mem.total_milestones ?? 0}`}
          color="var(--holo-green)"
          icon={<StarOutlined />}
        />
      </div>

      {/* 数据流分隔 */}
      <DataStream lines={4} height={40} color="var(--holo-purple)" />

      {/* 上次周期 + 能量环 + 记忆 */}
      <div className="holo-grid holo-grid-2" style={{ marginTop: 16 }}>
        {/* 上次进化周期 */}
        <GlassPanel title="上次进化周期" icon={<ClockCircleOutlined />} corners scanline className="holo-anim-fade-in">
          {dashboard.last_cycle ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <HoloDetailRow label="周期 ID" value={<span style={{ fontFamily: "monospace", fontSize: 12 }}>{dashboard.last_cycle.cycle_id}</span>} accent="var(--holo-cyan)" />
              <HoloDetailRow label="开始时间" value={dashboard.last_cycle.started_at} />
              <HoloDetailRow label="完成时间" value={dashboard.last_cycle.completed_at || "—"} />
              <div className="holo-divider" style={{ margin: "4px 0" }} />
              <HoloDetailRow label="经验挖掘" value={dashboard.last_cycle.experiences_mined} accent="var(--holo-amber)" />
              <HoloDetailRow label="模式发现" value={dashboard.last_cycle.patterns_discovered} accent="var(--holo-cyan)" />
              <HoloDetailRow label="改进生成" value={dashboard.last_cycle.improvements_generated} accent="var(--holo-green)" />
              <HoloDetailRow label="技能进化" value={dashboard.last_cycle.skills_evolved?.length ?? 0} accent="var(--holo-purple)" />
              <div className="holo-divider" style={{ margin: "4px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="holo-text-dim" style={{ fontSize: 12 }}>状态</span>
                {dashboard.last_cycle.success ? (
                  <HoloChip color="green"><CheckCircleOutlined /> 成功</HoloChip>
                ) : (
                  <HoloChip color="red"><CloseCircleOutlined /> 失败</HoloChip>
                )}
              </div>
              {dashboard.last_cycle.summary && (
                <>
                  <div className="holo-divider" style={{ margin: "4px 0" }} />
                  <div className="holo-glass" style={{ padding: 12, borderRadius: 10 }}>
                    <span className="holo-text" style={{ fontSize: 13, lineHeight: 1.6 }}>{dashboard.last_cycle.summary}</span>
                  </div>
                </>
              )}
            </div>
          ) : (
            <Empty description={<span className="holo-text-dim">尚未运行任何进化周期</span>} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </GlassPanel>

        {/* 右侧：能量环 + 记忆 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 进化健康能量环 */}
          <GlassPanel corners className="holo-anim-fade-scale" style={{ textAlign: "center" }}>
            <div className="holo-section-title" style={{ justifyContent: "center" }}>进化健康度</div>
            <div style={{ display: "flex", justifyContent: "center", gap: 40, padding: "12px 0 8px", flexWrap: "wrap" }}>
              <EnergyRing
                value={successRate}
                size={130}
                color="var(--holo-cyan)"
                label="成功率"
                subLabel={`${refl.total_reflections ?? 0} 次反思`}
                strokeWidth={10}
              />
              <EnergyRing
                value={avgConfidence}
                size={130}
                color="var(--holo-amber)"
                label="置信度"
                subLabel={`${exp.total_cases ?? 0} 条经验`}
                strokeWidth={10}
              />
            </div>
          </GlassPanel>

          {/* 进化记忆 */}
          <GlassPanel title="进化记忆" icon={<BulbOutlined />} corners className="holo-anim-fade-in">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <HoloDetailRow label="里程碑总数" value={mem.total_milestones ?? 0} accent="var(--holo-purple)" />
              <HoloDetailRow label="参与 Agent 数" value={mem.unique_agents ?? 0} accent="var(--holo-green)" />
              {mem.milestone_type_breakdown && Object.keys(mem.milestone_type_breakdown).length > 0 && (
                <>
                  <div className="holo-divider" style={{ margin: "4px 0" }} />
                  <div className="holo-text-dim" style={{ fontSize: 12, marginBottom: 6 }}>类型分布</div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {Object.entries(mem.milestone_type_breakdown).map(([k, v]) => (
                      <HoloChip key={k} color="purple">{k}: {v}</HoloChip>
                    ))}
                  </div>
                </>
              )}
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

// ================================================================
// Tab 2: 经验挖掘
// ================================================================

function ExperienceTab() {
  const [cases, setCases] = useState<ExperienceCase[]>([]);
  const [patterns, setPatterns] = useState<ExperiencePattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ExperienceCase[] | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [caseRes, patternRes] = await Promise.all([
        evolutionService.experienceCases(),
        evolutionService.experiencePatterns(),
      ]);
      setCases(caseRes.cases || []);
      setPatterns(patternRes.patterns || []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    try {
      const res = await evolutionService.searchExperience(searchQuery);
      setSearchResults((res.results as ExperienceCase[]) || []);
    } catch {
      message.error("搜索失败");
    }
  };

  const caseColumns: ColumnsType<ExperienceCase> = [
    {
      title: "任务类型",
      dataIndex: "task_type",
      key: "task_type",
      width: 120,
      render: (v: string) => <HoloChip color="cyan">{v}</HoloChip>,
    },
    {
      title: "Agent",
      dataIndex: "agent_id",
      key: "agent_id",
      width: 110,
      render: (v: string) => <span className="holo-text-dim" style={{ fontFamily: "monospace", fontSize: 12 }}>{v}</span>,
    },
    { title: "问题", dataIndex: "problem", key: "problem", width: 150, ellipsis: true },
    { title: "解决方案", dataIndex: "solution", key: "solution", width: 150, ellipsis: true },
    { title: "结果", dataIndex: "result", key: "result", ellipsis: true },
    {
      title: "置信度",
      dataIndex: "confidence",
      key: "confidence",
      width: 80,
      render: (v: number) => <HoloChip color={v > 0.7 ? "green" : "amber"}>{(v * 100).toFixed(0)}%</HoloChip>,
    },
    { title: "复用", dataIndex: "reuse_count", key: "reuse_count", width: 60 },
    {
      title: "时间",
      dataIndex: "created_time",
      key: "created_time",
      width: 150,
      render: (v: string) => <span className="holo-text-dim" style={{ fontSize: 12 }}>{v}</span>,
    },
  ];

  const displayCases = searchResults !== null ? searchResults : cases;

  return (
    <div>
      {/* 搜索栏 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Input
          placeholder="搜索相似经验..."
          prefix={<SearchOutlined style={{ color: "var(--holo-cyan)" }} />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 300, background: "rgba(255,255,255,0.06)", borderColor: "rgba(0,240,255,0.2)", color: "var(--holo-text)" }}
          allowClear
        />
        <HoloButton variant="cyan" icon={<SearchOutlined />} onClick={handleSearch}>搜索</HoloButton>
        <HoloButton variant="ghost" icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</HoloButton>
        {searchResults !== null && (
          <HoloButton variant="ghost" onClick={() => { setSearchResults(null); setSearchQuery(""); }}>清除搜索</HoloButton>
        )}
      </div>

      <div className="holo-grid holo-grid-2">
        {/* 经验模式 */}
        <GlassPanel title={`经验模式 (${patterns.length})`} icon={<BulbOutlined />} corners scanline className="holo-anim-fade-in">
          <Spin spinning={loading}>
            {patterns.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 500, overflowY: "auto", paddingRight: 4 }}>
                {patterns.map((p, i) => (
                  <div
                    key={i}
                    className="holo-glass holo-glass-hover holo-anim-fade-in"
                    style={{ padding: 12, borderRadius: 10, borderLeft: "3px solid var(--holo-purple)", animationDelay: `${i * 0.08}s` }}
                  >
                    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                      <HoloChip color="purple">{p.pattern_name}</HoloChip>
                      <span className="holo-text-bright" style={{ fontSize: 13, fontWeight: 600 }}>{p.description}</span>
                    </div>
                    <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                      <HoloChip>次数: {p.occurrence_count}</HoloChip>
                      <HoloChip color={p.success_rate > 0.7 ? "green" : "amber"}>
                        成功率: {(p.success_rate * 100).toFixed(0)}%
                      </HoloChip>
                      <HoloChip color={p.confidence > 0.7 ? "green" : "cyan"}>
                        置信度: {(p.confidence * 100).toFixed(0)}%
                      </HoloChip>
                    </div>
                    {p.common_solution && (
                      <div style={{ marginTop: 6 }}>
                        <span className="holo-text-dim" style={{ fontSize: 12 }}>共性方案: </span>
                        <HoloChip color="cyan">{p.common_solution}</HoloChip>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Empty description={<span className="holo-text-dim">暂无模式</span>} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Spin>
        </GlassPanel>

        {/* 经验案例 */}
        <GlassPanel
          title={`经验案例 (${displayCases.length})`}
          icon={<ExperimentOutlined />}
          corners
          className="holo-anim-fade-in"
          style={{ overflow: "hidden" }}
        >
          {searchResults !== null && (
            <div style={{ marginBottom: 8 }}>
              <HoloChip color="cyan">搜索结果</HoloChip>
            </div>
          )}
          <Table
            columns={caseColumns}
            dataSource={displayCases}
            rowKey="case_id"
            loading={loading}
            size="small"
            scroll={{ x: 800 }}
            pagination={{ pageSize: 6, size: "small" }}
            style={{ background: "transparent" }}
          />
        </GlassPanel>
      </div>
    </div>
  );
}

// ================================================================
// Tab 3: 反思引擎
// ================================================================

function ReflectionTab() {
  const [reflections, setReflections] = useState<ReflectionReport[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evolutionService.recentReflections(20);
      setReflections(res.reflections || []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <HoloButton variant="ghost" icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</HoloButton>
        <span className="holo-text-dim" style={{ fontSize: 13 }}>最近 {reflections.length} 条反思报告</span>
      </div>

      <Spin spinning={loading}>
        {reflections.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {reflections.map((r, idx) => (
              <GlassPanel
                key={r.reflection_id}
                corners
                className="holo-anim-fade-in"
                style={{ animationDelay: `${idx * 0.06}s` }}
              >
                {/* 头部 */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <HoloChip color="cyan">{r.task_type}</HoloChip>
                    <span className="holo-text-dim" style={{ fontFamily: "monospace", fontSize: 12 }}>{r.agent_id}</span>
                    <HoloChip color={r.task_layer?.task_success ? "green" : "red"}>
                      {r.task_layer?.task_success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                      {r.task_layer?.task_success ? " 成功" : " 失败"}
                    </HoloChip>
                    <HoloChip color={r.improvement_priority === "high" ? "red" : r.improvement_priority === "medium" ? "amber" : "cyan"}>
                      优先级: {r.improvement_priority}
                    </HoloChip>
                  </div>
                  <span className="holo-text-dim" style={{ fontSize: 12 }}>{r.timestamp}</span>
                </div>

                {/* 三列：优势 / 不足 / 改进 */}
                <div className="holo-grid holo-grid-3">
                  <div className="holo-glass" style={{ padding: 14, borderRadius: 10, borderLeft: "3px solid var(--holo-green)" }}>
                    <div className="holo-text-green" style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                      <CheckCircleOutlined /> 优势
                    </div>
                    {(r.analysis?.strengths || []).length > 0 ? (
                      (r.analysis?.strengths || []).map((s, i) => (
                        <div key={i} className="holo-text" style={{ fontSize: 12, lineHeight: 1.8, paddingLeft: 4 }}>
                          <span className="holo-text-green">▸</span> {s}
                        </div>
                      ))
                    ) : (
                      <span className="holo-text-dim" style={{ fontSize: 12 }}>—</span>
                    )}
                  </div>

                  <div className="holo-glass" style={{ padding: 14, borderRadius: 10, borderLeft: "3px solid var(--holo-red)" }}>
                    <div className="holo-text-red" style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                      <CloseCircleOutlined /> 不足
                    </div>
                    {(r.analysis?.weaknesses || []).length > 0 ? (
                      (r.analysis?.weaknesses || []).map((s, i) => (
                        <div key={i} className="holo-text" style={{ fontSize: 12, lineHeight: 1.8, paddingLeft: 4 }}>
                          <span className="holo-text-red">▸</span> {s}
                        </div>
                      ))
                    ) : (
                      <span className="holo-text-dim" style={{ fontSize: 12 }}>—</span>
                    )}
                  </div>

                  <div className="holo-glass" style={{ padding: 14, borderRadius: 10, borderLeft: "3px solid var(--holo-cyan)" }}>
                    <div className="holo-text-cyan" style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                      <WarningOutlined /> 改进建议
                    </div>
                    {(r.analysis?.improvements || []).length > 0 ? (
                      (r.analysis?.improvements || []).map((s, i) => (
                        <div key={i} className="holo-text" style={{ fontSize: 12, lineHeight: 1.8, paddingLeft: 4 }}>
                          <span className="holo-text-cyan">▸</span> {s}
                        </div>
                      ))
                    ) : (
                      <span className="holo-text-dim" style={{ fontSize: 12 }}>—</span>
                    )}
                  </div>
                </div>

                {/* 推理错误 & 缺失数据 */}
                {(r.reasoning_layer?.reasoning_errors || []).length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <CosmicAlert
                      level="warning"
                      title="推理错误"
                      detail={(r.reasoning_layer?.reasoning_errors || []).join("； ")}
                    />
                  </div>
                )}

                {(r.reasoning_layer?.missing_data || []).length > 0 && (
                  <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span className="holo-text-dim" style={{ fontSize: 12 }}>缺失数据:</span>
                    {(r.reasoning_layer?.missing_data || []).map((d, i) => (
                      <HoloChip key={i} color="amber">{d}</HoloChip>
                    ))}
                  </div>
                )}

                {/* 新知识 */}
                {r.analysis?.new_knowledge && (
                  <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
                    <BulbOutlined style={{ color: "var(--holo-amber)" }} />
                    <span className="holo-text-bright" style={{ fontSize: 13, fontWeight: 600 }}>新知识:</span>
                    <HoloChip color="amber">{r.analysis.new_knowledge}</HoloChip>
                  </div>
                )}
              </GlassPanel>
            ))}
          </div>
        ) : (
          <GlassPanel corners style={{ textAlign: "center", padding: 60 }}>
            <Empty description={<span className="holo-text-dim">暂无反思报告，请先运行进化周期</span>} />
          </GlassPanel>
        )}
      </Spin>
    </div>
  );
}

// ================================================================
// Tab 4: 技能进化
// ================================================================

function SkillEvolutionTab() {
  const [proposals, setProposals] = useState<SkillMutationProposal[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evolutionService.skillProposals(50);
      setProposals(res.proposals || []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleApprove = async (proposalId: string) => {
    try {
      await evolutionService.approveProposal(proposalId);
      message.success("提案已审批通过");
      loadData();
    } catch {
      message.error("审批失败");
    }
  };

  const mutColor = (v: string): "cyan" | "green" | "amber" | "purple" => {
    const m: Record<string, "cyan" | "green" | "amber" | "purple"> = {
      prompt_refinement: "cyan",
      model_upgrade: "cyan",
      feature_addition: "green",
      strategy_adjustment: "amber",
    };
    return m[v] || "purple";
  };

  const statusColor = (v: string): "cyan" | "green" | "amber" | "red" => {
    const m: Record<string, "cyan" | "green" | "amber" | "red"> = {
      proposed: "cyan",
      testing: "cyan",
      sandbox: "amber",
      approved: "green",
      deployed: "green",
      rejected: "red",
    };
    return m[v] || "cyan";
  };

  const proposalColumns: ColumnsType<SkillMutationProposal> = [
    {
      title: "技能 ID",
      dataIndex: "skill_id",
      key: "skill_id",
      width: 140,
      render: (v: string) => <HoloChip color="purple">{v}</HoloChip>,
    },
    {
      title: "变异类型",
      dataIndex: "mutation_type",
      key: "mutation_type",
      width: 120,
      render: (v: string) => <HoloChip color={mutColor(v)}>{v}</HoloChip>,
    },
    {
      title: "当前版本",
      dataIndex: "current_version",
      key: "current_version",
      width: 90,
      render: (v: string) => <span className="holo-text-dim" style={{ fontFamily: "monospace" }}>{v}</span>,
    },
    {
      title: "目标版本",
      dataIndex: "proposed_version",
      key: "proposed_version",
      width: 90,
      render: (v: string) => <span className="holo-text-cyan" style={{ fontFamily: "monospace" }}>{v}</span>,
    },
    { title: "原因", dataIndex: "mutation_reason", key: "mutation_reason", ellipsis: true },
    {
      title: "审批分",
      dataIndex: "approval_score",
      key: "approval_score",
      width: 80,
      render: (v: number) => <HoloChip color={v >= 0.8 ? "green" : v >= 0.6 ? "amber" : "red"}>{(v * 100).toFixed(0)}</HoloChip>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => <HoloChip color={statusColor(v)}>{v}</HoloChip>,
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_: unknown, record: SkillMutationProposal) =>
        record.status === "proposed" ? (
          <button
            type="button"
            className="holo-btn holo-btn-ghost"
            style={{ padding: "4px 12px", fontSize: 12 }}
            onClick={() => handleApprove(record.proposal_id)}
          >
            审批
          </button>
        ) : (
          <span className="holo-text-dim" style={{ fontSize: 12 }}>—</span>
        ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <HoloButton variant="ghost" icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</HoloButton>
        <span className="holo-text-dim" style={{ fontSize: 13 }}>技能变异提案 ({proposals.length})</span>
      </div>

      <GlassPanel corners scanline className="holo-anim-fade-in" style={{ overflow: "hidden" }}>
        <Table
          columns={proposalColumns}
          dataSource={proposals}
          rowKey="proposal_id"
          loading={loading}
          size="small"
          scroll={{ x: 700 }}
          pagination={{ pageSize: 8, size: "small" }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <HoloDetailRow label="变更内容" value={record.changes?.join("； ") || "—"} accent="var(--holo-cyan)" />
                <HoloDetailRow label="新增能力" value={record.added_capabilities?.join("； ") || "—"} accent="var(--holo-green)" />
                {record.test_result && Object.keys(record.test_result).length > 0 && (
                  <div className="holo-glass" style={{ padding: 10, borderRadius: 8 }}>
                    <span className="holo-text-dim" style={{ fontSize: 12 }}>测试结果: </span>
                    <pre style={{ margin: "4px 0 0", fontSize: 12, color: "var(--holo-text)" }}>{JSON.stringify(record.test_result, null, 2)}</pre>
                  </div>
                )}
                {record.sandbox_result && Object.keys(record.sandbox_result).length > 0 && (
                  <div className="holo-glass" style={{ padding: 10, borderRadius: 8 }}>
                    <span className="holo-text-dim" style={{ fontSize: 12 }}>沙箱结果: </span>
                    <pre style={{ margin: "4px 0 0", fontSize: 12, color: "var(--holo-text)" }}>{JSON.stringify(record.sandbox_result, null, 2)}</pre>
                  </div>
                )}
              </div>
            ),
          }}
        />
      </GlassPanel>
    </div>
  );
}

// ================================================================
// Tab 5: 进化时间线
// ================================================================

function TimelineTab() {
  const [entries, setEntries] = useState<EvolutionTimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evolutionService.timeline(50);
      setEntries(res.entries || []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const colorMap: Record<string, string> = {
    experience: "var(--holo-amber)",
    reflection: "var(--holo-cyan)",
    skill_evolution: "var(--holo-purple)",
    milestone: "var(--holo-amber)",
    insight: "var(--holo-green)",
    cycle: "var(--holo-cyan)",
  };

  const chipColor = (t: string): "amber" | "cyan" | "purple" | "green" => {
    const m: Record<string, "amber" | "cyan" | "purple" | "green"> = {
      experience: "amber",
      reflection: "cyan",
      skill_evolution: "purple",
      milestone: "amber",
      insight: "green",
      cycle: "cyan",
    };
    return m[t] || "cyan";
  };

  const iconMap: Record<string, React.ReactNode> = {
    experience: <BulbOutlined />,
    reflection: <SyncOutlined />,
    skill_evolution: <ThunderboltOutlined />,
    milestone: <StarOutlined />,
    insight: <CheckCircleOutlined />,
    cycle: <RocketOutlined />,
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <HoloButton variant="ghost" icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</HoloButton>
        <span className="holo-text-dim" style={{ fontSize: 13 }}>进化事件时间线 ({entries.length})</span>
      </div>

      <Spin spinning={loading}>
        {entries.length > 0 ? (
          <GlassPanel corners scanline className="holo-anim-fade-in">
            <Timeline
              mode="left"
              items={entries.map((e) => ({
                color: colorMap[e.event_type] || "gray",
                dot: (
                  <span style={{ color: colorMap[e.event_type] || "var(--holo-text-dim)", filter: `drop-shadow(0 0 6px ${colorMap[e.event_type] || "transparent"})` }}>
                    {iconMap[e.event_type] || <ClockCircleOutlined />}
                  </span>
                ),
                label: <span className="holo-text-dim" style={{ fontSize: 12 }}>{e.timestamp}</span>,
                children: (
                  <div
                    className="holo-glass holo-glass-hover"
                    style={{ padding: 14, borderRadius: 10, borderLeft: `3px solid ${colorMap[e.event_type] || "var(--holo-glass-border)"}` }}
                  >
                    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
                      <HoloChip color={chipColor(e.event_type)}>{e.event_type}</HoloChip>
                      {e.agent_id && <span className="holo-text-dim" style={{ fontFamily: "monospace", fontSize: 12 }}>{e.agent_id}</span>}
                      {e.impact_level && (
                        <HoloChip color={e.impact_level === "high" ? "red" : e.impact_level === "medium" ? "amber" : "green"}>
                          影响: {e.impact_level}
                        </HoloChip>
                      )}
                    </div>
                    <div className="holo-text-bright" style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
                      {e.title}
                    </div>
                    <div className="holo-text-dim" style={{ fontSize: 13, lineHeight: 1.6 }}>
                      {e.description}
                    </div>
                  </div>
                ),
              }))}
            />
          </GlassPanel>
        ) : (
          <GlassPanel corners style={{ textAlign: "center", padding: 60 }}>
            <Empty description={<span className="holo-text-dim">暂无进化事件，请先运行进化周期</span>} />
          </GlassPanel>
        )}
      </Spin>
    </div>
  );
}

// ================================================================
// 主页面
// ================================================================

export default function EvolutionEngine() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboard, setDashboard] = useState<EvolutionDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const data = await evolutionService.dashboard();
      setDashboard(data);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleRunCycle = async () => {
    setRunning(true);
    try {
      // /evolution 为演示页；runCycle 是桩，不产生真实进化结果。
      // 不再用 result.summary（该字段不存在）谎报“执行完成”。
      await evolutionService.runCycle();
      // 演示页动作不真实写入，用 info（中性通知）而非 success（绿色对勾会夸大"成功"）。
      message.info("进化周期已触发 · 演示模式");
      loadDashboard();
    } catch {
      message.error("进化周期触发失败");
    } finally {
      setRunning(false);
    }
  };

  const handleSeedDemo = async () => {
    setRunning(true);
    try {
      const result = await evolutionService.seedDemo();
      // result.seeded 是桩返回的样本数（演示页不真实写入）；
      // 如实展示，不谎报"已植入"；用 info 而非 success 避免夸大"成功"。
      message.info(`演示数据种子已生成 · 演示模式（样本 ${result.seeded} 条）`);
      loadDashboard();
    } catch {
      message.error("演示数据种子生成失败");
    } finally {
      setRunning(false);
    }
  };

  const tabItems = [
    {
      key: "dashboard",
      label: <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><RocketOutlined /> 进化总览</span>,
      children: (
        <DashboardTab
          dashboard={dashboard}
          loading={loading}
          onRunCycle={handleRunCycle}
          onSeedDemo={handleSeedDemo}
          running={running}
        />
      ),
    },
    {
      key: "experience",
      label: <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><BulbOutlined /> 经验挖掘</span>,
      children: <ExperienceTab />,
    },
    {
      key: "reflection",
      label: <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><SyncOutlined /> 反思引擎</span>,
      children: <ReflectionTab />,
    },
    {
      key: "skill",
      label: <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><ThunderboltOutlined /> 技能进化</span>,
      children: <SkillEvolutionTab />,
    },
    {
      key: "timeline",
      label: <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><ClockCircleOutlined /> 进化时间线</span>,
      children: <TimelineTab />,
    },
  ];

  return (
    <div style={{ position: "relative", zIndex: 2 }}>
      <DemoBadge level="L3" visible />
      {/* 页面标题 */}
      <h2 className="holo-section-title holo-anim-fade-in" style={{ fontSize: 22 }}>
        <RocketOutlined style={{ color: "var(--holo-cyan)", filter: "drop-shadow(0 0 8px var(--holo-cyan-glow))" }} />
        Agent 进化引擎
        <span className="holo-text-dim" style={{ fontSize: 13, fontWeight: 400, marginLeft: 8 }}>
          Experience → Knowledge → Skill → Intelligence
        </span>
      </h2>

      {/* 数据流装饰 */}
      <DataStream lines={3} height={36} color="var(--holo-cyan)" />

      {/* Tabs 容器 */}
      <GlassPanel className="holo-anim-fade-in" style={{ marginTop: 12 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{ color: "var(--holo-text)" }}
        />
      </GlassPanel>
    </div>
  );
}
