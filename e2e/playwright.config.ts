import { defineConfig, devices } from "@playwright/test";

// Contro lo stack compose (BASE_URL = il backoffice Vite, che inoltra /api all'API).
export default defineConfig({
  testDir: "./tests",
  timeout: 240_000,
  expect: { timeout: 20_000 },
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  outputDir: "/tmp/risultati-e2e",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:5173",
    locale: "it-IT",
    trace: "off",
    screenshot: "off",
  },
});
