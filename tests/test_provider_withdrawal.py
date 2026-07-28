from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_CONTROL = REPOSITORY_ROOT / "config/provider-control.json"
FLEASING_FIXTURES = Path(__file__).resolve().parent / "fixtures/fleasing"
TERMINALEN_FIXTURES = Path(__file__).resolve().parent / "fixtures/terminalen"


@dataclass(frozen=True)
class WithdrawalRun:
    withdrawal: subprocess.CompletedProcess[str]
    refresh: subprocess.CompletedProcess[str]
    build: subprocess.CompletedProcess[str]
    control_path: Path
    dataset_path: Path
    site_path: Path


class ProviderWithdrawalTest(unittest.TestCase):
    def test_withdrawal_disables_retrieval_and_removes_provider_content_from_the_next_dataset_and_site(self) -> None:
        received_at = datetime.now(UTC) - timedelta(minutes=1)
        received_at_text = received_at.isoformat().replace("+00:00", "Z")
        deadline_at_text = (received_at + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        responses = {
            "/terminalen": (TERMINALEN_FIXTURES / "catalogue.html").read_text(encoding="utf-8"),
            "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr": (
                TERMINALEN_FIXTURES / "inster-price-page.html"
            ).read_text(encoding="utf-8"),
            "/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr&culture=da-DK": (
                TERMINALEN_FIXTURES / "inster-price-page.json"
            ).read_text(encoding="utf-8"),
        }
        run = self.run_withdrawal_workflow(
            provider="Fleasing",
            received_at=received_at_text,
            responses=responses,
            source_option="--terminalen-catalogue-url",
            source_path="/terminalen",
        )
        dataset = json.loads(run.dataset_path.read_text(encoding="utf-8"))
        projection = json.loads((run.site_path / "projection.json").read_text(encoding="utf-8"))
        control = json.loads(run.control_path.read_text(encoding="utf-8"))

        self.assertEqual(run.withdrawal.returncode, 0, run.withdrawal.stderr)
        self.assertEqual(run.refresh.returncode, 0, run.refresh.stderr)
        self.assertEqual(run.build.returncode, 0, run.build.stderr)
        self.assertEqual({offer["provider"] for offer in dataset["catalogueOffers"]}, {"Terminalen"})
        self.assertEqual([provider["name"] for provider in dataset["coverage"]["providers"]], ["Terminalen"])
        self.assertEqual([provider["name"] for provider in projection["coverage"]["providers"]], ["Terminalen"])
        self.assertEqual(
            dataset["coverageEnded"],
            [{"name": "Fleasing", "coverageEndedAt": control["withdrawals"][0]["retrievalDisabledAt"]}],
        )
        self.assertEqual(projection["coverageEnded"], dataset["coverageEnded"])
        self.assertNotIn("fleasing:", json.dumps(dataset).lower())
        self.assertNotIn("fleasing.dk", json.dumps(dataset).lower())
        self.assertNotIn("fleasing:", json.dumps(projection).lower())
        self.assertNotIn("fleasing.dk", json.dumps(projection).lower())
        self.assertEqual(control["providers"][0], {"name": "Fleasing", "retrievalEnabled": False})
        self.assertEqual(control["providers"][1], {"name": "Terminalen", "retrievalEnabled": True})
        withdrawal_record = control["withdrawals"][0]
        self.assertEqual(withdrawal_record["provider"], "Fleasing")
        self.assertEqual(withdrawal_record["receivedAt"], received_at_text)
        self.assertEqual(withdrawal_record["deadlineAt"], deadline_at_text)
        self.assertEqual(
            withdrawal_record["authenticationNote"],
            "Authenticated against the provider contact on file.",
        )
        self.assertIn("refreshCompletedAt", withdrawal_record)
        self.assertIn("siteBuildCompletedAt", withdrawal_record)
        self.assertTrue(withdrawal_record["completedWithinDeadline"])

    def test_site_build_rejects_a_dataset_from_before_the_withdrawal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            control_path = temporary_path / "provider-control.json"
            site_path = temporary_path / "site"
            control_path.write_bytes(PROVIDER_CONTROL.read_bytes())
            withdrawal = run_cli(
                "withdraw-provider",
                "--provider",
                "Terminalen",
                "--provider-control",
                str(control_path),
                "--received-at",
                "2026-07-28T10:00:00Z",
                "--authentication-note",
                "Authenticated against the provider contact on file.",
            )

            build = run_cli(
                "build-site",
                "--dataset",
                str(REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"),
                "--output",
                str(site_path),
                "--provider-control",
                str(control_path),
            )

        self.assertEqual(withdrawal.returncode, 0, withdrawal.stderr)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn("completed catalogue refresh", build.stderr)
        self.assertFalse(site_path.exists())

    def test_terminalen_withdrawal_leaves_only_the_ended_coverage_fact(self) -> None:
        responses = {
            "/biler/": (FLEASING_FIXTURES / "catalogue.html").read_text(encoding="utf-8"),
            "/bil/?aston-martin-db9-volante-aut&vid=442795427": (
                FLEASING_FIXTURES / "aston-martin-db9.html"
            ).read_text(encoding="utf-8"),
            "/bil/?bmw-i4&vid=771869804": (
                FLEASING_FIXTURES / "bmw-i4.html"
            ).read_text(encoding="utf-8"),
        }
        run = self.run_withdrawal_workflow(
            provider="Terminalen",
            received_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            responses=responses,
            source_option="--fleasing-catalogue-url",
            source_path="/biler/",
        )
        dataset = json.loads(run.dataset_path.read_text(encoding="utf-8"))
        projection = json.loads((run.site_path / "projection.json").read_text(encoding="utf-8"))
        dataset_without_ended_fact = {key: value for key, value in dataset.items() if key != "coverageEnded"}
        projection_without_ended_fact = {key: value for key, value in projection.items() if key != "coverageEnded"}
        other_artifact_content = "\n".join(
            path.read_text(encoding="utf-8")
            for path in run.site_path.iterdir()
            if path.name != "projection.json"
        )

        self.assertEqual(run.withdrawal.returncode, 0, run.withdrawal.stderr)
        self.assertEqual(run.refresh.returncode, 0, run.refresh.stderr)
        self.assertEqual(run.build.returncode, 0, run.build.stderr)
        self.assertEqual(dataset["coverageEnded"][0]["name"], "Terminalen")
        self.assertEqual(projection["coverageEnded"], dataset["coverageEnded"])
        self.assertNotIn("terminalen", json.dumps(dataset_without_ended_fact).lower())
        self.assertNotIn("terminalen", json.dumps(projection_without_ended_fact).lower())
        self.assertNotIn("terminalen", other_artifact_content.lower())

    def test_late_site_build_records_the_missed_deadline(self) -> None:
        responses = {
            "/terminalen": (TERMINALEN_FIXTURES / "catalogue.html").read_text(encoding="utf-8"),
            "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr": (
                TERMINALEN_FIXTURES / "inster-price-page.html"
            ).read_text(encoding="utf-8"),
            "/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr&culture=da-DK": (
                TERMINALEN_FIXTURES / "inster-price-page.json"
            ).read_text(encoding="utf-8"),
        }
        run = self.run_withdrawal_workflow(
            provider="Fleasing",
            received_at="2000-01-01T00:00:00Z",
            responses=responses,
            source_option="--terminalen-catalogue-url",
            source_path="/terminalen",
        )
        control = json.loads(run.control_path.read_text(encoding="utf-8"))

        self.assertEqual(run.withdrawal.returncode, 0, run.withdrawal.stderr)
        self.assertEqual(run.refresh.returncode, 0, run.refresh.stderr)
        self.assertNotEqual(run.build.returncode, 0)
        self.assertIn("24-hour provider-withdrawal deadline", run.build.stderr)
        self.assertTrue((run.site_path / "projection.json").is_file(), run.build.stderr)
        self.assertFalse(control["withdrawals"][0]["completedWithinDeadline"])

    def run_withdrawal_workflow(
        self,
        *,
        provider: str,
        received_at: str,
        responses: dict[str, str],
        source_option: str,
        source_path: str,
    ) -> WithdrawalRun:
        server = fixture_server(responses)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        temporary_path = Path(self.enterContext(tempfile.TemporaryDirectory()))
        control_path = temporary_path / "provider-control.json"
        dataset_path = temporary_path / "catalogue-dataset.json"
        site_path = temporary_path / "site"
        control_path.write_bytes(PROVIDER_CONTROL.read_bytes())
        withdrawal = run_cli(
            "withdraw-provider",
            "--provider",
            provider,
            "--provider-control",
            str(control_path),
            "--received-at",
            received_at,
            "--authentication-note",
            "Authenticated against the provider contact on file.",
        )
        refresh = run_cli(
            "refresh-catalogue",
            "--dataset",
            str(dataset_path),
            "--provider-control",
            str(control_path),
            source_option,
            f"http://127.0.0.1:{server.server_port}{source_path}",
        )
        build = run_cli(
            "build-site",
            "--dataset",
            str(dataset_path),
            "--output",
            str(site_path),
            "--provider-control",
            str(control_path),
        )
        return WithdrawalRun(withdrawal, refresh, build, control_path, dataset_path, site_path)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def fixture_server(responses: dict[str, str]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            content = responses.get(self.path)
            if content is None:
                self.send_error(404)
                return
            self.send_response(200)
            content_type = "application/json; charset=utf-8" if self.path.startswith("/api/") else "text/html; charset=utf-8"
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


if __name__ == "__main__":
    unittest.main()
