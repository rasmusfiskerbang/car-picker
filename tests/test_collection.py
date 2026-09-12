from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from car_picker import (
    Catalogue,
    CatalogueCandidate,
    CatalogueRefreshError,
    KnownCandidateFact,
    KnownFact,
)
from car_picker.__main__ import app
from car_picker.collection import (
    FleasingProviderAdapter,
    TerminalenProviderAdapter,
    production_provider_adapters,
)
from car_picker.fleasing import FleasingAdapter, StructuralSourceError
from car_picker.provider_scope import (
    FLEASING_CATALOGUE_URL,
    FLEASING_FLEXLEASING_URL,
    TERMINALEN_CATALOGUE_URL,
)
from typer.testing import CliRunner

from tests.test_catalogue_contract import sample_dataset


class NoopHttpClient:
    def get_text(self, url: str) -> str:
        raise AssertionError(f"unexpected source request: {url}")


class FixtureHttpClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.requested_urls: list[str] = []

    def get_text(self, url: str) -> str:
        self.requested_urls.append(url)
        return self._responses[url]


class EmptyProviderAdapter:
    def __init__(self, provider_id: str, calls: list[str]) -> None:
        self.provider_id = provider_id
        self._calls = calls

    def collect(self) -> list[CatalogueCandidate]:
        self._calls.append(self.provider_id)
        return []


