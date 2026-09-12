from __future__ import annotations

import json
import copy
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from car_picker import CatalogueDataset, catalogue_dataset_json_schema
from tests.site_helpers import build_site

from tests.test_catalogue_contract import sample_dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/browser-catalogue-dataset.json"
INVALID_CASES = REPOSITORY_ROOT / "tests/fixtures/browser-catalogue-invalid-cases.json"


class BrowserCatalogueContractTest(unittest.TestCase):
    def test_serialization_schema_exposes_browser_visible_timestamp_and_https_rules(
        self,
    ) -> None:
        schema = catalogue_dataset_json_schema()

        generated_at = schema["properties"]["generatedAt"]
        self.assertRegex(generated_at["pattern"], r"\\d\{4\}")
        self.assertEqual(generated_at["minLength"], 20)
        self.assertEqual(generated_at["maxLength"], 20)
        self.assertEqual(generated_at["format"], "date-time")

        provider_url = schema["$defs"]["ActiveProvider"]["properties"]["url"]
        offer_url = schema["$defs"]["CatalogueOffer"]["properties"]["canonicalOfferUrl"]
        self.assertIn("^https://", provider_url["pattern"])
        self.assertIn("^https://", offer_url["pattern"])
        self.assertIsNone(
            re.fullmatch(provider_url["pattern"], "https://user@example.test/")
        )

    def test_shared_browser_fixture_has_matching_python_acceptance_and_rejection(
        self,
    ) -> None:
        dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
        parsed = CatalogueDataset.model_validate(dataset)
        self.assertEqual(
            parsed.model_dump(mode="json", by_alias=True),
            dataset,
        )

        incompatible = copy.deepcopy(dataset)
        incompatible["schemaVersion"] = "catalogue-dataset/v2"
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(incompatible)

        partial = copy.deepcopy(dataset)
        del partial["offers"]
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(partial)

        unknown = copy.deepcopy(dataset)
        unknown["offers"][0]["unexpected"] = True
        with self.assertRaises(ValidationError):
            CatalogueDataset.model_validate(unknown)

    def test_shared_invalid_constraint_cases_are_rejected_by_python(self) -> None:
        dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
        invalid_cases = json.loads(INVALID_CASES.read_text(encoding="utf-8"))

        for case_name, field_value in invalid_cases.items():
            with self.subTest(case_name=case_name):
                invalid = copy.deepcopy(dataset)
                if case_name == "invalidGeneratedAt":
                    invalid["generatedAt"] = field_value
                elif case_name == "invalidGeneratedAtCalendarDate":
                    invalid["generatedAt"] = field_value
                elif case_name == "invalidProviderUrl":
                    invalid["providers"][0]["url"] = field_value
                elif case_name == "invalidProviderCredentialsUrl":
                    invalid["providers"][0]["url"] = field_value
                else:
                    invalid["offers"][0]["canonicalOfferUrl"] = field_value
                with self.assertRaises(ValidationError):
                    CatalogueDataset.model_validate(invalid)

    def test_site_build_rejects_the_superseded_dataset_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            legacy_fixture = Path(temporary_directory) / "superseded-dataset.json"
            legacy_fixture.write_text(
                json.dumps(
                    {
                        "schemaVersion": "catalogue-dataset/v0",
                        "coverage": [],
                        "catalogueOffers": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                build_site(legacy_fixture, Path(temporary_directory) / "var/site")

    def test_site_packages_the_exact_serialized_dataset_and_schema(self) -> None:
        dataset = sample_dataset()
        serialized = CatalogueDataset.model_validate(dataset).model_dump(
            mode="json", by_alias=True
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_path = Path(temporary_directory) / "catalogue-dataset.json"
            site_path = Path(temporary_directory) / "var/site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

            with patch.dict(
                os.environ,
                {"CAR_PICKER_PYTHON": "/path/that/must/not/be_used"},
            ):
                build_site(dataset_path, site_path)

            packaged_dataset = json.loads(
                (site_path / "catalogue-dataset.json").read_text(encoding="utf-8")
            )
            packaged_schema = json.loads(
                (site_path / "catalogue-dataset-schema.json").read_text(
                    encoding="utf-8"
                )
            )
            packaged_files = {path.name for path in site_path.iterdir()}

        self.assertEqual(packaged_dataset, serialized)
        self.assertEqual(packaged_schema, catalogue_dataset_json_schema())
        self.assertNotIn("projection.json", packaged_files)


if __name__ == "__main__":
    unittest.main()
