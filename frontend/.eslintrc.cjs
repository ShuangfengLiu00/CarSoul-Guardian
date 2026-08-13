module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  ignorePatterns: ["dist", ".eslintrc.cjs", "node_modules"],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],

    // ── SPEC C-16: icon library locked to `lucide-react` ──────────────
    // Ban competing icon libraries outright. `@ant-design/icons` is legacy
    // (paired with `antd` in un-migrated components); NEW code MUST use
    // Lucide via `@/lib/icons`. The emoji half of C-17 is enforced by
    // `scripts/check-emoji.cjs` (wired into `npm run lint`), since ESLint
    // cannot regex-scan source text for emoji directly.
    "no-restricted-imports": [
      "error",
      {
        paths: [
          {
            name: "@heroicons/react",
            message: "SPEC C-16: use lucide-react (see @/lib/icons).",
          },
          {
            name: "@fortawesome/react-fontawesome",
            message: "SPEC C-16: use lucide-react (see @/lib/icons).",
          },
          {
            name: "@fortawesome/free-solid-svg-icons",
            message: "SPEC C-16: use lucide-react (see @/lib/icons).",
          },
          {
            name: "react-icons",
            message: "SPEC C-16: use lucide-react (see @/lib/icons).",
          },
        ],
        patterns: [
          {
            group: ["@heroicons/*", "@fortawesome/*", "react-icons/*"],
            message: "SPEC C-16: use lucide-react (see @/lib/icons).",
          },
        ],
      },
    ],
  },
};

