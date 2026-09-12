from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from car_picker import Catalogue, CatalogueCandidate
from car_picker.__main__ import app
from typer.testing import CliRunner

from tests.test_catalogue_contract import sample_dataset


class FixtureProviderAdapter:
    def __init__(
        self,
        provider_id: str,
        records: list[CatalogueCandidate],
        calls: list[str],
    ) -> None:
        self.provider_id = provider_id
        self._records = records
        self._calls = calls

    def collect(self) -> list[CatalogueCandidate]:
        self._calls.append(self.provider_id)
        return copy.deepcopy(self._records)


class CatalogueRefreshTest(unittest.TestCase):
    def test_refresh_uses_injected_adapters_in_active_registry_order(self) -> None:
        first_offer = candidate_for_provider("first", "first:car:one")
        second_offer = candidate_for_provider("second", "second:car:one")
        calls: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first"), provider("second")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    FixtureProviderAdapter("second", [second_offer], calls),
                    FixtureProviderAdapter("first", [first_offer], calls),
                ],
            )
            clock_calls: list[str] = []

            with patch(
                "car_picker.catalogue._current_timestamp",
                side_effect=lambda: (
                    clock_calls.append("clock") or "2026-08-16T12:00:00Z"
                ),
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(clock_calls, ["clock"])
        self.assertEqual(
            [provider.id for provider in dataset.providers], ["first", "second"]
        )
        self.assertEqual(
            [offer.offer_identity for offer in dataset.offers],
            ["first:car:one", "second:car:one"],
        )
        self.assertEqual(report.generated_at, "2026-08-16T12:00:00Z")

    def test_failed_collection_does_not_request_time_or_replace_active_dataset(
        self,
    ) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first"), provider("second")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[
                    FixtureProviderAdapter(
                        "first",
                        [candidate_for_provider("first", "first:car:one")],
                        calls,
                    ),
                    FailingAdapter("second", calls),
                ],
            )
            with patch(
                "car_picker.catalogue._current_timestamp",
                side_effect=AssertionError("time must be assigned after collection"),
            ):
                with self.assertRaisesRegex(ValueError, "second"):
                    catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, ["first", "second"])

    def test_refresh_skips_inactive_registry_providers(self) -> None:
        calls: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(
                workspace,
                [
                    {
                        **provider("first"),
                        "status": "inactive",
                        "reason": "blocked",
                        "explanation": "Owner paused this source.",
                    },
                    provider("second"),
                ],
            )
            catalogue = Catalogue(
                workspace,
                adapters=[
                    FixtureProviderAdapter(
                        "first",
                        [candidate_for_provider("first", "first:car:one")],
                        calls,
                    ),
                    FixtureProviderAdapter(
                        "second",
                        [candidate_for_provider("second", "second:car:one")],
                        calls,
                    ),
                ],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-16T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(calls, ["second"])
        self.assertEqual(report.provider_ids, ["second"])
        self.assertEqual([offer.provider_id for offer in dataset.offers], ["second"])

    def test_admission_quarantines_a_candidate_without_retaining_its_payload(
        self,
    ) -> None:
        candidate = candidate_for_provider(
            "first", "first:car:missing-offer", include_offer=False
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[FixtureProviderAdapter("first", [candidate], [])],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-16T12:00:00Z",
            ):
                report = catalogue.refresh()
            serialized = catalogue.current().model_dump(mode="json", by_alias=True)

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 1)
        self.assertEqual(serialized["offers"], [])
        self.assertEqual(
            serialized["quarantinedCandidates"],
            [
                {
                    "offerIdentity": "first:car:missing-offer",
                    "providerId": "first",
                    "canonicalSourceUrl": "https://first.example/offers/one",
                    "reasons": [
                        {
                            "criterion": "candidate_shape",
                            "state": "unclear",
                            "code": "candidate-shape.missing-offer",
                            "evidence": [
                                {
                                    "sourceUrl": "https://first.example/offers/one",
                                    "excerpt": "Candidate did not contain an Offer payload.",
                                }
                            ],
                        }
                    ],
                }
            ],
        )
        self.assertNotIn("admissionFacts", json.dumps(serialized))
        self.assertNotIn("rawSourceDocument", json.dumps(serialized))

    def test_admitted_candidate_becomes_an_offer_without_an_admission_record(
        self,
    ) -> None:
        candidate = candidate_for_provider("first", "first:car:one")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[FixtureProviderAdapter("first", [candidate], [])],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-16T12:00:00Z",
            ):
                catalogue.refresh()
            serialized = catalogue.current().model_dump(mode="json", by_alias=True)

        self.assertEqual(
            [offer["offerIdentity"] for offer in serialized["offers"]],
            ["first:car:one"],
        )
        self.assertNotIn("admissionFacts", json.dumps(serialized))

    def test_cli_reports_the_complete_refresh_as_human_text_or_stable_json(
        self,
    ) -> None:
        calls: list[str] = []
        adapters = [
            FixtureProviderAdapter(
                "first", [candidate_for_provider("first", "first:car:one")], calls
            )
        ]

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            runner = CliRunner()
            with patch(
                "car_picker.__main__.production_provider_adapters",
                return_value=adapters,
            ):
                human = runner.invoke(
                    app,
                    ["--workspace", str(workspace), "catalogue", "refresh"],
                )
                stable_json = runner.invoke(
                    app,
                    [
                        "--workspace",
                        str(workspace),
                        "--json",
                        "catalogue",
                        "refresh",
                    ],
                )

        self.assertEqual(human.exit_code, 0, human.stdout)
        self.assertIn("Catalogue Refresh", human.stdout)
        self.assertIn("Catalogue Offers: 1", human.stdout)
        self.assertEqual(stable_json.exit_code, 0, stable_json.stdout)
        report = json.loads(stable_json.stdout)
        self.assertEqual(
            list(report),
            [
                "catalogueOfferCount",
                "generatedAt",
                "kind",
                "providerIds",
                "quarantinedCandidateCount",
            ],
        )
        self.assertEqual(report["kind"], "catalogue-refresh")
        self.assertEqual(report["providerIds"], ["first"])
        self.assertEqual(report["catalogueOfferCount"], 1)
        self.assertEqual(report["quarantinedCandidateCount"], 0)
        self.assertEqual(calls, ["first", "first"])


