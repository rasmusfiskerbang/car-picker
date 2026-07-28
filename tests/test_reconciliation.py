from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATASET = REPOSITORY_ROOT / "tests/fixtures/one-offer-catalogue-dataset.json"


class ProviderAggregateReconciliationTest(unittest.TestCase):
    def test_public_diagnostics_and_site_distinguish_matching_tolerated_and_mismatched_aggregates(
        self,
    ) -> None:
        dataset = aggregate_dataset()

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            dataset_path = temporary_path / "catalogue-dataset.json"
            site_path = temporary_path / "site"
            dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
            all_result = run_cli("diagnose-aggregates", "--dataset", str(dataset_path))
            one_result = run_cli(
                "diagnose-aggregates",
                "--dataset",
                str(dataset_path),
                "--offer",
                "terminalen:ioniq-5:mismatch",
            )
            build_result = run_cli(
                "build-site", "--dataset", str(dataset_path), "--output", str(site_path)
            )
            projection = json.loads(
                (site_path / "projection.json").read_text(encoding="utf-8")
            )

        self.assertEqual(all_result.returncode, 0, all_result.stderr)
        diagnostics = json.loads(all_result.stdout)
        self.assertEqual(
            [
                (row["offerIdentity"], row["status"], row["differenceDkk"])
                for row in diagnostics["offers"]
            ],
            [
                ("terminalen:ioniq-5:matching", "matching", 0),
                (
                    "terminalen:ioniq-5:tolerated",
                    "within_ordinary_rounding_tolerance",
                    1,
                ),
                ("terminalen:ioniq-5:mismatch", "mismatch", 2),
            ],
        )
        mismatch = diagnostics["offers"][2]
        self.assertEqual(mismatch["toleranceDkk"], 1)
        self.assertEqual(mismatch["providerAdvertisedAggregate"]["valueDkk"], 24002)
        self.assertEqual(mismatch["reconstructedNominalBaseOutlayDkk"], 24000)
        self.assertEqual(
            [event["meaning"] for event in mismatch["reconstructedEvents"]],
            ["Førstegangsydelse", "Månedlig ydelse"],
        )
        self.assertEqual(mismatch["recurrenceCounts"], [1, 12])
        self.assertEqual(mismatch["vatBases"], ["including_vat"])
        self.assertEqual(len(mismatch["evidenceReferences"]), 3)
        self.assertTrue(mismatch["investigationPrompts"])
        self.assertEqual(one_result.returncode, 0, one_result.stderr)
        self.assertEqual(
            [row["offerIdentity"] for row in json.loads(one_result.stdout)["offers"]],
            ["terminalen:ioniq-5:mismatch"],
        )
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        self.assertEqual(
            projection["offers"][0]["nominalBaseOutlay"]["valueDkk"], 24000
        )
        self.assertEqual(
            projection["offers"][1]["nominalMonthlyEquivalent"]["valueDkk"], 2000
        )
        self.assertEqual(
            projection["offers"][2]["nominalBaseOutlay"]["blockingFacts"],
            ["providerAdvertisedAggregateMismatch"],
        )
        self.assertEqual(
            projection["offers"][2]["nominalMonthlyEquivalent"]["blockingFacts"],
            ["providerAdvertisedAggregateMismatch"],
        )


def aggregate_dataset() -> dict[str, object]:
    dataset = json.loads(FIXTURE_DATASET.read_text(encoding="utf-8"))
    original = dataset["catalogueOffers"][0]
    offers = []
    for suffix, aggregate in (
        ("matching", 24000),
        ("tolerated", 24001),
        ("mismatch", 24002),
    ):
        offer = json.loads(json.dumps(original))
        offer["offerIdentity"] = f"terminalen:ioniq-5:{suffix}"
        offer["termMonths"] = known_value(12, "Løbetid 12 måneder.")
        offer["baseCashFlowStream"] = [
            event("Førstegangsydelse", 12000, "acceptance_to_handover", 1),
            event("Månedlig ydelse", 1000, "recurring", 12),
        ]
        offer["providerAdvertisedAggregate"] = {
            "state": "known",
            "valueDkk": aggregate,
            "scope": "normal_completion_base_cash_flows",
            "evidence": {
                "sourceUrl": "https://example.test/ioniq-5",
                "wording": f"Samlet betaling {aggregate} kr.",
            },
        }
        offers.append(offer)
    dataset["catalogueOffers"] = offers
    return dataset


def known_value(value: int, wording: str) -> dict[str, object]:
    return {
        "state": "known",
        "value": value,
        "evidence": {"sourceUrl": "https://example.test/ioniq-5", "wording": wording},
    }


def event(
    meaning: str, amount_dkk: int, timing: str, recurrence_count: int
) -> dict[str, object]:
    return {
        "meaning": meaning,
        "direction": "payment",
        "amountDkk": amount_dkk,
        "amountBasis": "including_vat",
        "timing": timing,
        "recurrenceCount": recurrence_count,
        "refundability": "not_refundable",
        "includedInBase": True,
        "evidence": {
            "sourceUrl": "https://example.test/ioniq-5",
            "wording": f"{meaning}: {amount_dkk} kr.",
        },
    }


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
