/**
 * CockpitView — 3D 数字孪生驾驶舱（内嵌）
 *
 * 将 carModel 根目录 `frontend/cockpit/index.html`（Three.js 3D 车辆可视化 +
 * SOH 仪表 + AI 问答）以 iframe 方式嵌入 Guardian 主域。
 *
 * 数据链路（全程同源、no CORS、免登录）：
 *   iframe src = /cockpit/?apiBase=/api/carsoul/proxy
 *   - /cockpit/* 经 serve-frontend 反向代理到 :8000（carModel StaticFiles）
 *   - cockpit 内 fetch(API+path) 走 /api/carsoul/proxy/...，再由
 *     serve-frontend 代理到 :8001（Guardian 透传端点，白名单 + 鉴权豁免 +
 *     带服务令牌转发 :8000）
 *
 * 注意：守卫服务（5173）由 scripts/serve-frontend.mjs 托管 dist 静态 + 反向代理
 * 等价于 vite dev+proxy。本地 dev 与 nginx prod 已天然覆盖，无需额外配置。
 */
import { useState } from "react";
import { Alert, Button, Spin } from "antd";
import { ReloadOutlined } from "@ant-design/icons";

/** 内嵌地址：同源取 cockpit HTML，API 基址指向 Guardian 透传端点。 */
const COCKPIT_SRC = "/cockpit/?apiBase=/api/carsoul/proxy";

export default function CockpitView() {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [frameKey, setFrameKey] = useState(0);

  return (
    <div className="cockpit-embed">
      {failed ? (
        <div className="cockpit-embed__error">
          <Alert
            type="error"
            showIcon
            message="3D 数字孪生驾驶舱加载失败"
            description="请确认 carModel 预测引擎已在 :8000 启动（bash start.sh），且 /cockpit 静态托管可达；刷新 Guardian 后重试。"
            action={
              <Button size="small" icon={<ReloadOutlined />} onClick={() => { setFailed(false); setLoaded(false); setFrameKey((k) => k + 1); }}>
                重试
              </Button>
            }
          />
        </div>
      ) : (
        <>
          {!loaded && (
            <div className="cockpit-embed__loading">
              <Spin tip="正在加载 3D 数字孪生驾驶舱…">
                <div style={{ height: 120 }} />
              </Spin>
            </div>
          )}
          <iframe
            key={frameKey}
            src={COCKPIT_SRC}
            title="3D 数字孪生驾驶舱"
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            className="cockpit-embed__frame"
            style={{ display: loaded ? "block" : "none" }}
            allowFullScreen
          />
        </>
      )}
    </div>
  );
}
