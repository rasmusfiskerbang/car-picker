from __future__ import annotations

import unittest
import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from car_picker.fleasing import FleasingAdapter, StructuralSourceError, catalogue_detail_urls


FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixtures/fleasing"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_URL = "https://fleasing.dk/biler/"
DETAIL_URL = "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427"
MISSING_MONTHLY_DETAIL_URL = "https://fleasing.dk/bil/?bmw-i4&vid=771869804"


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        return self.responses[url]


class FleasingAdapterTest(unittest.TestCase):
    def test_ignores_catalogue_links_to_an_undesignated_host(self) -> None:
        detail_urls = catalogue_detail_urls(
            """
            <a href="/bil/?a&amp;vid=442795427">Fleasing</a>
            <a href="https://bilinfo.dk/bil/?a&amp;vid=999">Bilinfo</a>
            """,
            CATALOGUE_URL,
        )

        self.assertEqual(detail_urls, ["https://fleasing.dk/bil/?a&vid=442795427"])

    def test_collects_each_private_vat_inclusive_configuration_with_evidence(self) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
                DETAIL_URL: (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(encoding="utf-8"),
                MISSING_MONTHLY_DETAIL_URL: (FIXTURE_DIRECTORY / "bmw-i4.html").read_text(encoding="utf-8"),
            }
        )

        candidates = FleasingAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect()

        self.assertEqual(client.requested_urls, [CATALOGUE_URL, DETAIL_URL, MISSING_MONTHLY_DETAIL_URL])
        self.assertEqual(
            [(candidate["offerIdentity"], candidate["admissionStatus"]) for candidate in candidates],
            [
                ("fleasing:442795427:private-b3e29d362bda", "quarantined"),
                ("fleasing:771869804:private-390493d196b5", "quarantined"),
            ],
        )
        candidate = candidates[0]
        self.assertEqual(candidate["advertisedMonthlyPayment"]["valueDkk"], 15865)
        self.assertEqual(candidate["termMonths"]["value"], 12)
        self.assertEqual(candidate["vehicleSpecification"]["value"], {
            "make": "Aston Martin",
            "model": "DB9",
            "trim": "Volante aut.",
        })
        self.assertEqual(
            candidate["advertisedMonthlyPayment"]["evidence"],
            {
                "sourceUrl": DETAIL_URL,
                "wording": "Ydelse pr. måned 15.865 kr. /inkl. moms",
            },
        )
        self.assertEqual(candidate["sourceMetadata"]["parserVersion"], "fleasing-html-v2")
        self.assertEqual(len(candidate["sourceMetadata"]["documents"][0]["contentSha256"]), 64)
        self.assertEqual(
            candidate["quarantineReasons"],
            [
                {"fact": "passengerCarScope", "state": "not_stated"},
                {"fact": "supportedLeasingForm", "state": "unclear"},
            ],
        )
        self.assertEqual(
            candidates[1]["quarantineReasons"],
            [
                {"fact": "passengerCarScope", "state": "not_stated"},
                {"fact": "supportedLeasingForm", "state": "unclear"},
                {"fact": "advertisedMonthlyPayment", "state": "not_stated"},
            ],
        )

    def test_detects_a_detail_page_that_loses_the_private_configuration_structure(self) -> None:
        client = FixtureHttpClient(
            {
                CATALOGUE_URL: (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
                DETAIL_URL: """
                    <article data-offer-id="442795427" data-make="Aston Martin" data-model="DB9"
                    data-trim="Volante" data-passenger-car="true" data-availability="available"></article>
                """,
            }
        )

        with self.assertRaisesRegex(StructuralSourceError, "private-pricing tab"):
            FleasingAdapter(client, retrieved_at="2026-07-22T12:00:00Z").collect()

    def test_refresh_fleasing_cli_writes_an_atomic_catalogue_dataset(self) -> None:
        """The owner can refresh the bounded Fleasing source through the public CLI."""
        responses = {
            "/biler/": (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
            "/bil/?aston-martin-db9-volante-aut&vid=442795427": (FIXTURE_DIRECTORY / "aston-martin-db9.html").read_text(encoding="utf-8"),
            "/bil/?bmw-i4&vid=771869804": (FIXTURE_DIRECTORY / "bmw-i4.html").read_text(encoding="utf-8"),
        }
        server = fixture_server(responses)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server_thread.join)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "refresh-fleasing",
                    "--catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/biler/",
                    "--dataset",
                    str(dataset_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
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
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        self.assertEqual(dataset["schemaVersion"], "catalogue-dataset/v1")
        self.assertEqual(dataset["coverage"], {
            "providers": [{
                "name": "Fleasing",
                "designatedSource": "Fleasing passenger-car catalogue and linked detail pages",
                "quarantinedCandidateCount": 2,
            }]
        })
        self.assertEqual(
            [(candidate["offerIdentity"], candidate["admissionStatus"]) for candidate in dataset["catalogueOffers"]],
            [
                ("fleasing:442795427:private-b3e29d362bda", "quarantined"),
                ("fleasing:771869804:private-390493d196b5", "quarantined"),
            ],
        )
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            [],
        )

    def test_refresh_fleasing_cli_preserves_the_prior_dataset_after_a_source_failure(self) -> None:
        responses = {
            "/biler/": (FIXTURE_DIRECTORY / "catalogue.html").read_text(encoding="utf-8"),
            "/bil/?aston-martin-db9-volante-aut&vid=442795427": "<div class=\"vehicle-page-info\"></div>",
        }
        server = fixture_server(responses)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server_thread.join)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "catalogue-dataset.json"
            prior_dataset = '{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
            dataset_path.write_text(prior_dataset, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "refresh-fleasing",
                    "--catalogue-url",
                    f"http://127.0.0.1:{server.server_port}/biler/",
                    "--dataset",
                    str(dataset_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            active_dataset = dataset_path.read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(active_dataset, prior_dataset)

    def test_refresh_fleasing_cli_refuses_an_undesignated_live_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "catalogue-dataset.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "refresh-fleasing",
                    "--catalogue-url",
                    "https://fleasing.dk/wp-admin/",
                    "--dataset",
                    str(dataset_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("designated catalogue", result.stderr)
        self.assertFalse(dataset_path.exists())


def fixture_server(responses: dict[str, str]) -> ThreadingHTTPServer:
    class FixtureHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            response = responses.get(self.path) or responses.get(urlparse(self.path).path)
            if response is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)


if __name__ == "__main__":
    unittest.main()
