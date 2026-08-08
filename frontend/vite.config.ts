import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

/**
 * Vite 生产构建时，对形如 `@/components/hologram` 的目录级 import，
 * 如果该目录下存在 index.ts/index.tsx，则显式解析到 index 文件。
 * 开发服务器能自动处理，但 Rollup 生产构建偶发 EISDIR 报错，用此插件兜底。
 */
function directoryIndexResolver() {
  return {
    name: "directory-index-resolver",
    enforce: "pre" as const,
    async resolveId(source: string, importer: string | undefined) {
      if (!source.startsWith("@/")) return null;
      const resolved = path.resolve(__dirname, "./src", source.slice(2));
      try {
        const stat = await fs.promises.stat(resolved);
        if (!stat.isDirectory()) return null;
        for (const ext of ["index.ts", "index.tsx"]) {
          const candidate = path.join(resolved, ext);
          if (fs.existsSync(candidate)) {
            return candidate;
          }
        }
      } catch {
        // 不是目录或不存在，交给默认解析器
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
      "/health": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
