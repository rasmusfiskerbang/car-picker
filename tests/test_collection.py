from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from car_picker.collection import refresh_catalogue


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FLEASING_FIXTURES = Path(__file__).resolve().parent / "fixtures/fleasing"
TERMINALEN_FIXTURES = Path(__file__).resolve().parent / "fixtures/terminalen"


def candidate(
    provider: str, identity: str, status: str = "admitted"
) -> dict[str, object]:
    evidence = {
        "sourceUrl": f"https://example.test/{provider.lower()}",
        "wording": "Fixture evidence",
    }
    known_boolean = {"state": "known", "value": True, "evidence": evidence}
    value: dict[str, object] = {
        "provider": provider,
        "offerIdentity": identity,
        "admissionOutcome": status,
        "vehicleSpecification": {
            "state": "known",
            "value": {"make": "Fixture", "model": "Car"},
            "evidence": evidence,
        },
        "privateConsumerEligibility": known_boolean,
        "passengerCarScope": known_boolean,
        "currentAvailability": known_boolean,
        "supportedLeasingForm": {
            "state": "known",
            "value": "operational",
            "evidence": evidence,
        },
        "advertisedMonthlyPayment": {
            "state": "known",
            "valueDkk": 1000,
            "evidence": evidence,
        },
        "termMonths": {"state": "known", "value": 12, "evidence": evidence},
        "baseCashFlowStream": [
            {
                "meaning": "Fixture payment",
                "direction": "payment",
                "amountDkk": 1000,
                "amountBasis": "including_vat",
                "timing": "recurring",
                "recurrenceCount": 12,
                "refundability": "not_refundable",
                "includedInBase": True,
                "evidence": evidence,
            }
        ],
        "sourceMetadata": {"documents": [{"sourceUrl": evidence["sourceUrl"]}]},
    }
    if status == "quarantined":
        value["quarantineReasons"] = [
            {"fact": "supportedLeasingForm", "state": "unclear"}
        ]
        value["supportedLeasingForm"] = {
            "state": "unclear",
            "evidence": evidence,
        }
    return value


