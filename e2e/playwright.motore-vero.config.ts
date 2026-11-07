import { defineConfig, devices } from "@playwright/test";

// Prova di aggancio con il motore VERO (scripts/prova-motore-vero.sh): lenta (minuti per documento),
// per questo separata dalle prove normali (playwright.config.ts, finto motore).
export default defineConfig({
  testDir: "./motore-vero",
  timeout: 60 * 60_000,
  expect: { timeout: 30_000 },
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  outputDir: "/tmp/risultati-e2e-motore-vero",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:5173",
    locale: "it-IT",
    trace: "off",
    screenshot: "off",
  },
});
