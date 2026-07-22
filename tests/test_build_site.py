from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class BuildSiteTest(unittest.TestCase):
    def test_build_site_projects_one_evidence_backed_catalogue_offer(self) -> None:
        """The public CLI builds the one-offer catalogue shown to a prospective lessee."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_path = Path(temporary_directory) / "site"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--output",
                    str(site_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((site_path / "index.html").is_file())
            self.assertTrue((site_path / "app.js").is_file())
            self.assertTrue((site_path / "styles.css").is_file())
            projection = json.loads((site_path / "projection.json").read_text(encoding="utf-8"))

        self.assertEqual(projection["schemaVersion"], "catalogue-presentation/v1")
        self.assertEqual(projection["offers"], [
            {
                "offerIdentity": "terminalen:ioniq-5:essential-84",
                "provider": "Terminalen",
                "vehicleSpecification": {
                    "state": "known",
                    "value": "Hyundai IONIQ 5 Essential 84 kWh",
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Hyundai IONIQ 5 Essential 84 kWh.",
                    },
                },
                "supportedLeasingForm": {
                    "state": "known",
                    "value": "operational",
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Privatleasing med aflevering ved udløb.",
                    },
                },
                "advertisedMonthlyPayment": {
                    "state": "known",
                    "valueDkk": 3795,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Månedlig ydelse 3.795 kr.",
                    },
                },
                "upfrontCashRequirement": {
                    "state": "known",
                    "valueDkk": 15990,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Førstegangsydelse 15.990 kr.",
                    },
                },
                "nominalBaseOutlay": {
                    "state": "known",
                    "valueDkk": 152610,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "36 betalinger og førstegangsydelse.",
                    },
                },
                "nominalMonthlyEquivalent": {
                    "state": "known",
                    "valueDkk": 4239,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "152.610 kr. fordelt over 36 måneder.",
                    },
                },
                "termMonths": {
                    "state": "known",
                    "value": 36,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Løbetid 36 måneder.",
                    },
                },
                "annualMileageKm": {
                    "state": "known",
                    "value": 10000,
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "10.000 km om året.",
                    },
                },
                "normalEndMechanism": {
                    "state": "known",
                    "value": "Bilen afleveres ved normal udløb.",
                    "evidence": {
                        "sourceUrl": "https://example.test/ioniq-5",
                        "wording": "Bilen afleveres ved leasingperiodens udløb.",
                    },
                },
            }
        ])

    def test_build_site_refuses_an_output_outside_the_ignored_site_boundary(self) -> None:
        """The CLI keeps generated site artifacts in an ignored `site` directory."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "dist"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "car_picker",
                    "build-site",
                    "--dataset",
                    str(FIXTURE_DATASET),
                    "--output",
                    str(output_path),
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must name a site directory", result.stderr)

    def test_build_site_withholds_quarantined_candidates_from_the_active_catalogue(self) -> None:
        """A quarantined offer remains in the dataset but cannot enter the static catalogue."""
        dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
        quarantined_offer = dataset["catalogueOffers"][0].copy()
        quarantined_offer["offerIdentity"] = "terminalen:ioniq-5:quarantined"
        quarantined_offer["admissionStatus"] = "quarantined"
        dataset["catalogueOffers"].append(quarantined_offer)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            result = subprocess.run(
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
        self.assertEqual(
            [offer["offerIdentity"] for offer in projection["offers"]],
            ["terminalen:ioniq-5:essential-84"],
        )


if __name__ == "__main__":
    unittest.main()
