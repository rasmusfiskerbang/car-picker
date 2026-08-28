from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from pydantic import ValidationError

from car_picker import (
    Catalogue,
    CatalogueCandidate,
    CatalogueOffer,
    KnownCandidateFact,
)
from car_picker.collection import FleasingProviderAdapter, TerminalenProviderAdapter

from tests.test_catalogue_contract import sample_dataset


class RawOutcomeAdapter:
    provider_id = "first"

    def __init__(self, record: object) -> None:
        self._record = record

    def collect(self) -> list[Any]:
        return [self._record]


class NoopHttpClient:
    def get_text(self, url: str) -> str:
        raise AssertionError(f"unexpected source request: {url}")


class CatalogueRefreshContractTest(unittest.TestCase):
    def test_catalogue_rejects_mapping_adapter_construction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TypeError):
                Catalogue(
                    Path(directory),
                    adapters=cast(Any, {"first": RawOutcomeAdapter({})}),
                )

    def test_production_adapter_ingress_returns_only_normalized_candidates(
        self,
    ) -> None:
        raw = fleasing_boundary_record()

        with patch(
            "car_picker.collection.FleasingAdapter.collect",
            return_value=[raw],
        ):
            candidates = FleasingProviderAdapter(
                NoopHttpClient(), "2026-08-16T12:00:00Z"
            ).collect()

        self.assertEqual(len(candidates), 1)
        self.assertIsInstance(candidates[0], CatalogueCandidate)
        self.assertEqual(candidates[0].provider_id, "fleasing")
        fact = candidates[0].admission_facts.private_consumer_eligibility
        assert isinstance(fact, KnownCandidateFact)
        self.assertEqual(fact.value, True)

    def test_terminalen_production_adapter_ingress_rejects_unvalidated_records(
        self,
    ) -> None:
        raw = {
            "offerIdentity": "terminalen:car:fixture",
            "canonicalOfferUrl": "https://terminalen.example/offers/fixture?configuration=1",
            "privateConsumerEligibility": known_fact(True),
            "privateConsumerAmountAdmissibility": known_fact(True),
            "passengerCarScope": known_fact(True),
            "currentAvailability": known_fact(True),
            "supportedLeasingForm": known_fact("operational"),
        }

        with (
            patch(
                "car_picker.collection.TerminalenAdapter.collect",
                return_value=[raw],
            ),
            self.assertRaises(ValidationError),
        ):
            TerminalenProviderAdapter(
                NoopHttpClient(), "2026-08-16T12:00:00Z"
            ).collect()

    def test_refresh_rejects_raw_or_direct_outcome_records(self) -> None:
        raw_offer = offer_for_provider("first", "first:car:raw")
        raw_offer["admissionOutcome"] = "admitted"

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[RawOutcomeAdapter(raw_offer)],
            )

            with self.assertRaisesRegex(ValueError, "Provider first collection failed"):
                catalogue.refresh()

    def test_refresh_rejects_a_direct_catalogue_offer_record(self) -> None:
        direct_offer = CatalogueOffer.model_validate(
            offer_for_provider("first", "first:car:direct")
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[RawOutcomeAdapter(direct_offer)],
            )

            with self.assertRaisesRegex(ValueError, "Provider first collection failed"):
                catalogue.refresh()

    def test_candidate_requires_every_provider_independent_admission_fact(self) -> None:
        payload = {
            "offerIdentity": "first:car:incomplete",
            "providerId": "first",
            "canonicalSourceUrl": "https://first.example/offers/incomplete",
            "admissionFacts": complete_admission_facts(),
            "offer": offer_for_provider("first", "first:car:incomplete"),
        }
        del payload["admissionFacts"]["currentAvailability"]

        with self.assertRaises(ValidationError):
            CatalogueCandidate.model_validate(payload)

    def test_candidate_rejects_nested_offer_identity_mismatch(self) -> None:
        payload = {
            "offerIdentity": "first:car:candidate",
            "providerId": "first",
            "canonicalSourceUrl": "https://first.example/offers/candidate",
            "admissionFacts": complete_admission_facts(),
            "offer": offer_for_provider("first", "first:car:nested"),
        }

        with self.assertRaises(ValidationError):
            CatalogueCandidate.model_validate(payload)

    def test_candidate_rejects_nested_offer_provider_mismatch(self) -> None:
        payload = {
            "offerIdentity": "first:car:provider",
            "providerId": "first",
            "canonicalSourceUrl": "https://first.example/offers/provider",
            "admissionFacts": complete_admission_facts(),
            "offer": offer_for_provider("second", "first:car:provider"),
        }

        with self.assertRaises(ValidationError):
            CatalogueCandidate.model_validate(payload)

    def test_refresh_has_no_public_timestamp_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [])
            catalogue = Catalogue(workspace, adapters=[])

            with self.assertRaises(TypeError):
                cast(Any, catalogue.refresh)(
                    generated_at=lambda: "2026-08-16T12:00:00Z"
                )


