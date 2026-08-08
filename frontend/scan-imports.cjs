const fs = require("fs");
const path = require("path");

const SRC = path.resolve(__dirname, "src");
const exts = [".ts", ".tsx", ".js", ".jsx"];

// 收集 src 下所有文件，建立 "目录" 与 "文件(去扩展名)" 索引
function walk(dir, acc) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full, acc);
    else acc.push(full);
  }
  return acc;
}
const allFiles = walk(SRC, []);
const fileSet = new Set(allFiles);

// 判断一个 "模块路径" 是否能解析
function resolveMod(modPath) {
  // 已带扩展名
  if (exts.includes(path.extname(modPath))) {
    return fs.existsSync(modPath) ? "ok:" + modPath : "missing:" + modPath;
  }
  // 尝试加扩展名
  for (const ex of exts) {
    if (fs.existsSync(modPath + ex)) return "ok(file+ext):" + modPath + ex;
  }
  // 尝试 index
  for (const ex of exts) {
    if (fs.existsSync(path.join(modPath, "index" + ex)))
      return "ok(index):" + path.join(modPath, "index" + ex);
  }
  return "UNRESOLVABLE:" + modPath;
}

const importRe = /(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g;
let problemCount = 0;
const problems = [];

for (const f of allFiles) {
  if (!exts.includes(path.extname(f))) continue;
  const text = fs.readFileSync(f, "utf8");
  let m;
  while ((m = importRe.exec(text))) {
    const spec = m[1];
    if (!spec.startsWith("@/")) continue;
    const rel = spec.slice(2); // 去掉 @/
    const modPath = path.join(SRC, rel);
    const r = resolveMod(modPath);
    if (r.startsWith("UNRESOLVABLE") || r.startsWith("missing")) {
      problemCount++;
      problems.push({ file: path.relative(SRC, f), spec, resolved: r });
    }
  }
}

console.log("=== 无法解析的 @/ 导入共 " + problemCount + " 处 ===");
for (const p of problems) {
  console.log(`  [${p.file}]  ${p.spec}  ->  ${p.resolved}`);
}
if (problemCount === 0) console.log("  无问题，构建应可直接通过");
