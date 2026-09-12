import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, "..", "..");
const virtualEnvironmentPython = join(repositoryRoot, ".venv", "bin", "python");
const python =
  process.env.CAR_PICKER_PYTHON ??
  (existsSync(virtualEnvironmentPython) ? virtualEnvironmentPython : "python3");
const result = spawnSync(
  python,
  [
    "-c",
    "from car_picker.publication import generate_catalogue_contract_sources; generate_catalogue_contract_sources()",
  ],
  { cwd: repositoryRoot, stdio: "inherit" },
);

if (result.error) {
  console.error(
    `Could not generate the Catalogue Dataset contract: ${result.error.message}`,
  );
  process.exit(1);
}
process.exit(result.status ?? 1);
