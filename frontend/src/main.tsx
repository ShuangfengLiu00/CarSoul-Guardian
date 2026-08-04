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
        algorithm: antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: "#3b82f6",
          borderRadius: 12,
          fontFamily:
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
          // 触摸 / 大屏适配：放大控件与字号
          fontSize: 15,
          controlHeight: 40,
          controlHeightLG: 48,
          controlHeightSM: 36,
          lineHeight: 1.6,
        },
        components: {
          Menu: {
            itemHeight: 48,
            itemMarginInline: 8,
            iconSize: 18,
          },
          Button: {
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 36,
            paddingInline: 18,
            paddingInlineLG: 24,
          },
          Table: {
            cellPaddingBlock: 14,
            cellPaddingInline: 14,
            headerBg: "#f8fafc",
          },
          Tabs: {
            horizontalItemPadding: "14px 20px",
            titleFontSize: 16,
          },
          Input: {
            controlHeight: 40,
            paddingInline: 12,
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