class CollectionTest(unittest.TestCase):
    def test_fleasing_provider_adapter_preserves_source_order_identity_and_images(
        self,
    ) -> None:
        detail_url = (
            "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427"
        )
        second_detail_url = "https://fleasing.dk/bil/?bmw-i4&vid=771869804"
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: fixture_text("fleasing/catalogue.html"),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: fixture_text("fleasing/aston-martin-db9.html"),
                second_detail_url: fixture_text("fleasing/bmw-i4.html"),
            }
        )

        candidates = FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

        self.assertEqual(
            client.requested_urls,
            [
                FLEASING_CATALOGUE_URL,
                FLEASING_FLEXLEASING_URL,
                detail_url,
                second_detail_url,
            ],
        )
        self.assertEqual(
            [candidate.offer_identity for candidate in candidates],
            [
                "fleasing:442795427:private-b3e29d362bda",
                "fleasing:771869804:private-390493d196b5",
            ],
        )
        self.assertEqual(candidates[0].canonical_source_url, detail_url)
        self.assertEqual(
            candidates[
                0
            ].admission_facts.private_consumer_eligibility.evidence.source_url,
            detail_url,
        )
        self.assertEqual(
            candidates[0].offer.canonical_offer_url if candidates[0].offer else None,
            detail_url,
        )
        self.assertEqual(
            candidates[0].offer.image_urls if candidates[0].offer else None,
            ["https://fleasing.dk/wp-content/uploads/2026/07/aston-martin-db9.jpg"],
        )
        serialized_candidates = json.dumps(
            [candidate.model_dump(mode="json") for candidate in candidates]
        )
        self.assertNotIn("sourceMetadata", serialized_candidates)
        self.assertNotIn("documents", serialized_candidates)

    def test_fleasing_provider_adapter_accepts_a_valid_empty_catalogue(self) -> None:
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: '<a href="/biler/">Personbiler</a>',
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
            }
        )

        candidates = FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

        self.assertEqual(candidates, [])

    def test_fleasing_provider_adapter_keeps_each_configuration_applicable_to_its_offer(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?porsche-taycan&vid=982451736"
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Porsche Taycan</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: fixture_text("fleasing/porsche-taycan-configurations.html"),
            }
        )

        candidates = FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

        self.assertEqual(
            [candidate.offer_identity for candidate in candidates],
            [
                "fleasing:982451736:private-standard",
                "fleasing:982451736:private-low-upfront",
            ],
        )
        self.assertEqual(
            [
                (
                    candidate.offer.term_months if candidate.offer else None,
                    candidate.offer.base_cash_flow_stream[0].amount.value
                    if candidate.offer
                    and isinstance(
                        candidate.offer.base_cash_flow_stream[0].amount, KnownFact
                    )
                    else None,
                    candidate.offer.base_cash_flow_stream[1].amount.value
                    if candidate.offer
                    and isinstance(
                        candidate.offer.base_cash_flow_stream[1].amount, KnownFact
                    )
                    else None,
                )
                for candidate in candidates
            ],
            [(12, 149995, 9995), (12, 99995, 11995)],
        )

    def test_fleasing_candidate_evidence_failure_is_quarantined_during_refresh(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?conflicting&vid=982451736"
        detail_html = """
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <dl>
                <dt>Køretøjstype</dt><dd>Personbil</dd>
                <dt>Køretøjstype</dt><dd>Varebil</dd>
                <dt>Leasingform</dt><dd>Finansiel leasing</dd>
                <dt>Leasingform</dt><dd>Operationel leasing</dd>
                <dt>Drivmiddel</dt><dd>Elektrisk</dd>
              </dl>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                <ul data-configuration-id="conflicting">
                  <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
                  <li>Udbetaling 149.995 kr. /inkl. moms</li>
                  <li>Leasingperiode 12</li>
                </ul>
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Conflicting Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 1)
        self.assertEqual(
            [reason.criterion for reason in dataset.quarantined_candidates[0].reasons],
            ["passenger_car_scope", "supported_leasing_form"],
        )
        self.assertNotIn("sourceMetadata", json.dumps(dataset.model_dump(mode="json")))

    def test_fleasing_without_first_party_drivetrain_evidence_is_not_an_offer(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?missing-drivetrain&vid=982451736"
        detail_html = """
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <dl>
                <dt>Køretøjstype</dt><dd>Personbil</dd>
                <dt>Leasingform</dt><dd>Finansiel leasing</dd>
              </dl>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                <ul data-configuration-id="missing-drivetrain">
                  <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
                  <li>Udbetaling 149.995 kr. /inkl. moms</li>
                  <li>Leasingperiode 12</li>
                </ul>
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Missing drivetrain Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 1)
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].code,
            "candidate-shape.vehicle-kind-unknown",
        )

    def test_fleasing_supporting_facts_require_private_qualified_residual_value(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?unqualified-residual&vid=982451736"
        detail_html = """
            <div class="vehicle-page-info">
              <h1>Porsche Taycan</h1><h3>Performance Plus</h3>
              <div id="privat">
                <h2>Privatleasing · inkl. moms</h2>
                <ul data-configuration-id="unqualified">
                  <li>Ydelse pr. måned 9.995 kr. /inkl. moms</li>
                  <li>Udbetaling 149.995 kr. /inkl. moms</li>
                  <li>Restværdi 500.000 kr.</li>
                  <li>Leasingperiode 12</li>
                </ul>
              </div>
            </div>
        """
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Unqualified Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        [candidate] = FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

        self.assertNotEqual(
            candidate.admission_facts.supported_leasing_form.state, "known"
        )

    def test_fleasing_private_tab_establishes_unqualified_private_prices(self) -> None:
        detail_url = "https://fleasing.dk/bil/?unqualified-private&vid=982451736"
        detail_html = fixture_text("fleasing/porsche-taycan-configurations.html")
        detail_html = detail_html.replace(
            "Privatleasing · inkl. moms", "Privatleasing"
        ).replace(" /inkl. moms", "")
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Unqualified Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        candidates = FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

        self.assertEqual(len(candidates), 2)
        for candidate in candidates:
            self.assertEqual(
                candidate.admission_facts.private_consumer_eligibility.state, "known"
            )
            fact = candidate.admission_facts.private_consumer_eligibility
            assert isinstance(fact, KnownCandidateFact)
            self.assertTrue(fact.value)
            self.assertIsNotNone(candidate.offer)

    def test_fleasing_explicit_net_private_payment_is_quarantined_on_refresh(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?net-private&vid=982451736"
        detail_html = fixture_text("fleasing/porsche-taycan-configurations.html")
        detail_html = detail_html.replace("/inkl. moms", "/ex. moms")
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Net Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        self.assertEqual(
            [
                [reason.criterion for reason in candidate.reasons]
                for candidate in dataset.quarantined_candidates
            ],
            [
                [
                    "advertised_monthly_payment",
                    "upfront_payment",
                    "private_consumer_amount_admissibility",
                ],
                [
                    "advertised_monthly_payment",
                    "upfront_payment",
                    "private_consumer_amount_admissibility",
                ],
            ],
        )

    def test_fleasing_upfront_only_vat_conflict_is_attributed_to_upfront_payment(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?net-upfront&vid=982451736"
        detail_html = fixture_text("fleasing/porsche-taycan-configurations.html")
        detail_html = detail_html.replace(
            "Udbetaling 149.995 kr. /inkl. moms", "Udbetaling 149.995 kr. /ex. moms"
        ).replace(
            "Udbetaling 99.995 kr. /inkl. moms", "Udbetaling 99.995 kr. /ex. moms"
        )
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Upfront-net Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        reasons = [
            reason
            for candidate in dataset.quarantined_candidates
            for reason in candidate.reasons
        ]
        self.assertTrue(
            all(
                reason.criterion
                in {"upfront_payment", "private_consumer_amount_admissibility"}
                for reason in reasons
            )
        )
        self.assertTrue(
            all(
                reason.code == "upfront-payment.vat-conflicting"
                for reason in reasons
                if reason.criterion == "upfront_payment"
            )
        )
        self.assertTrue(
            all(reason.evidence[0].source_url == detail_url for reason in reasons)
        )

    def test_fleasing_ambiguous_configuration_ids_are_quarantined_individually(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?duplicate-config&vid=982451736"
        detail_html = fixture_text("fleasing/porsche-taycan-configurations.html")
        detail_html = detail_html.replace(
            'data-configuration-id="standard"',
            'data-configuration-id="duplicate"',
        ).replace(
            'data-configuration-id="low-upfront"',
            'data-configuration-id="duplicate"',
        )
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Duplicate Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: detail_html,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        self.assertEqual(
            [candidate.offer_identity for candidate in dataset.quarantined_candidates],
            [
                "fleasing:982451736:private-duplicate-1",
                "fleasing:982451736:private-duplicate-2",
            ],
        )
        self.assertTrue(
            all(
                reason.criterion == "offer_identity"
                for candidate in dataset.quarantined_candidates
                for reason in candidate.reasons
            )
        )

    def test_fleasing_malformed_identity_failure_is_a_structural_boundary_error(
        self,
    ) -> None:
        detail_url = "https://fleasing.dk/bil/?malformed-identity&vid=982451736"
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: (
                    f'<a href="/biler/">Personbiler</a><a href="{detail_url}">'
                    "Malformed identity Porsche</a>"
                ),
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
                detail_url: fixture_text("fleasing/porsche-taycan-configurations.html"),
            }
        )
        raw_record = FleasingAdapter(client, "2026-08-16T12:00:00Z").collect()[0]
        raw_record["configurationIdentityFailures"] = [
            {"state": "conflicting", "code": "duplicate_configuration_id"}
        ]

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            catalogue = Catalogue(
                workspace,
                adapters=[FleasingProviderAdapter(client, "2026-08-16T12:00:00Z")],
            )

            with (
                patch(
                    "car_picker.collection.FleasingAdapter.collect",
                    return_value=[raw_record],
                ),
                self.assertRaisesRegex(
                    CatalogueRefreshError,
                    "Provider fleasing returned structurally invalid source data",
                ),
            ):
                catalogue.refresh()

    def test_fleasing_unscoped_empty_catalogue_is_a_provider_structural_failure(
        self,
    ) -> None:
        client = FixtureHttpClient(
            {
                FLEASING_CATALOGUE_URL: "<p>No designated navigation.</p>",
                FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
            }
        )

        with self.assertRaises(StructuralSourceError):
            FleasingProviderAdapter(client, "2026-08-16T12:00:00Z").collect()

    def test_fleasing_fixture_refresh_admits_source_offers(self) -> None:
        detail_url = (
            "https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427"
        )
        responses = {
            FLEASING_CATALOGUE_URL: fixture_text("fleasing/catalogue.html"),
            FLEASING_FLEXLEASING_URL: fixture_text("fleasing/flexleasing.html"),
            detail_url: fixture_text("fleasing/aston-martin-db9.html"),
            "https://fleasing.dk/bil/?bmw-i4&vid=771869804": fixture_text(
                "fleasing/bmw-i4.html"
            ),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("fleasing")])
            adapter = FleasingProviderAdapter(
                FixtureHttpClient(responses), "2026-08-16T12:00:00Z"
            )
            candidates = adapter.collect()
            self.assertTrue(
                all(
                    candidate.offer is not None
                    and candidate.offer.offer_identity == candidate.offer_identity
                    and candidate.offer.provider_id == candidate.provider_id
                    for candidate in candidates
                )
            )
            for candidate in candidates:
                for fact in (
                    candidate.admission_facts.private_consumer_eligibility,
                    candidate.admission_facts.passenger_car_scope,
                    candidate.admission_facts.current_availability,
                    candidate.admission_facts.supported_leasing_form,
                ):
                    self.assertEqual(fact.state, "known")
                    self.assertTrue(fact.evidence.wording)
            self.assertEqual(
                [
                    candidate.admission_facts.private_consumer_amount_admissibility.state
                    for candidate in candidates
                ],
                ["known", "known"],
            )
            catalogue = Catalogue(
                workspace,
                adapters=[adapter],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-16T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertGreater(report.catalogue_offer_count, 0)
        self.assertEqual(report.catalogue_offer_count, len(dataset.offers))
        self.assertIn(
            "fleasing:442795427:private-b3e29d362bda",
            [offer.offer_identity for offer in dataset.offers],
        )
        self.assertTrue(
            all(
                offer.provider_id == "fleasing"
                and offer.offer_identity.startswith("fleasing:")
                for offer in dataset.offers
            )
        )

    def test_terminalen_fixture_refresh_admits_source_offers(self) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: fixture_text("terminalen/inster-price-page.json"),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            adapter = TerminalenProviderAdapter(
                FixtureHttpClient(responses), "2026-08-16T12:00:00Z"
            )
            candidates = adapter.collect()
            self.assertTrue(
                all(
                    candidate.offer is not None
                    and candidate.offer.offer_identity == candidate.offer_identity
                    and candidate.offer.provider_id == candidate.provider_id
                    for candidate in candidates
                )
            )
            for candidate in candidates:
                for fact in (
                    candidate.admission_facts.private_consumer_eligibility,
                    candidate.admission_facts.private_consumer_amount_admissibility,
                    candidate.admission_facts.passenger_car_scope,
                    candidate.admission_facts.current_availability,
                    candidate.admission_facts.supported_leasing_form,
                ):
                    self.assertEqual(fact.state, "known")
                    self.assertTrue(fact.evidence.wording)
            catalogue = Catalogue(
                workspace,
                adapters=[adapter],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-16T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 2)
        self.assertEqual(len(dataset.quarantined_candidates), 0)
        self.assertEqual(
            [offer.offer_identity for offer in dataset.offers],
            [
                "terminalen:HY_INSTER:private-2f775a9b781a",
                "terminalen:HY_INSTER:private-e25cc77f6e4b",
            ],
        )
        self.assertTrue(
            all(
                offer.offer_identity.startswith("terminalen:")
                and offer.provider_id == "terminalen"
                for offer in dataset.offers
            )
        )
        first_offer = dataset.offers[0]
        self.assertEqual(
            first_offer.image_urls,
            [
                "https://assets.terminalen.dk/media/inster/model-overview.webp",
                "https://assets.terminalen.dk/media/inster/hero.webp",
            ],
        )
        serialized_offer = first_offer.model_dump(mode="json", by_alias=True)
        self.assertEqual(
            serialized_offer["advertisedTotal"]["value"]["amountDkk"],
            117195,
        )
        self.assertEqual(
            serialized_offer["calculatedTotal"]["value"]["amountDkk"],
            117065,
        )
        self.assertEqual(
            serialized_offer["calculatedMonthlyTotal"]["value"]["amountDkk"],
            3251.81,
        )

    def test_terminalen_explicit_vat_exclusion_quarantines_candidates(self) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        payload["grid"][0]["content"][3]["text"] = (
            "<p>Alle beløb er eksklusive moms.</p>"
        )
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            adapter = TerminalenProviderAdapter(
                FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
            )
            catalogue = Catalogue(workspace, adapters=[adapter])

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        self.assertEqual(len(dataset.offers), 0)
        self.assertEqual(
            [reason.criterion for reason in dataset.quarantined_candidates[0].reasons],
            ["private_consumer_amount_admissibility"],
        )
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].state,
            "conflicting",
        )

    def test_terminalen_card_vat_exclusion_quarantines_that_configuration(
        self,
    ) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        payload["grid"][0]["content"][2]["columns"][0]["text"] += (
            "<p>Alle beløb er ekskl. moms.</p>"
        )
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    TerminalenProviderAdapter(
                        FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
                    )
                ],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 1)
        self.assertEqual(report.quarantined_candidate_count, 1)
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].criterion,
            "private_consumer_amount_admissibility",
        )

    def test_terminalen_non_ioniq_suv_fallback_is_quarantined(self) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        del payload["vehicleData"]["vehicleType"]
        payload["vehicleData"]["bodyType"] = "SUV"
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    TerminalenProviderAdapter(
                        FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
                    )
                ],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].criterion,
            "passenger_car_scope",
        )
        self.assertEqual(
            dataset.quarantined_candidates[0].reasons[0].state,
            "unclear",
        )

    def test_terminalen_unsupported_drivetrain_is_quarantined(self) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        payload["pimModelId"] = "HY_UNKNOWN"
        payload["vehicleData"]["model"] = "UNKNOWN MODEL"
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    TerminalenProviderAdapter(
                        FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
                    )
                ],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 2)
        self.assertEqual(
            [reason.criterion for reason in dataset.quarantined_candidates[0].reasons],
            ["candidate_shape"],
        )

    def test_terminalen_valid_empty_source_publishes_an_empty_refresh(self) -> None:
        price_path = "/nye-biler/hyundai/hyundai-bayon/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        payload["url"] = price_path
        payload["grid"] = []
        payload.pop("pimModelId")
        payload.pop("vehicleData")
        catalogue_payload = {
            "G./api/navigation?culture=da-DK&levels=10": {
                "body": [
                    {
                        "url": price_path,
                        "template": "modelSubpage",
                        "children": [],
                    }
                ]
            }
        }
        catalogue_html = (
            '<script id="terminalen-ncg-state" type="application/json">'
            f"{json.dumps(catalogue_payload)}"
            "</script>"
        )
        responses = {
            TERMINALEN_CATALOGUE_URL: catalogue_html,
            price_url: "<h1>Hyundai BAYON</h1>",
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    TerminalenProviderAdapter(
                        FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
                    )
                ],
            )

            with patch(
                "car_picker.catalogue._current_timestamp",
                return_value="2026-08-23T12:00:00Z",
            ):
                report = catalogue.refresh()
            dataset = catalogue.current()

        self.assertEqual(report.catalogue_offer_count, 0)
        self.assertEqual(report.quarantined_candidate_count, 0)
        self.assertEqual(dataset.offers, [])
        self.assertEqual(dataset.quarantined_candidates, [])

    def test_terminalen_mismatched_page_api_is_provider_structural_failure(
        self,
    ) -> None:
        price_path = "/nye-biler/hyundai/hyundai-inster/pris-og-udstyr"
        price_url = f"https://www.terminalen.dk{price_path}"
        api_url = (
            f"https://www.terminalen.dk/api/page/url?url={price_path}&culture=da-DK"
        )
        payload = json.loads(fixture_text("terminalen/inster-price-page.json"))
        payload["url"] = "/nye-biler/hyundai/hyundai-kona-electric/pris-og-udstyr"
        responses = {
            TERMINALEN_CATALOGUE_URL: fixture_text("terminalen/catalogue.html"),
            price_url: fixture_text("terminalen/inster-price-page.html"),
            api_url: json.dumps(payload),
        }

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("terminalen")])
            catalogue = Catalogue(
                workspace,
                adapters=[
                    TerminalenProviderAdapter(
                        FixtureHttpClient(responses), "2026-08-23T12:00:00Z"
                    )
                ],
            )

            with self.assertRaises(CatalogueRefreshError) as raised:
                catalogue.refresh()

        self.assertEqual(raised.exception.code, "catalogue.provider_structural_failure")
        self.assertEqual(raised.exception.provider_id, "terminalen")
        self.assertFalse((workspace / "var/catalogue-dataset.json").exists())

    def test_refresh_is_registry_backed_and_uses_workspace_dataset_path(self) -> None:
        calls: list[str] = []
        adapters = [
            EmptyProviderAdapter("second", calls),
            EmptyProviderAdapter("first", calls),
        ]

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_registry(workspace, [provider("first"), provider("second")])
            runner = CliRunner()
            with (
                patch(
                    "car_picker.__main__.production_provider_adapters",
                    return_value=adapters,
                ),
                patch(
                    "car_picker.catalogue._current_timestamp",
                    return_value="2026-08-16T12:00:00Z",
                ),
            ):
                result = runner.invoke(
                    app,
                    ["--workspace", str(workspace), "catalogue", "refresh"],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            dataset_path = workspace / "var/catalogue-dataset.json"
            self.assertTrue(dataset_path.is_file())
            dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(dataset["generatedAt"], "2026-08-16T12:00:00Z")
        self.assertEqual(dataset["offers"], [])

    def test_refresh_has_no_legacy_artifact_source_or_control_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "catalogue",
                "refresh",
                "--dataset",
                "legacy.json",
                "--provider-control",
                "control.json",
                "--fleasing-catalogue-url",
                "https://example.test/legacy",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("no such option", result.output.lower())

    def test_refresh_catalogue_legacy_command_is_not_exposed(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["refresh-catalogue"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("no such command", result.output.lower())

    def test_catalogue_inspect_remains_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            dataset_path = workspace / "var/catalogue-dataset.json"
            dataset_path.parent.mkdir(parents=True)
            dataset_path.write_text(json.dumps(sample_dataset()), encoding="utf-8")
            result = CliRunner().invoke(
                app,
                ["--workspace", str(workspace), "catalogue", "inspect"],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Catalogue Dataset", result.output)

    def test_production_composition_keeps_registry_provider_order(self) -> None:
        adapters = production_provider_adapters(
            NoopHttpClient(), retrieved_at="2026-08-16T12:00:00Z"
        )

        self.assertIsInstance(adapters, tuple)
        self.assertIsInstance(adapters[0], FleasingProviderAdapter)
        self.assertIsInstance(adapters[1], TerminalenProviderAdapter)
        self.assertEqual(
            [adapter.provider_id for adapter in adapters], ["fleasing", "terminalen"]
        )


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


def fixture_text(relative_path: str) -> str:
    return (Path(__file__).parent / "fixtures" / relative_path).read_text(
        encoding="utf-8"
    )


if __name__ == "__main__":
    unittest.main()
