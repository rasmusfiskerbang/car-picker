from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from car_picker.catalogue_model import (
    CatalogueDataset,
    catalogue_dataset_json_schema,
    from_legacy_dataset,
    to_legacy_dataset,
)


FIXTURE = Path(__file__).parent / "fixtures/one-offer-catalogue-dataset.json"


class CatalogueModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy_dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_compatibility_boundary_round_trips_the_existing_fixture(self) -> None:
        canonical = from_legacy_dataset(self.legacy_dataset)

        self.assertEqual(len(canonical.catalogue_offers), 1)
        self.assertEqual(canonical.quarantined_offers, [])
        self.assertEqual(to_legacy_dataset(canonical), self.legacy_dataset)

    def test_serialization_schema_is_generated_from_the_authoritative_model(self) -> None:
        schema = catalogue_dataset_json_schema()

        self.assertEqual(schema["properties"]["schemaVersion"]["const"], "catalogue-dataset/v1")
        self.assertIn("catalogueOffers", schema["properties"])
        self.assertIn("quarantinedOffers", schema["properties"])
        self.assertNotIn("admissionStatus", schema["$defs"]["CatalogueOffer"]["properties"])
        self.assertEqual(
            schema["$defs"]["CatalogueOffer"]["properties"]["admissionOutcome"]["const"],
            "admitted",
        )
        self.assertIn("ServiceArrangement", schema["$defs"])
        self.assertIn("ExposureScenario", schema["$defs"])

    def test_rejects_an_invalid_fact_state(self) -> None:
        invalid = copy.deepcopy(self.legacy_dataset)
        invalid["catalogueOffers"][0]["termMonths"]["state"] = "missing"

        with self.assertRaises(ValidationError):
            from_legacy_dataset(invalid)

    def test_rejects_an_admitted_offer_that_has_quarantine_reasons(self) -> None:
        invalid = copy.deepcopy(self.legacy_dataset)
        invalid["catalogueOffers"][0]["quarantineReasons"] = [
            {"code": "unsupported", "fact": "supportedLeasingForm"}
        ]

        with self.assertRaises(ValidationError):
            from_legacy_dataset(invalid)

    def test_rejects_an_invalid_admission_outcome(self) -> None:
        invalid = copy.deepcopy(self.legacy_dataset)
        invalid["catalogueOffers"][0]["admissionStatus"] = "pending"

        with self.assertRaises(ValidationError):
            from_legacy_dataset(invalid)

    def test_rejects_duplicate_or_malformed_offer_identities(self) -> None:
        duplicate = copy.deepcopy(self.legacy_dataset)
        duplicate["catalogueOffers"].append(copy.deepcopy(duplicate["catalogueOffers"][0]))

        with self.assertRaises(ValidationError):
            from_legacy_dataset(duplicate)

        malformed = copy.deepcopy(self.legacy_dataset)
        malformed["catalogueOffers"][0]["offerIdentity"] = "not namespaced"
        with self.assertRaises(ValidationError):
            from_legacy_dataset(malformed)

    def test_rejects_provider_coverage_that_disagrees_with_offers(self) -> None:
        invalid = copy.deepcopy(self.legacy_dataset)
        invalid["coverage"]["providers"][0]["name"] = "Fleasing"

        with self.assertRaises(ValidationError):
            from_legacy_dataset(invalid)

    def test_rejects_incomplete_dataset_replacement_inputs(self) -> None:
        incomplete = copy.deepcopy(self.legacy_dataset)
        del incomplete["catalogueOffers"][0]["sourceMetadata"]

        with self.assertRaises(ValidationError):
            from_legacy_dataset(incomplete)

        canonical = from_legacy_dataset(self.legacy_dataset).model_dump(
            mode="json",
            by_alias=True,
        )
        canonical["catalogueOffers"][0]["baseCashFlowStream"][0] = {
            "meaning": "Incomplete payment"
        }
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(canonical)

    def test_quarantined_candidates_are_not_catalogue_offers(self) -> None:
        legacy = copy.deepcopy(self.legacy_dataset)
        candidate = legacy["catalogueOffers"][0]
        candidate["admissionStatus"] = "quarantined"
        candidate["quarantineReasons"] = [
            {
                "code": "admission_fact_not_known",
                "fact": "supportedLeasingForm",
                "state": "unclear",
            }
        ]
        candidate["supportedLeasingForm"] = {
            "state": "unclear",
            "evidence": {
                "sourceUrl": "https://example.test/ioniq-5",
                "wording": "Leasingform fremgår ikke entydigt.",
            },
        }
        legacy["coverage"]["providers"][0]["quarantinedCandidateCount"] = 1

        canonical = from_legacy_dataset(legacy)

        self.assertEqual(canonical.catalogue_offers, [])
        self.assertEqual(len(canonical.quarantined_offers), 1)
        self.assertEqual(to_legacy_dataset(canonical), legacy)


if __name__ == "__main__":
    unittest.main()
