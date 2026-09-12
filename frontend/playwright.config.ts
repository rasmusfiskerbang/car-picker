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
      "pnpm --dir frontend prepare-e2e-fixture && .venv/bin/python -m car_picker --workspace . site build && exec .venv/bin/python -m car_picker --workspace . site serve --port 4173",
    cwd: "..",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
