/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Disable preflight so Tailwind's CSS reset does not fight Ant Design.
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        // CarSoul Guardian brand palette
        brand: {
          50: "#eef6ff",
          100: "#d9eaff",
          200: "#bcd9ff",
          300: "#8ec1ff",
          400: "#599dff",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        guardian: {
          green: "#10b981",
          amber: "#f59e0b",
          red: "#ef4444",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
