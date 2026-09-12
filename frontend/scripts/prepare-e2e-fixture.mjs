import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(frontendRoot, "..");
const variableDirectory = resolve(repositoryRoot, "var");
await mkdir(variableDirectory, { recursive: true });
await copyFile(
  resolve(repositoryRoot, "tests/fixtures/browser-catalogue-dataset.json"),
  resolve(variableDirectory, "catalogue-dataset.json"),
);