class FailingAdapter:
    def __init__(self, provider_id: str, calls: list[str]) -> None:
        self.provider_id = provider_id
        self._calls = calls

    def collect(self) -> list[CatalogueCandidate]:
        self._calls.append(self.provider_id)
        raise OSError("fixture source failed")


def provider(provider_id: str) -> dict[str, str]:
    return {
        "id": provider_id,
        "name": provider_id.title(),
        "url": f"https://{provider_id}.example/",
        "status": "active",
    }


def write_registry(workspace: Path, providers: list[dict[str, str]]) -> None:
    path = workspace / "config/provider-registry.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in providers),
        encoding="utf-8",
    )


def offer_for_provider(provider_id: str, identity: str) -> dict[str, Any]:
    dataset = sample_dataset()
    offer = copy.deepcopy(cast(list[dict[str, Any]], dataset["offers"])[0])
    offer["providerId"] = provider_id
    offer["offerIdentity"] = identity
    offer["canonicalOfferUrl"] = f"https://{provider_id}.example/offers/one"
    return offer


def candidate_for_provider(
    provider_id: str,
    identity: str,
    *,
    include_offer: bool = True,
) -> CatalogueCandidate:
    evidence = {
        "sourceUrl": f"https://{provider_id}.example/offers/one",
        "wording": "Fixture evidence",
    }
    payload: dict[str, Any] = {
        "offerIdentity": identity,
        "providerId": provider_id,
        "canonicalSourceUrl": f"https://{provider_id}.example/offers/one",
        "admissionFacts": {
            "privateConsumerEligibility": {
                "state": "known",
                "value": True,
                "evidence": evidence,
            },
            "privateConsumerAmountAdmissibility": {
                "state": "known",
                "value": True,
                "evidence": evidence,
            },
            "passengerCarScope": {
                "state": "known",
                "value": True,
                "evidence": evidence,
            },
            "currentAvailability": {
                "state": "known",
                "value": True,
                "evidence": evidence,
            },
            "supportedLeasingForm": {
                "state": "known",
                "value": "operational",
                "evidence": evidence,
            },
        },
    }
    if include_offer:
        payload["offer"] = offer_for_provider(provider_id, identity)
    return CatalogueCandidate.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
