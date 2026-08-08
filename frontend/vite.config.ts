import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

/**
 * Vite 生产构建时兜底解析两类 import：
 * 1. 目录级 import（如 `@/components/hologram`）→ 找目录下 index.ts/index.tsx
 * 2. 无扩展名文件 import（如 `@/layouts/index`）→ 补 .ts/.tsx
 * 开发服务器能自动处理，但 Rollup 生产构建偶发 ENOENT/EISDIR，用此插件兜底。
 */
function directoryIndexResolver() {
  return {
    name: "directory-index-resolver",
    enforce: "pre" as const,
    async resolveId(source: string, importer: string | undefined) {
      if (!source.startsWith("@/")) return null;
      const resolved = path.resolve(__dirname, "./src", source.slice(2));
      let isDirectory = false;
      try {
        const stat = await fs.promises.stat(resolved);
        isDirectory = stat.isDirectory();
      } catch {
        // 可能是无扩展名文件 import，继续走下方兜底
      }

      if (isDirectory) {
        for (const ext of ["index.ts", "index.tsx"]) {
          const candidate = path.join(resolved, ext);
          if (fs.existsSync(candidate)) {
            return candidate;
          }
        }
      }

      // 兜底：无扩展名文件 import 补 .ts/.tsx
      for (const ext of [".ts", ".tsx"]) {
        const candidate = resolved + ext;
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      }

      return null;
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), directoryIndexResolver()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Proxy API calls to the FastAPI backend during dev.
      // NOTE: CarSoul World Model (carModel) already occupies :8000 as the
      // prediction engine, so the Guardian backend runs on :8001 to avoid the
      // clash. Keep these two targets in sync with the backend's --port.
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      // Guardian's own health (backend liveness) stays on :8001.
      "/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      // --- carModel (world model engine) surfaces, proxied straight to :8000 ---
      // /docs  -> carModel's Swagger UI
      // /cockpit -> carModel's 3D digital-twin view (the canonical "world model")
      "/docs": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/cockpit": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
