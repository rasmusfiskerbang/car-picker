from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from car_picker.__main__ import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class LegalReleaseGateTest(unittest.TestCase):
    def test_pre_transition_validation_records_the_horizon_without_claiming_revalidation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            legal_record_path = commit_legal_record(
                repository,
                {
                    "schemaVersion": "consumer-credit-legal-review/v1",
                    "changeHorizon": "2026-11-20",
                    "revalidation": None,
                },
            )

            result = run_cli_on_date(
                date(2026, 11, 19),
                "validate",
                "--dataset",
                str(FIXTURE_DATASET),
                "--repository",
                str(repository),
                "--legal-record",
                str(legal_record_path),
            )
            legal_record = json.loads(legal_record_path.read_text(encoding="utf-8"))
            legal_record_path.write_text(
                json.dumps({**legal_record, "revalidation": {}}),
                encoding="utf-8",
            )
            uncommitted_update_result = run_cli_on_date(
                date(2026, 11, 19),
                "validate",
                "--dataset",
                str(FIXTURE_DATASET),
                "--repository",
                str(repository),
                "--legal-record",
                str(legal_record_path),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("change horizon 2026-11-20", result.stdout)
        self.assertIn("post-transition revalidation is pending", result.stdout)
        self.assertIsNone(legal_record["revalidation"])
        self.assertNotEqual(uncommitted_update_result.returncode, 0)
        self.assertIn(
            "must be committed without local changes before release validation",
            uncommitted_update_result.stderr,
        )

    def test_transition_date_requires_a_completed_revalidation_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            legal_record_path = commit_legal_record(
                repository,
                {
                    "schemaVersion": "consumer-credit-legal-review/v1",
                    "changeHorizon": "2026-11-20",
                    "revalidation": None,
                },
            )

            result = run_cli_on_date(
                date(2026, 11, 20),
                "validate",
                "--dataset",
                str(FIXTURE_DATASET),
                "--repository",
                str(repository),
                "--legal-record",
                str(legal_record_path),
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "release on or after 2026-11-20 requires a completed consumer-credit revalidation",
            result.stderr,
        )

    def test_transition_release_accepts_a_complete_dated_official_revalidation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            legal_record_path = commit_legal_record(
                repository,
                completed_legal_record(),
            )

            result = run_cli_on_date(
                date(2026, 11, 20),
                "validate",
                "--dataset",
                str(FIXTURE_DATASET),
                "--repository",
                str(repository),
                "--legal-record",
                str(legal_record_path),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("consumer-credit revalidation reviewed 2026-11-20", result.stdout)
        self.assertIn("owner sign-off Fixture Owner on 2026-11-20", result.stdout)

    def test_transition_release_rejects_sources_not_effective_on_the_review_date(self) -> None:
        ineffective_intervals = (
            ("future", "2030-01-01", None),
            ("expired", "2020-01-01", "2021-01-01"),
        )
        for description, effective_from, effective_to in ineffective_intervals:
            with self.subTest(description=description), tempfile.TemporaryDirectory() as temporary_directory:
                repository = Path(temporary_directory)
                record = completed_legal_record()
                revalidation = record["revalidation"]
                assert isinstance(revalidation, dict)
                sources = revalidation["sources"]
                assert isinstance(sources, list)
                source = sources[0]
                assert isinstance(source, dict)
                source["effectiveFrom"] = effective_from
                source["effectiveTo"] = effective_to
                legal_record_path = commit_legal_record(repository, record)

                result = run_cli_on_date(
                    date(2026, 11, 20),
                    "validate",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--repository",
                    str(repository),
                    "--legal-record",
                    str(legal_record_path),
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be effective on the review date", result.stderr)


def commit_legal_record(repository: Path, record: dict[str, object]) -> Path:
    run_git(repository, "init")
    legal_record_path = repository / "config/consumer-credit-legal-review.json"
    legal_record_path.parent.mkdir()
    legal_record_path.write_text(json.dumps(record), encoding="utf-8")
    run_git(repository, "add", "config/consumer-credit-legal-review.json")
    run_git(
        repository,
        "-c",
        "user.name=Fixture Owner",
        "-c",
        "user.email=owner@example.test",
        "commit",
        "-m",
        "record consumer-credit legal review",
    )
    return legal_record_path


def completed_legal_record() -> dict[str, object]:
    return {
        "schemaVersion": "consumer-credit-legal-review/v1",
        "changeHorizon": "2026-11-20",
        "revalidation": {
            "reviewedOn": "2026-11-20",
            "sources": [
                {
                    "kind": "official_law",
                    "title": "Then-current consumer-credit law",
                    "publisher": "Retsinformation",
                    "url": "https://www.retsinformation.dk/example-law",
                    "checkedOn": "2026-11-20",
                    "effectiveFrom": "2026-11-20",
                    "effectiveTo": None,
                },
                {
                    "kind": "official_guidance",
                    "title": "Then-current official consumer-credit guidance",
                    "publisher": "Official Danish authority",
                    "url": "https://official.example.test/example-guidance",
                    "checkedOn": "2026-11-20",
                    "effectiveFrom": "2026-11-20",
                    "effectiveTo": None,
                },
            ],
            "consumerCreditClassificationConclusion": "Recorded classification conclusion.",
            "disclosureRulesConclusion": "Recorded disclosure-rules conclusion.",
            "implementationImpact": "No application change required after source review.",
            "ownerSignOff": {
                "name": "Fixture Owner",
                "signedOn": "2026-11-20",
            },
        },
    }


def run_cli_on_date(validation_date: date, *arguments: str) -> subprocess.CompletedProcess[str]:
    class FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return validation_date

    stdout = io.StringIO()
    stderr = io.StringIO()
    command = [sys.executable, "-m", "car_picker", *arguments]
    return_code = 0
    with (
        patch("car_picker.legal_release.date", FrozenDate),
        patch.object(sys, "argv", ["car-picker", *arguments]),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            main()
        except SystemExit as error:
            if isinstance(error.code, int):
                return_code = error.code
            elif error.code is None:
                return_code = 0
            else:
                return_code = 1
                print(error.code, file=sys.stderr)
    return subprocess.CompletedProcess(
        command,
        return_code,
        stdout.getvalue(),
        stderr.getvalue(),
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
