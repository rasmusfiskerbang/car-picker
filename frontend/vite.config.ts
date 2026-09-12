import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const publicDir = process.env.CAR_PICKER_DEV_PUBLIC_DIR ?? "public";

export default defineConfig({
  base: "./",
  plugins: [react()],
  publicDir,
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: {
    outDir: process.env.CAR_PICKER_SITE_OUTPUT ?? "dist",
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        assetFileNames: "styles.css",
      },
    },
  },
});
