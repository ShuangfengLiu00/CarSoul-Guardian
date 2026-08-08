const fs = require("fs");
const path = require("path");

const SRC = path.resolve(__dirname, "src");
const exts = [".ts", ".tsx"];

const dirs = [
  "components/three",
  "components/hologram",
  "pages/hologram",
  "services",
  "stores",
  "hooks",
  "layouts",
  "components",
  "pages",
];

// 解析一个文件导出的具名标识符
function namedExportsOf(content) {
  const names = new Set();
  const re1 = /export\s+(?:const|let|var|function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)/g;
  let m;
  while ((m = re1.exec(content))) names.add(m[1]);
  const re2 = /export\s*\{([^}]*)\}/g;
  while ((m = re2.exec(content))) {
    for (let part of m[1].split(",")) {
      part = part.trim();
      if (!part) continue;
      const asMatch = part.match(/as\s+([A-Za-z_$][\w$]*)\s*$/);
      if (asMatch) names.add(asMatch[1]);
      else names.add(part.split(/\s/)[0]);
    }
  }
  return names;
}

function genBarrel(relDir) {
  const dir = path.join(SRC, relDir);
  if (!fs.existsSync(dir)) { console.log("跳过(不存在): " + relDir); return; }
  const idxFile = path.join(dir, "index.ts");
  const lines = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === "index.ts" || e.name === "index.tsx") continue;
    if (e.isDirectory()) {
      lines.push(`export * from "./${e.name}";`);
    } else if (exts.includes(path.extname(e.name))) {
      const base = e.name.replace(/\.(ts|tsx)$/, "");
      const content = fs.readFileSync(path.join(dir, e.name), "utf8");
      const hasDefault = /export\s+default\b/.test(content);
      const named = namedExportsOf(content);
      lines.push(`export * from "./${base}";`);
      if (hasDefault && !named.has(base)) {
        lines.push(`export { default as ${base} } from "./${base}";`);
      }
    }
  }
  if (lines.length === 0) { console.log("空目录跳过: " + relDir); return; }
  fs.writeFileSync(idxFile, lines.join("\n") + "\n", "utf8");
  console.log(`生成 ${relDir}/index.ts (${lines.length} 条)`);
}

for (const d of dirs) genBarrel(d);
console.log("=== barrel 生成完成 ===");
