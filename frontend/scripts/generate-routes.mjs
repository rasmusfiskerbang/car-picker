import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptDirectory, "..");
const manifestPath = resolve(frontendRoot, "src/route-manifest.json");
const outputPath = resolve(frontendRoot, "src/generated/route-output.ts");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const orderedRoutes = Object.fromEntries(
  Object.entries(manifest).sort(([left], [right]) => left.localeCompare(right)),
);

const output = [
  "/* Generated from src/route-manifest.json. Do not edit. */",
  `export const routePaths = ${JSON.stringify(orderedRoutes, null, 2)} as const;`,
  "",
].join("\n");
await writeFile(outputPath, output, "utf8");
