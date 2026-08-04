/**
 * CriticalAlertOverlay — 霸屏红色闪烁警示
 *
 * 当存在 critical 级别活跃告警时，全屏覆盖红色脉冲闪烁警示层，
 * 用于平板/触摸大屏演示场景下强力吸睛、警示用户"有问题"。
 *
 * - 红色背景脉冲闪烁动画（cs-alert-flash）
- 大号警示标题 + 告警详情滚动
 * - 触摸友好大按钮：立即查看 / 我知道了
 * - 关闭后记录该告警 id，不重复弹出（直至新 critical 告警出现）
 */
import { useEffect, useMemo, useState, useCallback } from "react";
import { Button, Space, Typography } from "antd";
import {
  AlertOutlined,
  BellOutlined,
  ExclamationCircleFilled,
  CheckCircleOutlined,
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

export interface CriticalAlert {
  id?: number | string;
  level: "critical" | "warning" | "info";
  title: string;
  detail?: string;
  recommendation?: string;
  triggered_at?: string;
  category?: string;
}

interface Props {
  alerts: CriticalAlert[];
  onView?: (a: CriticalAlert) => void;
}

export default function CriticalAlertOverlay({ alerts, onView }: Props) {
  // 当前展示的告警（取第一条 critical），以及已被用户关闭的 id 集合
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [currentIndex, setCurrentIndex] = useState(0);

  // 仅 critical 级别
  const criticalAlerts = useMemo(
    () => alerts.filter((a) => a.level === "critical"),
    [alerts],
  );

  // 未被关闭的 critical 告警
  const visibleAlerts = useMemo(
    () =>
      criticalAlerts.filter((a) => {
        const key = a.id != null ? String(a.id) : a.title;
        return !dismissed.has(key);
      }),
    [criticalAlerts, dismissed],
  );

  // 新 critical 告警出现时重置索引
  useEffect(() => {
    setCurrentIndex(0);
  }, [visibleAlerts.length]);

  const current = visibleAlerts[currentIndex];

  const handleDismiss = useCallback(() => {
    if (!current) return;
    const key = current.id != null ? String(current.id) : current.title;
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });
  }, [current]);

  const handleNext = useCallback(() => {
    if (onView && current) onView(current);
    setCurrentIndex((i) => i + 1);
  }, [onView, current]);

  // 震动反馈（移动端/平板，若支持）
  useEffect(() => {
    if (current && "vibrate" in navigator) {
      try {
        (navigator as Navigator & { vibrate: (p: number | number[]) => boolean }).vibrate([
          200, 100, 200, 100, 400,
        ]);
      } catch {
        /* ignore */
      }
    }
  }, [current]);

  if (!current) return null;

  const remaining = visibleAlerts.length - currentIndex;

  return (
    <div className="cs-critical-overlay" role="alertdialog" aria-modal="true" aria-live="assertive">
      {/* 闪烁红色背景层 */}
      <div className="cs-critical-overlay__flash" aria-hidden="true" />

      {/* 扫描线效果 */}
      <div className="cs-critical-overlay__scan" aria-hidden="true" />

      <div className="cs-critical-overlay__content">
        {/* 顶部状态条 */}
        <div className="cs-critical-overlay__topbar">
          <Space size={12}>
            <ExclamationCircleFilled className="cs-critical-overlay__icon" />
            <Text style={{ color: "#fff", fontSize: 18, fontWeight: 700, letterSpacing: "0.1em" }}>
              紧急告警 · CRITICAL ALERT
            </Text>
          </Space>
          <Space size={8}>
            <BellOutlined className="cs-critical-overlay__bell" />
            <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 13 }}>
              {new Date().toLocaleTimeString("zh-CN")}
            </Text>
          </Space>
        </div>

        {/* 主体警示内容 */}
        <div className="cs-critical-overlay__main">
          <div className="cs-critical-overlay__badge">!</div>
          <Title level={1} className="cs-critical-overlay__title">
            {current.title}
          </Title>
          {current.category && (
            <div className="cs-critical-overlay__chip">{current.category}</div>
          )}
          {current.detail && (
            <Paragraph className="cs-critical-overlay__detail">{current.detail}</Paragraph>
          )}
          {current.recommendation && (
            <div className="cs-critical-overlay__reco">
              <CheckCircleOutlined style={{ marginRight: 8 }} />
              {current.recommendation}
            </div>
          )}
        </div>

        {/* 底部操作区 */}
        <div className="cs-critical-overlay__actions">
          <Button
            size="large"
            className="cs-critical-overlay__btn cs-critical-overlay__btn--ghost"
            onClick={handleDismiss}
          >
            我知道了
          </Button>
          <Button
            size="large"
            type="primary"
            danger
            className="cs-critical-overlay__btn cs-critical-overlay__btn--primary"
            onClick={handleNext}
          >
            立即查看详情
          </Button>
        </div>

        {/* 分页指示 */}
        {remaining > 1 && (
          <div className="cs-critical-overlay__pager">
            还有 {remaining - 1} 条紧急告警 →
          </div>
        )}
      </div>
    </div>
  );
}
