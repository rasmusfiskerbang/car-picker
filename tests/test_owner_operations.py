from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class OwnerOperationsTest(unittest.TestCase):
    def test_validate_checks_schemas_and_rejects_generated_artifacts_in_git_history(self) -> None:
        valid_checkout_result = run_cli(
            "validate",
            "--dataset",
            str(FIXTURE_DATASET),
            "--repository",
            str(REPOSITORY_ROOT),
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            run_git(repository, "init")
            site_path = repository / "site"
            site_path.mkdir()
            (site_path / "index.html").write_text("<p>Generated site</p>", encoding="utf-8")
            generated_data_path = repository / "var/catalogue-dataset.json"
            generated_data_path.parent.mkdir()
            generated_data_path.write_text('{"providerOfferData":true}', encoding="utf-8")
            run_git(repository, "add", "site/index.html", "var/catalogue-dataset.json")
            run_git(
                repository,
                "-c",
                "user.name=Fixture Owner",
                "-c",
                "user.email=owner@example.test",
                "commit",
                "-m",
                "accidentally track generated site",
            )

            generated_artifact_result = run_cli(
                "validate",
                "--dataset",
                str(FIXTURE_DATASET),
                "--repository",
                str(repository),
            )

        self.assertEqual(valid_checkout_result.returncode, 0, valid_checkout_result.stderr)
        self.assertIn("schema and Git-history validation passed", valid_checkout_result.stdout)
        self.assertNotEqual(generated_artifact_result.returncode, 0)
        self.assertIn("generated provider content or built artifacts", generated_artifact_result.stderr)
        self.assertIn("site/index.html", generated_artifact_result.stderr)
        self.assertIn("var/catalogue-dataset.json", generated_artifact_result.stderr)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )


if __name__ == "__main__":
    unittest.main()
