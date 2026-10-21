/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In sviluppo il browser parla solo con Vite e Vite inoltra /api al server FastAPI:
// stesso "sito" per il cookie di sessione (SameSite=Strict), nessun CORS.
const API = process.env.VITE_API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: API, changeOrigin: false } } },
  preview: { port: 5173, proxy: { "/api": { target: API, changeOrigin: false } } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    testTimeout: 40_000,
  },
});
