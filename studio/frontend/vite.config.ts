import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8765";

// The production build is served by the FastAPI app; the dev server proxies the API to it.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": { target: backend, changeOrigin: true, headers: { Origin: backend } } },
  },
});
