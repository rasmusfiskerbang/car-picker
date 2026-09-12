from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import cast
from unittest.mock import patch

from car_picker import Catalogue, CatalogueCandidate, CatalogueRefreshError
from car_picker.__main__ import app
from car_picker.json_persistence import (
    write_json_atomically as real_write_json_atomically,
)
from typer.testing import CliRunner

from tests.test_catalogue_refresh import (
    candidate_for_provider,
    provider,
    write_registry,
)


class SpyAdapter:
    def __init__(
        self,
        provider_id: str,
        records: object = (),
        calls: list[str] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.provider_id = provider_id
        self._records = records
        self._calls = calls if calls is not None else []
        self._failure = failure

    def collect(self) -> Sequence[CatalogueCandidate]:
        self._calls.append(self.provider_id)
        if self._failure is not None:
            raise self._failure
        return cast(Sequence[CatalogueCandidate], copy.deepcopy(self._records))


class CatalogueRefreshFailClosedTest(unittest.TestCase):
    def test_invalid_workspace_fails_before_adapter_access(self) -> None:
        calls: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            workspace_path = Path(directory) / "workspace-file"
            workspace_path.write_text("not a workspace", encoding="utf-8")
            catalogue = Catalogue(
                workspace_path,
                adapters=[SpyAdapter("first", calls=calls)],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

        self.assertEqual(calls, [])
        self.assertEqual(raised.exception.category, "invalid-input")
        self.assertEqual(raised.exception.code, "catalogue.workspace_invalid")

    def test_invalid_registry_fails_before_adapter_access_and_preserves_dataset(
        self,
    ) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            registry_path = workspace / "config/provider-registry.jsonl"
            registry_path.parent.mkdir()
            registry_path.write_text(
                '{"id":"first","status":"active"}\n', encoding="utf-8"
            )
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[SpyAdapter("first", calls=calls)],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, [])
        self.assertEqual(raised.exception.category, "invalid-input")
        self.assertEqual(raised.exception.code, "catalogue.registry_invalid")

    def test_missing_active_adapter_fails_before_network_and_preserves_dataset(
        self,
    ) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first"), provider("second")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[SpyAdapter("first", calls=calls)],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, [])
        self.assertEqual(raised.exception.category, "invalid-input")
        self.assertEqual(raised.exception.code, "catalogue.adapter_coverage_invalid")

    def test_duplicate_static_adapter_fails_before_network(self) -> None:
        calls: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    SpyAdapter("first", calls=calls),
                    SpyAdapter("first", calls=calls),
                ],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

        self.assertEqual(calls, [])
        self.assertEqual(raised.exception.category, "invalid-input")
        self.assertEqual(raised.exception.code, "catalogue.adapter_invalid")

    def test_candidate_evidence_failure_is_quarantined_without_payload(self) -> None:
        payload = candidate_for_provider("first", "first:car:unclear")
        candidate_payload = payload.model_dump(mode="json", by_alias=True)
        candidate_payload["admissionFacts"]["currentAvailability"] = {
            "state": "unclear",
            "evidence": {
                "sourceUrl": "https://first.example/offers/unclear",
                "wording": "Tilgængelighed kunne ikke bekræftes.",
            },
        }
        candidate = CatalogueCandidate.model_validate(candidate_payload)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            catalogue = Catalogue(
                workspace,
                adapters=[SpyAdapter("first", [candidate])],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 1)
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].criterion,
            "current_availability",
        )
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].evidence[0].excerpt,
            "Tilgængelighed kunne ikke bekræftes.",
        )
        self.assertNotIn("admissionFacts", json.dumps(dataset.model_dump(mode="json")))

    def test_provider_retrieval_failure_aborts_and_preserves_bytes(self) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first"), provider("second")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[
                    SpyAdapter(
                        "first",
                        [candidate_for_provider("first", "first:car:one")],
                        calls,
                    ),
                    SpyAdapter(
                        "second",
                        calls=calls,
                        failure=OSError("https://secret.example/transport detail"),
                    ),
                ],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(raised.exception.category, "operational")
        self.assertEqual(raised.exception.code, "catalogue.provider_retrieval_failed")
        self.assertNotIn("secret.example", str(raised.exception))
        self.assertNotIn("transport detail", str(raised.exception))

    def test_invalid_enumeration_aborts_without_partial_publication(self) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[SpyAdapter("first", None, calls)],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, ["first"])
        self.assertEqual(raised.exception.category, "operational")
        self.assertEqual(raised.exception.code, "catalogue.provider_enumeration_failed")

    def test_structural_candidate_failure_aborts_without_partial_publication(
        self,
    ) -> None:
        calls: list[str] = []
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace,
                adapters=[SpyAdapter("first", [object()], calls)],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(calls, ["first"])
        self.assertEqual(raised.exception.category, "operational")
        self.assertEqual(raised.exception.code, "catalogue.provider_structural_failure")

    def test_final_validation_failure_happens_before_dataset_replace(self) -> None:
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
        candidate = candidate_for_provider("first", "first:car:one")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace, adapters=[SpyAdapter("first", [candidate])]
            )

            with patch(
                "car_picker.catalogue.CatalogueDataset.model_validate",
                side_effect=ValueError("unexpected source payload"),
            ):
                with self.assertRaises(CatalogueRefreshError) as raised:
                    catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(raised.exception.category, "operational")
        self.assertEqual(raised.exception.code, "catalogue.final_validation_failed")
        self.assertNotIn("unexpected source payload", str(raised.exception))

    def test_atomic_replace_failure_preserves_previous_dataset(self) -> None:
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
        candidate = candidate_for_provider("first", "first:car:one")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace, adapters=[SpyAdapter("first", [candidate])]
            )

            with patch(
                "car_picker.catalogue.write_json_atomically",
                side_effect=OSError("disk detail for https://secret.example"),
            ):
                with self.assertRaises(CatalogueRefreshError) as raised:
                    catalogue.refresh()

            self.assertEqual(dataset_path.read_bytes(), prior)

        self.assertEqual(raised.exception.category, "operational")
        self.assertEqual(raised.exception.code, "catalogue.dataset_replace_failed")
        self.assertNotIn("secret.example", str(raised.exception))

    def test_post_replace_writer_failure_reports_committed_dataset(self) -> None:
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'
        candidate = candidate_for_provider("first", "first:car:one")

        def replace_then_raise(path: Path, value: object) -> None:
            real_write_json_atomically(path, value)
            raise OSError("raised after the active Dataset was replaced")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir()
            dataset_path.write_bytes(prior)
            catalogue = Catalogue(
                workspace, adapters=[SpyAdapter("first", [candidate])]
            )

            with patch(
                "car_picker.catalogue.write_json_atomically",
                side_effect=replace_then_raise,
            ):
                report = catalogue.refresh()

            self.assertNotEqual(dataset_path.read_bytes(), prior)
            self.assertEqual(
                catalogue.current().offers[0].offer_identity, "first:car:one"
            )

        self.assertEqual(report.catalogue_offer_count, 1)

    def test_cli_diagnostics_distinguish_failure_categories_and_hide_details(
        self,
    ) -> None:
        prior = b'{"schemaVersion":"catalogue-dataset/v1","marker":"prior"}'

        cases: list[tuple[str, BaseException, int, str]] = [
            (
                "operational",
                OSError("https://secret.example/response"),
                1,
                "catalogue.provider_retrieval_failed",
            ),
            (
                "unexpected-defect",
                RuntimeError("implementation traceback detail"),
                3,
                "catalogue.unexpected_defect",
            ),
            (
                "interruption",
                KeyboardInterrupt(),
                130,
                "catalogue.refresh_interrupted",
            ),
        ]

        for category, failure, exit_code, code in cases:
            with (
                self.subTest(category=category),
                tempfile.TemporaryDirectory() as directory,
            ):
                workspace = Path(directory)
                write_registry(workspace, [provider("first")])
                dataset_path = workspace / "var/catalogue-dataset.json"
                dataset_path.parent.mkdir()
                dataset_path.write_bytes(prior)
                adapter = SpyAdapter("first", calls=[], failure=failure)

                with patch(
                    "car_picker.__main__.production_provider_adapters",
                    return_value=(adapter,),
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

                diagnostic = json.loads(result.stderr)
                self.assertEqual(result.exit_code, exit_code, result.output)
                self.assertEqual(diagnostic["error"]["category"], category)
                self.assertEqual(diagnostic["error"]["code"], code)
                self.assertTrue(diagnostic["safeState"]["unchanged"])
                self.assertEqual(dataset_path.read_bytes(), prior)
                self.assertNotIn("secret.example", result.output)
                self.assertNotIn("traceback", result.output.lower())

    def test_cli_invalid_input_uses_invalid_input_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first")])
            adapter = SpyAdapter("first", calls=[])
            with patch(
                "car_picker.__main__.production_provider_adapters",
                return_value=(adapter,),
            ):
                result = CliRunner().invoke(
                    app,
                    [
                        "--workspace",
                        str(workspace / "missing"),
                        "--json",
                        "catalogue",
                        "refresh",
                    ],
                )

        diagnostic = json.loads(result.stderr)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(diagnostic["error"]["category"], "invalid-input")
        self.assertEqual(diagnostic["error"]["code"], "catalogue.workspace_invalid")
        self.assertEqual(adapter._calls, [])


if __name__ == "__main__":
    unittest.main()
