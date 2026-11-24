import { defineConfig } from "@playwright/test";

// Uses the installed Chrome; no browser download. The server seeds a stub project in /tmp/mb-e2e.
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 90_000,
  workers: 1,
  fullyParallel: false,
  use: { baseURL: "http://127.0.0.1:4399", channel: "chrome", headless: true, viewport: { width: 1440, height: 900 } },
  webServer: {
    command: "bash tests/e2e/serve.sh",
    url: "http://127.0.0.1:4399/api/projects",
    timeout: 180_000,
    reuseExistingServer: false,
    stdout: "ignore",
    stderr: "pipe",
  },
});
