import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI dev server so the browser stays same-origin.
// The target honors BACKEND_PORT so `BACKEND_PORT=8123 poker-coach` works;
// strictPort keeps vite from silently drifting to :7778 when :7777 is busy
// (scripts/serve.sh reports the port it *asked* for).
// 7777 (not vite's default 5173) so this app never fights dbt-trainer for the port.
const backendPort = process.env.BACKEND_PORT ?? "8008";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7777,
    strictPort: true,
    proxy: {
      "/api": `http://localhost:${backendPort}`,
    },
  },
  // vite preview does not inherit server.proxy — mirror it so a built bundle
  // can be exercised against the real backend (used for design verification).
  preview: {
    port: 5301,
    strictPort: true,
    proxy: {
      "/api": `http://localhost:${backendPort}`,
    },
  },
});
