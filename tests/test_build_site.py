from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from unittest.mock import patch

import car_picker
from car_picker import SiteBuildError, catalogue_dataset_json_schema
from tests.site_helpers import build_site, open_site, write_workspace_dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/browser-catalogue-dataset.json"


class BuildSiteTest(unittest.TestCase):
    def test_build_site_preserves_the_active_dataset_bytes_exactly(self) -> None:
        dataset_bytes = b"\n" + FIXTURE_DATASET.read_bytes() + b"\n"

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "active-dataset.json"
            site_path = temporary_path / "var/site"
            dataset_path.write_bytes(dataset_bytes)

            build_site(dataset_path, site_path)

            packaged_bytes = (site_path / "catalogue-dataset.json").read_bytes()

        self.assertEqual(packaged_bytes, dataset_bytes)

    def test_build_site_runs_the_contract_generator_once_before_compilation(
        self,
    ) -> None:
        commands: list[tuple[str, ...]] = []

        def run_frontend_command(
            command: list[str],
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            commands.append(tuple(command))
            if command == ["pnpm", "build"]:
                environment = kwargs["env"]
                environment = cast(Mapping[str, object], environment)
                staging_path = Path(str(environment["CAR_PICKER_SITE_OUTPUT"]))
                (staging_path / "index.html").write_text(
                    "<!doctype html>"
                    '<html lang="da"><head><title>Bilvalg</title></head>'
                    '<body><main id="root"></main>'
                    '<script type="module" src="./app.js"></script>'
                    '<link rel="stylesheet" href="./styles.css"></body></html>',
                    encoding="utf-8",
                )
                (staging_path / "app.js").write_text(
                    "console.log('compiled');", encoding="utf-8"
                )
                (staging_path / "styles.css").write_text("body {}", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "var/site"
            with patch("subprocess.run", side_effect=run_frontend_command):
                build_site(FIXTURE_DATASET, site_path)

        self.assertEqual(
            commands,
            [
                ("pnpm", "generate-contract"),
                ("pnpm", "generate-routes"),
                ("pnpm", "build"),
            ],
        )

    def test_open_site_validates_its_packaged_dataset_without_a_newer_dataset(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            site_path = temporary_path / "var/site"
            active_dataset_path = temporary_path / "var/catalogue-dataset.json"
            active_dataset_path.parent.mkdir(parents=True)
            active_dataset_path.write_bytes(FIXTURE_DATASET.read_bytes())
            build_site(active_dataset_path, site_path)

            newer_dataset = copy.deepcopy(
                json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
            )
            newer_dataset["generatedAt"] = "2099-01-01T00:00:00Z"
            active_dataset_path.write_text(json.dumps(newer_dataset), encoding="utf-8")

            opened = open_site(site_path)

        self.assertEqual(opened.generated_at, "2026-07-31T10:00:00Z")

    def test_open_site_rejects_an_incomplete_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "var/site"
            build_site(FIXTURE_DATASET, site_path)
            (site_path / "styles.css").unlink()

            with self.assertRaises(ValueError):
                open_site(site_path)

    def test_open_site_rejects_a_nonempty_corrupt_compiled_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "var/site"
            build_site(FIXTURE_DATASET, site_path)
            (site_path / "app.js").write_bytes(b"corrupt but non-empty")

            with self.assertRaisesRegex(ValueError, "integrity"):
                open_site(site_path)

    def test_failed_staged_verification_preserves_the_prior_site(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "var/site"
            build_site(FIXTURE_DATASET, site_path)
            initial_site = {
                path.name: path.read_bytes() for path in site_path.iterdir()
            }

            def run_frontend_command(
                command: list[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[str]:
                if command == ["pnpm", "build"]:
                    environment = cast(Mapping[str, object], kwargs["env"])
                    staging_path = Path(str(environment["CAR_PICKER_SITE_OUTPUT"]))
                    (staging_path / "index.html").write_text(
                        "<html>incomplete</html>", encoding="utf-8"
                    )
                    (staging_path / "app.js").write_text(
                        "this is not a completed bundle", encoding="utf-8"
                    )
                    (staging_path / "styles.css").write_text(
                        "body {}", encoding="utf-8"
                    )
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("subprocess.run", side_effect=run_frontend_command):
                with self.assertRaises(SiteBuildError):
                    build_site(FIXTURE_DATASET, site_path)

            final_site = {path.name: path.read_bytes() for path in site_path.iterdir()}

        self.assertEqual(final_site, initial_site)

    def test_site_lifecycle_is_exposed_through_one_package_interface(self) -> None:
        self.assertIn("CatalogueSite", car_picker.__all__)
        self.assertTrue(hasattr(car_picker, "CatalogueSite"))
        self.assertNotIn("build_site", car_picker.__all__)
        self.assertNotIn("open_site", car_picker.__all__)
        self.assertNotIn("serve_site", car_picker.__all__)

    def test_build_site_publishes_the_exact_serialized_dataset_and_schema(self) -> None:
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            write_workspace_dataset(workspace, FIXTURE_DATASET)
            site_path = workspace / "var/site"
            result = run_cli("--workspace", str(workspace), "site", "build")
            packaged_dataset = json.loads(
                (site_path / "catalogue-dataset.json").read_text(encoding="utf-8")
            )
            packaged_schema = json.loads(
                (site_path / "catalogue-dataset-schema.json").read_text(
                    encoding="utf-8"
                )
            )
            packaged_files = {path.name for path in site_path.iterdir()}

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(packaged_dataset, dataset)
        self.assertEqual(packaged_schema, catalogue_dataset_json_schema())
        self.assertEqual(
            packaged_files,
            {
                "app.js",
                "catalogue-dataset.json",
                "catalogue-dataset-schema.json",
                "catalogue-site-integrity.json",
                "index.html",
                "styles.css",
            },
        )

    def test_build_site_rejects_the_superseded_dataset_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "catalogue-dataset/v0",
                        "coverage": [],
                        "catalogueOffers": [],
                    }
                ),
                encoding="utf-8",
            )
            site_path = workspace / "var/site"
            result = run_cli("--workspace", str(workspace), "site", "build")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(site_path.exists())
        self.assertIn("providers", result.stderr)

    def test_build_site_rejects_unknown_dataset_fields(self) -> None:
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        dataset["offers"][0]["unexpected"] = True

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = run_cli("--workspace", str(workspace), "site", "build")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Extra inputs are not permitted", result.stderr)

    def test_build_site_rejects_invalid_generated_at_before_creating_artifacts(
        self,
    ) -> None:
        dataset = copy.deepcopy(json.loads(FIXTURE_DATASET.read_text(encoding="utf-8")))
        dataset["generatedAt"] = "not-a-timestamp"

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            dataset_path = workspace / "var/catalogue-dataset.json"
            site_path = workspace / "var/site"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = run_cli("--workspace", str(workspace), "site", "build")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(site_path.exists())
        self.assertIn("generatedAt", result.stderr)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
