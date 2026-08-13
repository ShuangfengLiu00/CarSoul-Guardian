#!/usr/bin/env node
/**
 * check-emoji.cjs — Enforce SPEC C-17 (no emoji as functional icons).
 *
 * Scans the frontend src tree (.ts/.tsx/.jsx/.js) for emoji characters and
 * fails (exit code 1) if any are found. Wired into `npm run lint` so emoji
 * can never sneak back in.
 *
 * Detection covers the C-17 Unicode ranges:
 *   U+1F000–U+1F02F, U+1F0A0–U+1F0FF, U+1F100–U+1F64F,
 *   U+1F680–U+1F6FF, U+1F900–U+1F9FF, U+1FA00–U+1FA6F, U+1FA70–U+1FAFF,
 *   U+1F300–U+1F5FF, U+2600–U+26FF, U+2700–U+27BF, U+FE00–U+FE0F.
 *
 * Escape hatch: append `// allow-emoji` to a line that legitimately needs an
 * emoji in user-facing content (e.g. echoing a user message). Functional UI
 * icons must use Lucide (see src/lib/icons.ts).
 *
 * Usage:  node scripts/check-emoji.cjs [scan-root]
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", "src"));

// C-17 emoji ranges (inclusive).
const EMOJI_REGEX =
  /[\u{1F000}-\u{1F02F}\u{1F0A0}-\u{1F0FF}\u{1F100}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{1F300}-\u{1F5FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}]/gu;

const EXT_RE = /\.(ts|tsx|jsx|js)$/;

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (EXT_RE.test(entry.name)) out.push(full);
  }
  return out;
}

if (!fs.existsSync(ROOT)) {
  console.error(`[check-emoji] scan root not found: ${ROOT}`);
  process.exit(2);
}

const files = walk(ROOT);
let total = 0;
const hits = [];

for (const file of files) {
  const content = fs.readFileSync(file, "utf8");
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Escape hatch: a line tagged `// allow-emoji` may carry user-content emoji.
    if (/\ballow-emoji\b/.test(line)) continue;
    const matches = line.match(EMOJI_REGEX);
    if (matches) {
      total += matches.length;
      const rel = path.relative(process.cwd(), file);
      hits.push(`  ${rel}:${i + 1}  ${line.trim().slice(0, 100)}`);
    }
  }
}

if (total === 0) {
  console.log(`[check-emoji] OK — 0 emoji in ${files.length} files under ${path.relative(process.cwd(), ROOT) || ROOT}`);
  process.exit(0);
}

console.error(`[check-emoji] FAIL — found ${total} emoji character(s):`);
for (const h of hits) console.error(h);
console.error(
  "\nEmoji as functional UI icons violates SPEC C-17. Replace with Lucide icons"
);
console.error("(see src/lib/icons.ts). If a line genuinely needs emoji in");
console.error("user-facing content, append `// allow-emoji` to that line.");
process.exit(1);
