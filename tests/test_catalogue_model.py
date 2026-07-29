from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from car_picker.catalogue_model import (
    CatalogueDataset,
    catalogue_dataset_json_schema,
)


FIXTURE = Path(__file__).parent / "fixtures/one-offer-catalogue-dataset.json"


class CatalogueModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_authoritative_model_parses_the_canonical_fixture(self) -> None:
        canonical = CatalogueDataset.model_validate(self.dataset)

        self.assertEqual(len(canonical.catalogue_offers), 1)
        self.assertEqual(canonical.quarantined_candidates, [])

    def test_serialization_schema_is_generated_from_the_authoritative_model(
        self,
    ) -> None:
        schema = catalogue_dataset_json_schema()

        self.assertEqual(
            schema["properties"]["schemaVersion"]["const"], "catalogue-dataset/v1"
        )
        self.assertIn("catalogueOffers", schema["properties"])
        self.assertIn("quarantinedCandidates", schema["properties"])
        self.assertNotIn(
            "admissionStatus", schema["$defs"]["CatalogueOffer"]["properties"]
        )
        self.assertEqual(
            schema["$defs"]["CatalogueOffer"]["properties"]["admissionOutcome"][
                "const"
            ],
            "admitted",
        )
        self.assertIn("ServiceArrangement", schema["$defs"])
        self.assertIn("ExposureScenario", schema["$defs"])

    def test_rejects_an_invalid_fact_state(self) -> None:
        invalid = copy.deepcopy(self.dataset)
        invalid["catalogueOffers"][0]["termMonths"]["state"] = "missing"

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_rejects_an_admitted_offer_that_has_quarantine_reasons(self) -> None:
        invalid = copy.deepcopy(self.dataset)
        invalid["catalogueOffers"][0]["quarantineReasons"] = [
            {"code": "unsupported", "fact": "supportedLeasingForm"}
        ]

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_rejects_an_invalid_admission_outcome(self) -> None:
        invalid = copy.deepcopy(self.dataset)
        invalid["catalogueOffers"][0]["admissionOutcome"] = "pending"

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_rejects_duplicate_or_malformed_offer_identities(self) -> None:
        duplicate = copy.deepcopy(self.dataset)
        duplicate["catalogueOffers"].append(
            copy.deepcopy(duplicate["catalogueOffers"][0])
        )

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(duplicate)

        malformed = copy.deepcopy(self.dataset)
        malformed["catalogueOffers"][0]["offerIdentity"] = "not namespaced"
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(malformed)

    def test_rejects_provider_coverage_that_disagrees_with_offers(self) -> None:
        invalid = copy.deepcopy(self.dataset)
        invalid["coverage"]["providers"][0]["name"] = "Fleasing"

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_rejects_a_provider_outside_the_declared_source_scope(self) -> None:
        invalid = copy.deepcopy(self.dataset)
        invalid["coverage"]["providers"][0]["name"] = "Unknown"
        invalid["catalogueOffers"][0]["provider"] = "Unknown"

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(invalid)

    def test_rejects_incomplete_dataset_replacement_inputs(self) -> None:
        incomplete = copy.deepcopy(self.dataset)
        del incomplete["catalogueOffers"][0]["sourceMetadata"]

        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(incomplete)

        canonical = CatalogueDataset.model_validate(self.dataset).model_dump(
            mode="json",
            by_alias=True,
        )
        canonical["catalogueOffers"][0]["baseCashFlowStream"][0] = {
            "meaning": "Incomplete payment"
        }
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(canonical)

    def test_quarantined_candidates_are_not_catalogue_offers(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        candidate = dataset["catalogueOffers"].pop()
        candidate["admissionOutcome"] = "quarantined"
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
        dataset["quarantinedCandidates"].append(candidate)
        dataset["coverage"]["providers"][0]["quarantinedCandidateCount"] = 1

        canonical = CatalogueDataset.model_validate(dataset)

        self.assertEqual(canonical.catalogue_offers, [])
        self.assertEqual(len(canonical.quarantined_candidates), 1)


if __name__ == "__main__":
    unittest.main()