class CollectionTest(unittest.TestCase):
    def test_public_cli_has_no_one_provider_dataset_writer(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "car_picker", "refresh-fleasing"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refresh-fleasing", result.stderr)

    def test_refresh_catalogue_cli_publishes_both_covered_providers(self) -> None:
        responses = {
            "/biler/": (FLEASING_FIXTURES / "catalogue.html").read_text(
                encoding="utf-8"
            ),
            "/bil/?aston-martin-db9-volante-aut&vid=442795427": (
                FLEASING_FIXTURES / "aston-martin-db9.html"
            ).read_text(encoding="utf-8"),
            "/bil/?bmw-i4&vid=771869804": (FLEASING_FIXTURES / "bmw-i4.html").read_text(
                encoding="utf-8"
            ),
            "/terminalen": (TERMINALEN_FIXTURES / "catalogue.html").read_text(
                encoding="utf-8"
            ),
            "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr": (
                TERMINALEN_FIXTURES / "inster-price-page.html"
            ).read_text(encoding="utf-8"),
            "/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr&culture=da-DK": (
                TERMINALEN_FIXTURES / "inster-price-page.json"
            ).read_text(encoding="utf-8"),
        }
        server = fixture_server(responses)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue-dataset.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "refresh-catalogue",
                    "--dataset",
                    str(path),
                    "--fleasing-catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/biler/",
                    "--terminalen-catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/terminalen",
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            dataset = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            [row["name"] for row in dataset["coverage"]["providers"]],
            ["Fleasing", "Terminalen"],
        )
        self.assertEqual(len(dataset["catalogueOffers"]), 2)
        self.assertEqual(len(dataset["quarantinedCandidates"]), 2)
        self.assertIn(
            "WARNING provider aggregate reconciliation mismatch:", result.stdout
        )
        self.assertIn("terminalen:HY_INSTER:", result.stdout)

    def test_complete_fixture_refresh_carries_admitted_catalogue_offers_into_static_catalogue(
        self,
    ) -> None:
        fleasing_detail_path = "/bil/?porsche-taycan&vid=982451736"
        responses = {
            "/biler/": (f'<a href="{fleasing_detail_path}">Porsche Taycan</a>'),
            fleasing_detail_path: (
                FLEASING_FIXTURES / "porsche-taycan-configurations.html"
            ).read_text(encoding="utf-8"),
            "/terminalen": (TERMINALEN_FIXTURES / "catalogue.html").read_text(
                encoding="utf-8"
            ),
            "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr": (
                TERMINALEN_FIXTURES / "inster-price-page.html"
            ).read_text(encoding="utf-8"),
            "/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr&culture=da-DK": (
                TERMINALEN_FIXTURES / "inster-price-page.json"
            ).read_text(encoding="utf-8"),
        }
        server = fixture_server(responses)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as directory:
            temporary_path = Path(directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            provider_control_path = temporary_path / "provider-control.json"
            provider_control_path.write_text(
                (REPOSITORY_ROOT / "config/provider-control.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            refresh_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "refresh-catalogue",
                    "--dataset",
                    str(dataset_path),
                    "--fleasing-catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/biler/",
                    "--terminalen-catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/terminalen",
                    "--provider-control",
                    str(provider_control_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(refresh_result.returncode, 0, refresh_result.stderr)
            build_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    str(site_path),
                    "--provider-control",
                    str(provider_control_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_result.returncode, 0, build_result.stderr)
            dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        fleasing_candidates = [
            candidate
            for candidate in dataset["catalogueOffers"]
            if candidate["provider"] == "Fleasing"
        ]
        self.assertEqual(
            [
                (candidate["offerIdentity"], candidate["admissionOutcome"])
                for candidate in fleasing_candidates
            ],
            [
                ("fleasing:982451736:private-standard", "admitted"),
                ("fleasing:982451736:private-low-upfront", "admitted"),
            ],
        )
        fleasing_offers = [
            offer for offer in projection["offers"] if offer["provider"] == "Fleasing"
        ]
        self.assertEqual(len(fleasing_offers), 2)
        self.assertEqual(
            fleasing_offers[0]["advertisedMonthlyPayment"]["valueDkk"], 9995
        )
        self.assertEqual(
            fleasing_offers[0]["upfrontCashRequirement"]["valueDkk"], 149995
        )
        self.assertEqual(
            fleasing_offers[0]["advertisedMonthlyPayment"]["evidence"]["wording"],
            "Ydelse pr. måned 9.995 kr. /inkl. moms",
        )
        terminalen_candidates = [
            candidate
            for candidate in dataset["catalogueOffers"]
            if candidate["provider"] == "Terminalen"
        ]
        self.assertEqual(len(terminalen_candidates), 2)
        self.assertTrue(
            all(
                candidate["admissionOutcome"] == "admitted"
                for candidate in terminalen_candidates
            )
        )
        self.assertEqual(
            terminalen_candidates[0]["providerAdvertisedAggregate"]["valueDkk"],
            117195,
        )
        terminalen_offers = [
            offer for offer in projection["offers"] if offer["provider"] == "Terminalen"
        ]
        self.assertEqual(len(terminalen_offers), 2)
        self.assertEqual(
            terminalen_offers[0]["advertisedMonthlyPayment"]["valueDkk"], 3095
        )
        self.assertEqual(
            terminalen_offers[0]["providerFormLabel"]["value"], "Privatleasing"
        )
        self.assertEqual(
            terminalen_offers[0]["nominalBaseOutlay"]["state"], "not_stated"
        )
        self.assertIn(
            "providerAdvertisedAggregateMismatch",
            terminalen_offers[0]["nominalBaseOutlay"]["blockingFacts"],
        )
        self.assertEqual(
            terminalen_offers[0]["advertisedMonthlyPayment"]["evidence"]["sourceUrl"],
            f"http://127.0.0.1:{server.server_port}"
            "/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
            "&culture=da-DK",
        )

    def test_retries_each_provider_at_most_twice_and_publishes_one_complete_generation(
        self,
    ) -> None:
        calls: list[str] = []
        sleeps: list[float] = []
        fleasing_attempts = 0

        def collect_fleasing() -> list[dict[str, object]]:
            nonlocal fleasing_attempts
            calls.append("Fleasing")
            fleasing_attempts += 1
            if fleasing_attempts < 3:
                raise OSError("temporary source failure")
            return [candidate("Fleasing", "fleasing:one", "quarantined")]

        def collect_terminalen() -> list[dict[str, object]]:
            calls.append("Terminalen")
            return [candidate("Terminalen", "terminalen:one")]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue-dataset.json"
            refresh_catalogue(
                path,
                collect_fleasing=collect_fleasing,
                collect_terminalen=collect_terminalen,
                generated_at=lambda: "2026-07-22T12:00:00Z",
                sleep=sleeps.append,
            )
            dataset = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(calls, ["Fleasing", "Fleasing", "Fleasing", "Terminalen"])
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertEqual(dataset["generatedAt"], "2026-07-22T12:00:00Z")
        self.assertEqual(
            [row["name"] for row in dataset["coverage"]["providers"]],
            ["Fleasing", "Terminalen"],
        )
        self.assertEqual(
            [row["offerIdentity"] for row in dataset["catalogueOffers"]],
            ["terminalen:one"],
        )
        self.assertEqual(
            [row["offerIdentity"] for row in dataset["quarantinedCandidates"]],
            ["fleasing:one"],
        )

    def test_preserves_the_prior_dataset_when_terminalen_fails_after_fleasing_succeeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue-dataset.json"
            prior = '{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
            path.write_text(prior, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Terminalen collection failed"):
                refresh_catalogue(
                    path,
                    collect_fleasing=lambda: [candidate("Fleasing", "fleasing:one")],
                    collect_terminalen=lambda: (_ for _ in ()).throw(
                        OSError("Terminalen unavailable")
                    ),
                    generated_at=lambda: "2026-07-22T12:00:00Z",
                    sleep=lambda _: None,
                )
            self.assertEqual(path.read_text(encoding="utf-8"), prior)

    def test_preserves_the_prior_dataset_when_validation_rejects_a_partial_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue-dataset.json"
            prior = '{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
            path.write_text(prior, encoding="utf-8")
            partial = candidate("Terminalen", "terminalen:one")
            partial.pop("sourceMetadata")
            with self.assertRaisesRegex(ValueError, "sourceMetadata"):
                refresh_catalogue(
                    path,
                    collect_fleasing=lambda: [candidate("Fleasing", "fleasing:one")],
                    collect_terminalen=lambda: [partial],
                    generated_at=lambda: "2026-07-22T12:00:00Z",
                    sleep=lambda _: None,
                )
            self.assertEqual(path.read_text(encoding="utf-8"), prior)

    def test_rejects_a_candidate_with_an_unknown_admission_outcome(self) -> None:
        pending = candidate("Terminalen", "terminalen:pending")
        pending["admissionOutcome"] = "pending"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue-dataset.json"
            with self.assertRaisesRegex(ValueError, "valid admission outcome"):
                refresh_catalogue(
                    path,
                    collect_fleasing=lambda: [candidate("Fleasing", "fleasing:one")],
                    collect_terminalen=lambda: [pending],
                    generated_at=lambda: "2026-07-22T12:00:00Z",
                    sleep=lambda _: None,
                )


if __name__ == "__main__":
    unittest.main()


def fixture_server(responses: dict[str, str]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            content = responses.get(self.path)
            if content is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
                if self.path.startswith("/api/")
                else "text/html; charset=utf-8",
            )
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
