import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider, theme as antdTheme } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        // 2026-08-12：CarSoul 设计系统规范（CS-UI-DS v1.0）落地
        // 精密克制座舱感 · 灵魂绿主强调 · 禁用霓虹发光
        algorithm: antdTheme.darkAlgorithm,
        token: {
          colorPrimary: "#2dd4bf", // 灵魂绿 soul-400
          colorInfo: "#3b82f6", // 电光蓝 info-500
          colorSuccess: "#14b8a6", // 灵魂绿 soul-500
          colorWarning: "#f59e0b", // 琥珀 warn-500
          colorError: "#ef4444", // 危险红 danger-500
          colorLink: "#2dd4bf",
          colorBgBase: "#07090f", // ink-950
          colorBgLayout: "#0b0f17", // ink-900
          colorBgContainer: "#0f141f", // ink-850
          colorBgElevated: "#141b29", // ink-800
          colorBorder: "rgba(255,255,255,0.07)", // --line
          colorBorderSecondary: "rgba(255,255,255,0.07)",
          colorText: "#eef2f8", // text-100
          colorTextSecondary: "#c3ccda", // text-200
          borderRadius: 10, // --r-md
          fontFamily:
            '"IBM Plex Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
          fontSize: 14,
          controlHeight: 38,
          controlHeightLG: 44,
          controlHeightSM: 34,
          lineHeight: 1.6,
        },
        components: {
          Menu: {
            itemHeight: 46,
            itemMarginInline: 6,
            iconSize: 18,
            itemSelectedBg: "rgba(45,212,191,0.12)",
            itemSelectedColor: "#2dd4bf",
            itemHoverBg: "rgba(255,255,255,0.06)",
            itemColor: "#8b97a8",
            itemActiveBg: "rgba(255,255,255,0.06)",
          },
          Button: {
            controlHeight: 38,
            controlHeightLG: 44,
            controlHeightSM: 34,
            paddingInline: 18,
            paddingInlineLG: 22,
            primaryShadow: "none", // 移除霓虹发光
          },
          Table: {
            cellPaddingBlock: 14,
            cellPaddingInline: 14,
            headerBg: "rgba(45,212,191,0.06)",
            headerColor: "#eef2f8",
            headerSplitColor: "transparent",
            borderColor: "rgba(255,255,255,0.07)",
            rowHoverBg: "rgba(45,212,191,0.05)",
            colorBgContainer: "rgba(255,255,255,0.03)",
          },
          Tabs: {
            horizontalItemPadding: "14px 20px",
            titleFontSize: 16,
          },
          Input: {
            controlHeight: 38,
            paddingInline: 12,
          },
          Card: {
            colorBgContainer: "#0f141f",
          },
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
);
