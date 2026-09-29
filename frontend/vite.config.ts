import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the backend so the frontend code always calls
// relative /api/* URLs. Set BACKEND_URL if your backend runs elsewhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
