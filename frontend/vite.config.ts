import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI dev server so the browser stays same-origin.
// The target honors BACKEND_PORT so `BACKEND_PORT=8123 poker-trainer` works;
// strictPort keeps vite from silently drifting to :5174 when :5173 is busy
// (scripts/serve.sh reports the port it *asked* for).
const backendPort = process.env.BACKEND_PORT ?? "8008";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": `http://localhost:${backendPort}`,
    },
  },
});
