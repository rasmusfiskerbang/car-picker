import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/python -m car_picker serve-site --site ../var/site --port 4173",
    cwd: ".",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
