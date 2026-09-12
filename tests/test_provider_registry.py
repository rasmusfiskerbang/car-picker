from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from car_picker import (
    ActiveProvider,
    InactiveProvider,
    ProviderRegistry,
    ProviderRecordInvalid,
    RegistryInvalid,
)


class ProviderRegistryTest(unittest.TestCase):
    def test_open_returns_ordered_typed_publication_safe_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "provider-registry.jsonl"
            registry_path.write_text(
                "\n".join(
                    json.dumps(record)
                    for record in (
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
                            "status": "inactive",
                            "reason": "blocked",
                            "explanation": "Owner paused retrieval pending source review.",
                        },
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            snapshot = ProviderRegistry.open(registry_path).snapshot()

        self.assertEqual(
            [provider.id for provider in snapshot.providers],
            ["fleasing", "terminalen"],
        )
        self.assertIsInstance(snapshot.providers[0], ActiveProvider)
        inactive_provider = snapshot.providers[1]
        self.assertIsInstance(inactive_provider, InactiveProvider)
        assert isinstance(inactive_provider, InactiveProvider)
        self.assertEqual(inactive_provider.reason, "blocked")
        self.assertEqual(
            snapshot.model_dump(mode="json"),
            {
                "providers": [
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
                        "status": "inactive",
                        "reason": "blocked",
                        "explanation": "Owner paused retrieval pending source review.",
                    },
                ]
            },
        )

    def test_open_rejects_duplicate_ids_and_non_union_fields(self) -> None:
        invalid_records = (
            (
                {
                    "id": "same",
                    "name": "One",
                    "url": "https://one.example/",
                    "status": "active",
                },
                {
                    "id": "same",
                    "name": "Two",
                    "url": "https://two.example/",
                    "status": "active",
                },
            ),
            (
                {
                    "id": "inactive-without-reason",
                    "name": "Provider",
                    "url": "https://provider.example/",
                    "status": "inactive",
                    "explanation": "Missing the required reason.",
                },
            ),
            (
                {
                    "id": "active-with-reason",
                    "name": "Provider",
                    "url": "https://provider.example/",
                    "status": "active",
                    "reason": "blocked",
                    "explanation": "Active records cannot carry inactive fields.",
                },
            ),
        )

        for records in invalid_records:
            with (
                self.subTest(records=records),
                tempfile.TemporaryDirectory() as temporary_directory,
            ):
                registry_path = Path(temporary_directory) / "provider-registry.jsonl"
                registry_path.write_text(
                    "\n".join(json.dumps(record) for record in records) + "\n",
                    encoding="utf-8",
                )

                with self.assertRaises(RegistryInvalid):
                    ProviderRegistry.open(registry_path)

    def test_open_rejects_invalid_utf8_as_a_registry_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "provider-registry.jsonl"
            registry_path.write_bytes(b"{\xff\n")

            with self.assertRaises(RegistryInvalid):
                ProviderRegistry.open(registry_path)

    def test_put_atomically_replaces_one_record_and_rejects_invalid_update(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            registry_path = Path(temporary_directory) / "provider-registry.jsonl"
            registry_path.write_text(
                '{"id":"fleasing","name":"Fleasing","url":"https://fleasing.dk/","status":"active"}\n'
                '{"id":"terminalen","name":"Terminalen","url":"https://www.terminalen.dk/","status":"active"}\n',
                encoding="utf-8",
            )
            registry = ProviderRegistry.open(registry_path)

            updated_snapshot = registry.put(
                InactiveProvider(
                    id="terminalen",
                    name="Terminalen",
                    url="https://www.terminalen.dk/",
                    status="inactive",
                    reason="blocked",
                    explanation="Owner paused retrieval pending source review.",
                )
            )
            updated_bytes = registry_path.read_bytes()

            self.assertEqual(
                [provider.status for provider in updated_snapshot.providers],
                ["active", "inactive"],
            )
            self.assertEqual(updated_snapshot.providers[1].id, "terminalen")

            with self.assertRaises(ProviderRecordInvalid):
                registry.put(
                    {
                        "id": "terminalen",
                        "name": "Terminalen",
                        "url": "https://www.terminalen.dk/",
                        "status": "inactive",
                        "reason": "not-a-supported-reason",
                        "explanation": "This must be rejected before persistence.",
                    }
                )

            with self.assertRaises(ProviderRecordInvalid):
                registry.put(
                    ActiveProvider(
                        id="unsupported-provider",
                        name="Unsupported Provider",
                        url="https://unsupported.example/",
                        status="active",
                    )
                )

            self.assertEqual(registry_path.read_bytes(), updated_bytes)

    def test_cli_inspects_registry_in_human_readable_form(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            registry_path = workspace / "config/provider-registry.jsonl"
            registry_path.parent.mkdir()
            registry_path.write_text(
                '{"id":"fleasing","name":"Fleasing","url":"https://fleasing.dk/","status":"active"}\n'
                '{"id":"terminalen","name":"Terminalen","url":"https://www.terminalen.dk/","status":"active"}\n',
                encoding="utf-8",
            )

            result = run_cli(
                "--workspace",
                str(workspace),
                "provider",
                "inspect",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ID", result.stdout)
        self.assertIn("Fleasing", result.stdout)
        self.assertIn("Terminalen", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_cli_sets_json_record_without_mutating_catalogue_or_site(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            registry_path = workspace / "config/provider-registry.jsonl"
            registry_path.parent.mkdir()
            registry_path.write_text(
                '{"id":"fleasing","name":"Fleasing","url":"https://fleasing.dk/","status":"active"}\n'
                '{"id":"terminalen","name":"Terminalen","url":"https://www.terminalen.dk/","status":"active"}\n',
                encoding="utf-8",
            )
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_bytes = b"active catalogue generation"
            dataset_path.write_bytes(dataset_bytes)
            site_path = workspace / "var/site"
            site_path.mkdir()
            site_bytes = b"completed catalogue site"
            (site_path / "index.html").write_bytes(site_bytes)

            result = run_cli(
                "--workspace",
                str(workspace),
                "--json",
                "provider",
                "set",
                "terminalen",
                "inactive",
                "--reason",
                "blocked",
                "--explanation",
                "Owner paused retrieval pending source review.",
            )

            report = json.loads(result.stdout)
            dataset_after = dataset_path.read_bytes()
            site_after = (site_path / "index.html").read_bytes()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(report["kind"], "provider")
        self.assertEqual(report["record"]["id"], "terminalen")
        self.assertEqual(report["record"]["status"], "inactive")
        self.assertEqual(report["record"]["reason"], "blocked")
        self.assertFalse(report["catalogueDatasetChanged"])
        self.assertEqual(dataset_after, dataset_bytes)
        self.assertEqual(site_after, site_bytes)

    def test_cli_sets_human_record_and_names_the_unchanged_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            registry_path = workspace / "config/provider-registry.jsonl"
            registry_path.parent.mkdir()
            registry_path.write_text(
                '{"id":"terminalen","name":"Terminalen","url":"https://www.terminalen.dk/","status":"active"}\n',
                encoding="utf-8",
            )

            result = run_cli(
                "--workspace",
                str(workspace),
                "provider",
                "set",
                "terminalen",
                "inactive",
                "--reason",
                "deferred",
                "--explanation",
                "Source review is deferred.",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Provider terminalen is now inactive (deferred).", result.stdout)
        self.assertIn("Active Catalogue Dataset was not changed.", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_cli_rejected_update_has_stable_json_diagnostic_and_preserves_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            registry_path = workspace / "config/provider-registry.jsonl"
            registry_path.parent.mkdir()
            registry_path.write_text(
                '{"id":"terminalen","name":"Terminalen","url":"https://www.terminalen.dk/","status":"active"}\n',
                encoding="utf-8",
            )
            prior_bytes = registry_path.read_bytes()

            result = run_cli(
                "--workspace",
                str(workspace),
                "--json",
                "provider",
                "set",
                "terminalen",
                "inactive",
                "--reason",
                "blocked",
                "--explanation",
                " ",
            )

            diagnostic = json.loads(result.stderr)
            current_bytes = registry_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(diagnostic["error"]["code"], "provider.record_invalid")
        self.assertTrue(diagnostic["safeState"]["unchanged"])
        self.assertEqual(current_bytes, prior_bytes)
        self.assertNotIn("traceback", result.stderr.lower())


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "car_picker", *arguments],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