def complete_admission_facts() -> dict[str, dict[str, object]]:
    evidence = {
        "sourceUrl": "https://first.example/offers/fixture",
        "wording": "Fixture evidence",
    }
    return {
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
    }


def known_fact(value: object) -> dict[str, object]:
    return {
        "state": "known",
        "value": value,
        "evidence": {
            "sourceUrl": "https://fleasing.example/offers/fixture?vid=1",
            "wording": "Fixture evidence",
        },
    }


def fleasing_boundary_record() -> dict[str, object]:
    evidence = {
        "sourceUrl": "https://fleasing.example/bil/?fixture&vid=1",
        "wording": "Fixture evidence",
    }
    unavailable = {"state": "not_stated", "evidence": evidence}
    return {
        "offerIdentity": "fleasing:car:fixture",
        "provider": "Fleasing",
        "providerSourceId": "1",
        "canonicalOfferUrl": "https://fleasing.example/bil/?fixture&vid=1",
        "sourceLocalConfigurationKey": "private-fixture",
        "vehicleSpecification": {
            "state": "known",
            "value": {
                "make": "Fixture",
                "model": "Car",
                "trim": "Trim",
                "drivetrain": "gasoline",
            },
            "evidence": evidence,
        },
        "imageUrls": [],
        "configurationIdentityFailures": [],
        "upfrontPayment": {
            "state": "known",
            "valueDkk": 100,
            "evidence": evidence,
        },
        "privateConsumerEligibility": known_fact(True),
        "privateConsumerAmountAdmissibility": known_fact(True),
        "passengerCarScope": known_fact(True),
        "currentAvailability": known_fact(True),
        "supportedLeasingForm": known_fact("operational"),
        "advertisedMonthlyPayment": {
            "state": "known",
            "valueDkk": 10,
            "evidence": evidence,
        },
        "termMonths": known_fact(1),
        "baseCashFlowStream": [
            {
                "meaning": "Udbetaling",
                "direction": "payment",
                "amountDkk": 100,
                "amountBasis": "including_vat",
                "timing": "acceptance_to_handover",
                "recurrenceCount": 1,
                "refundability": "not_refundable",
                "includedInBase": True,
                "evidence": evidence,
            },
            {
                "meaning": "Ydelse pr. måned",
                "direction": "payment",
                "amountDkk": 10,
                "amountBasis": "including_vat",
                "timing": "recurring",
                "recurrenceCount": 1,
                "refundability": "not_refundable",
                "includedInBase": True,
                "evidence": evidence,
            },
        ],
        "baseCashFlowBlockers": None,
        "annualMileageKm": unavailable,
        "normalEndMechanism": unavailable,
        "residualRiskAllocation": unavailable,
        "registrationTaxTreatment": unavailable,
        "serviceArrangements": unavailable,
        "exclusions": unavailable,
        "exposureScenarios": unavailable,
        "sourceMetadata": {
            "parserVersion": "fleasing-html-test",
            "documents": [
                {
                    "sourceUrl": "https://fleasing.example/bil/?fixture&vid=1",
                    "contentSha256": "0" * 64,
                    "retrievedAt": "2026-08-16T12:00:00Z",
                }
            ],
        },
    }


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
    offer = copy.deepcopy(cast(dict[str, Any], sample_dataset())["offers"][0])
    assert isinstance(offer, dict)
    offer["providerId"] = provider_id
    offer["offerIdentity"] = identity
    offer["canonicalOfferUrl"] = f"https://{provider_id}.example/offers/one"
    return offer


if __name__ == "__main__":
    unittest.main()
