from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from car_picker import Catalogue, ProviderRegistry
from car_picker.__main__ import app
from car_picker.collection import (
    UrlLibHttpClient,
    production_provider_adapters,
)
from car_picker.provider_scope import (
    FLEASING_CATALOGUE_URL,
    FLEASING_FLEXLEASING_URL,
    TERMINALEN_CATALOGUE_URL,
)
from typer.testing import CliRunner


PROJECT_ROOT = Path(__file__).parents[1]


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        return self._responses[url]


class ProductionCompositionTest(unittest.TestCase):
    def test_versioned_initial_registry_contains_complete_public_scope(self) -> None:
        snapshot = ProviderRegistry.open(
            PROJECT_ROOT / "config" / "provider-registry.jsonl"
        ).snapshot()

        self.assertEqual(
            [provider.model_dump(mode="json") for provider in snapshot.providers],
            [
                {
                    "id": "fleasing",
                    "name": "Fleasing",
                    "url": "https://fleasing.dk/",
                    "status": "active",
                },
                {
                    "id": "terminalen",
                    "name": "Terminalen",
                    "url": "https://www.terminalen.dk/",
                    "status": "active",
                },
            ],
        )

    def test_production_composition_refreshes_the_complete_fixture_catalogue(
        self,
    ) -> None:
        responses = fixture_responses()

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_initial_registry(workspace)
            client = FixtureHttpClient(responses)
            catalogue = Catalogue(
                workspace,
                adapters=production_provider_adapters(
                    client,
                    retrieved_at="2026-08-23T12:00:00Z",
                ),
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.provider_ids, ["fleasing", "terminalen"])
        self.assertEqual(report.catalogue_offer_count, 4)
        self.assertEqual(report.quarantined_candidate_count, 0)
        self.assertEqual(
            [offer.offer_identity for offer in dataset.offers],
            [
                "fleasing:442795427:private-b3e29d362bda",
                "fleasing:771869804:private-390493d196b5",
                "terminalen:HY_INSTER:private-2f775a9b781a",
                "terminalen:HY_INSTER:private-e25cc77f6e4b",
            ],
        )
        serialized = json.dumps(dataset.model_dump(mode="json"))
        self.assertNotIn("sourceMetadata", serialized)
        self.assertNotIn("admissionFacts", serialized)

    def test_owner_refresh_cli_uses_complete_static_composition_without_site_build(
        self,
    ) -> None:
        responses = fixture_responses()

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_initial_registry(workspace)
            client = FixtureHttpClient(responses)

            with (
                patch.object(UrlLibHttpClient, "get_text", side_effect=client.get_text),
                patch(
                    "car_picker.catalogue._current_timestamp",
                    return_value="2026-08-23T12:00:00Z",
                ),
            ):
                result = CliRunner().invoke(
                    app,
                    [
                        "--workspace",
                        str(workspace),
                        "--json",
                        "catalogue",
                        "refresh",
                    ],
                )

            dataset_path = workspace / "var" / "catalogue-dataset.json"
            dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

        self.assertEqual(result.exit_code, 0, result.output)
        report = json.loads(result.stdout)
        self.assertEqual(report["providerIds"], ["fleasing", "terminalen"])
        self.assertEqual(report["catalogueOfferCount"], 4)
        self.assertEqual(report["quarantinedCandidateCount"], 0)
        self.assertEqual(
            [offer["providerId"] for offer in dataset["offers"]],
            ["fleasing", "fleasing", "terminalen", "terminalen"],
        )
        self.assertFalse((workspace / "site").exists())
        self.assertEqual(
            client.requested_urls,
            [
                FLEASING_CATALOGUE_URL,
                FLEASING_FLEXLEASING_URL,
                "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427",
                "https://fleasing.dk/bil/?bmw-i4&vid=771869804",
                TERMINALEN_CATALOGUE_URL,
                "https://www.terminalen.dk/nye-biler/hyundai/hyundai-inster/pris-og-udstyr",
                "https://www.terminalen.dk/api/page/url?url=/nye-biler/hyundai/hyundai-inster/pris-og-udstyr&culture=da-DK",
            ],
        )

    def test_owner_refresh_keeps_access_and_adapter_identity_when_names_change(
        self,
    ) -> None:
        responses = fixture_responses()

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_initial_registry(workspace)
            client = FixtureHttpClient(responses)
            registry_path = workspace / "config/provider-registry.jsonl"
            renamed_records = []
            for line in registry_path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                renamed_records.append({**record, "name": f"{record['name']} DK"})
            registry_path.write_text(
                "".join(json.dumps(record) + "\n" for record in renamed_records),
                encoding="utf-8",
            )

            with (
                patch.object(UrlLibHttpClient, "get_text", side_effect=client.get_text),
                patch(
                    "car_picker.catalogue._current_timestamp",
                    return_value="2026-08-23T12:00:00Z",
                ),
            ):
                result = CliRunner().invoke(
                    app,
                    ["--workspace", str(workspace), "--json", "catalogue", "refresh"],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.stdout)["catalogueOfferCount"], 4)

    def test_owner_refresh_cli_rejects_partial_or_runtime_source_controls(self) -> None:
        invocations = (
            ["catalogue", "refresh", "terminalen"],
            ["catalogue", "refresh", "--provider", "terminalen"],
            ["catalogue", "refresh", "--adapter", "terminalen"],
            ["catalogue", "refresh", "--source", "https://example.test/"],
            ["catalogue", "refresh", "--force"],
        )

        for invocation in invocations:
            with self.subTest(invocation=invocation):
                result = CliRunner().invoke(app, invocation)

                self.assertNotEqual(result.exit_code, 0)
                self.assertRegex(
                    result.output.lower(),
                    "no such (option|command)|unexpected extra argument",
                )


def fixture_responses() -> dict[str, str]:
    fleasing_details = {
        "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427": (
            "fleasing/aston-martin-db9.html"
        ),
        "https://fleasing.dk/bil/?bmw-i4&vid=771869804": "fleasing/bmw-i4.html",
    }
    price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
    price_url = f"https://www.terminalen.dk{price_path}"
    api_url = f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
    return {
        FLEASING_CATALOGUE_URL: fixture_text("fleasing/catalogue.html"),
        FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
        **{url: fixture_text(path) for url, path in fleasing_details.items()},
        TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
        price_url: fixture_text("terminalen/inster-price-page.html"),
        api_url: fixture_text("terminalen/inster-price-page.json"),
    }


def fixture_text(relative_path: str) -> str:
    return (PROJECT_ROOT / "tests" / "fixtures" / relative_path).read_text(
        encoding="utf-8"
    )


def write_initial_registry(workspace: Path) -> None:
    registry_path = workspace / "config" / "provider-registry.jsonl"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_bytes(
        (PROJECT_ROOT / "config" / "provider-registry.jsonl").read_bytes()
    )


if __name__ == "__main__":
    unittest.main()
