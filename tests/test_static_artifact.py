from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from car_picker.publication import build_site


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class StaticArtifactTest(unittest.TestCase):
    def test_build_exports_a_minimized_verified_artifact_and_preserves_the_prior_artifact_on_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            site_path = temporary_path / "site"
            first_build = run_cli(
                "build-site",
                "--dataset",
                str(FIXTURE_DATASET),
                "--output",
                str(site_path),
            )
            initial_projection = (site_path / "projection.json").read_bytes()
            initial_files = sorted(path.name for path in site_path.iterdir())
            malformed_dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
            malformed_dataset["catalogueOffers"][0]["vehicleSpecification"] = {
                "state": "known",
                "evidence": {
                    "sourceUrl": "https://example.test",
                    "wording": "Missing value",
                },
            }
            malformed_path = temporary_path / "catalogue-dataset.json"
            malformed_path.write_text(json.dumps(malformed_dataset), encoding="utf-8")
            failed_build = run_cli(
                "build-site",
                "--dataset",
                str(malformed_path),
                "--output",
                str(site_path),
            )

            projection = json.loads(initial_projection)
            schema = json.loads(
                (site_path / "projection-schema.json").read_text(encoding="utf-8")
            )
            final_projection = (site_path / "projection.json").read_bytes()

        self.assertEqual(first_build.returncode, 0, first_build.stderr)
        self.assertEqual(
            initial_files,
            [
                "app.js",
                "index.html",
                "projection-schema.json",
                "projection.json",
                "styles.css",
            ],
        )
        self.assertEqual(
            schema["$id"],
            "https://car-picker.local/schemas/catalogue-presentation-v1.json",
        )
        self.assertEqual(
            projection["schemaVersion"], schema["properties"]["schemaVersion"]["const"]
        )
        self.assertNotIn("sourceMetadata", json.dumps(projection))
        self.assertNotIn("quarantineReasons", json.dumps(projection))
        self.assertNotIn("contentSha256", json.dumps(projection))
        self.assertNotEqual(failed_build.returncode, 0)
        self.assertEqual(final_projection, initial_projection)

    def test_failed_browser_output_does_not_replace_the_completed_artifact(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            build_site(FIXTURE_DATASET, site_path)
            initial_app = (site_path / "app.js").read_bytes()
            malformed_browser_app = 'fetch("projection.json"); window.addEventListener("hashchange", () => {;'

            with patch(
                "car_picker.publication.browser_app", return_value=malformed_browser_app
            ):
                with self.assertRaisesRegex(ValueError, "unclosed syntax delimiters"):
                    build_site(FIXTURE_DATASET, site_path)

            final_app = (site_path / "app.js").read_bytes()

        self.assertEqual(final_app, initial_app)

    def test_invalid_presentation_projection_does_not_replace_the_completed_artifact(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            build_site(FIXTURE_DATASET, site_path)
            initial_projection = (site_path / "projection.json").read_bytes()

            with patch(
                "car_picker.publication.project_catalogue",
                return_value={
                    "schemaVersion": "catalogue-presentation/v1",
                    "generatedAt": "2026-07-22T12:00:00Z",
                },
            ):
                with self.assertRaises(ValueError):
                    build_site(FIXTURE_DATASET, site_path)

            final_projection = (site_path / "projection.json").read_bytes()

        self.assertEqual(final_projection, initial_projection)

    def test_serve_site_binds_the_completed_artifact_on_all_interfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            site_path = temporary_path / "site"
            build = run_cli(
                "build-site",
                "--dataset",
                str(FIXTURE_DATASET),
                "--output",
                str(site_path),
            )
            port = free_port()
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "serve-site",
                    "--site",
                    str(site_path),
                    "--port",
                    str(port),
                ],
                cwd=REPOSITORY_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                response = wait_for_site(port)
            finally:
                server.terminate()
                server.wait(timeout=5)
                assert server.stdout is not None
                assert server.stderr is not None
                server.stdout.close()
                server.stderr.close()

        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn("<title>Bilvalg</title>", response)

    def test_serve_site_rejects_nested_internal_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            build_site(FIXTURE_DATASET, site_path)
            internal_path = site_path / "internal"
            internal_path.mkdir()
            (internal_path / "sourceMetadata.json").write_text("{}", encoding="utf-8")

            serve = run_cli("serve-site", "--site", str(site_path))

        self.assertNotEqual(serve.returncode, 0)
        self.assertIn("must contain only approved regular files", serve.stderr)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_site(port: int) -> str:
    for _ in range(20):
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=0.2) as response:  # noqa: S310 - local test server.
                return response.read().decode("utf-8")
        except OSError:
            time.sleep(0.05)
    raise AssertionError("LAN server did not serve the completed static artifact")


if __name__ == "__main__":
    unittest.main()
