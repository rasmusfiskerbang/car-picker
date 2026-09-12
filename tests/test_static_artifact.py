from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from tests.site_helpers import build_site, write_workspace_dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/browser-catalogue-dataset.json"


class StaticArtifactTest(unittest.TestCase):
    def test_failed_frontend_generation_reports_and_preserves_the_prior_site(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            site_path = temporary_path / "var/site"
            write_workspace_dataset(temporary_path, FIXTURE_DATASET)
            build_site(FIXTURE_DATASET, site_path)
            initial_site = {
                path.name: path.read_bytes() for path in site_path.iterdir()
            }

            fake_bin = temporary_path / "bin"
            fake_bin.mkdir()
            fake_pnpm = fake_bin / "pnpm"
            fake_pnpm.write_text("#!/bin/sh\nexit 17\n", encoding="utf-8")
            fake_pnpm.chmod(0o755)
            environment = os.environ | {"PATH": str(fake_bin)}

            result = run_cli(
                "--workspace",
                str(temporary_path),
                "site",
                "build",
                env=environment,
            )

            final_site = {path.name: path.read_bytes() for path in site_path.iterdir()}

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("safe state", result.stderr)
        self.assertIn(str(site_path), result.stderr)
        self.assertEqual(final_site, initial_site)

    def test_failed_dataset_build_preserves_the_prior_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            site_path = temporary_path / "var/site"
            build_site(FIXTURE_DATASET, site_path)
            initial_dataset = (site_path / "catalogue-dataset.json").read_bytes()

            invalid_dataset = copy.deepcopy(
                json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
            )
            invalid_dataset["offers"][0]["canonicalOfferUrl"] = (
                "http://example.test/invalid"
            )
            invalid_path = temporary_path / "invalid-dataset.json"
            invalid_path.write_text(json.dumps(invalid_dataset), encoding="utf-8")

            with self.assertRaises(ValueError):
                build_site(invalid_path, site_path)

            final_dataset = (site_path / "catalogue-dataset.json").read_bytes()

        self.assertEqual(final_dataset, initial_dataset)

    def test_serve_site_binds_the_completed_artifact_on_all_interfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            site_path = workspace / "var/site"
            write_workspace_dataset(workspace, FIXTURE_DATASET)
            build_site(FIXTURE_DATASET, site_path)
            port = free_port()
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "--workspace",
                    str(workspace),
                    "site",
                    "serve",
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
                if server.stdout is not None:
                    server.stdout.close()
                if server.stderr is not None:
                    server.stderr.close()

        self.assertIn("<title>Bilvalg</title>", response)

    def test_serve_site_rejects_nested_internal_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            site_path = workspace / "var/site"
            write_workspace_dataset(workspace, FIXTURE_DATASET)
            build_site(FIXTURE_DATASET, site_path)
            internal_path = site_path / "internal"
            internal_path.mkdir()
            (internal_path / "sourceMetadata.json").write_text("{}", encoding="utf-8")

            serve = run_cli("--workspace", str(workspace), "site", "serve")

        self.assertNotEqual(serve.returncode, 0)
        self.assertIn("must contain only approved regular files", serve.stderr)

    def test_serve_site_rejects_a_nonempty_corrupt_compiled_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            site_path = workspace / "var/site"
            write_workspace_dataset(workspace, FIXTURE_DATASET)
            build_site(FIXTURE_DATASET, site_path)
            (site_path / "styles.css").write_bytes(b"corrupt but non-empty")

            serve = run_cli("--workspace", str(workspace), "site", "serve")

        self.assertNotEqual(serve.returncode, 0)
        self.assertIn("integrity", serve.stderr)


def run_cli(
    *arguments: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        env=env,
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
