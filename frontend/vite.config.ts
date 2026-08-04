import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import {
  tanStackRouterCodeSplitter,
  tanstackRouterGenerator,
} from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  plugins: [
    tanstackRouterGenerator({
      target: "react",
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routeTree.gen.ts",
    }),
    tanStackRouterCodeSplitter({ target: "react" }),
    react(),
    tailwindcss(),
  ],
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
