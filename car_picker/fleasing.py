from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Annotated, Any, Literal, Protocol, TypeAlias
from urllib.parse import parse_qs, urljoin, urlparse

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

from car_picker.provider_contract import (
    evidence,
    known_fact,
    source_document,
    unavailable_fact,
)
from car_picker.provider_scope import (
    FLEASING_CATALOGUE_URL,
    FLEASING_FLEXLEASING_URL,
)


PARSER_VERSION = "fleasing-html-v8"
FLEASING_IMAGE_HOST = "billeder.bilinfo.net"
FLEASING_IMAGE_PATH_PREFIX = "/bilinfo/"
FLEASING_UPLOAD_PATH_PREFIX = "/wp-content/uploads/"
BACKGROUND_IMAGE_URL = re.compile(
    r"background-image\s*:\s*url\(\s*(['\"]?)(?P<url>.*?)\1\s*\)",
    flags=re.IGNORECASE,
)


class TextHttpClient(Protocol):
    """The bounded HTTP boundary used by a source adapter."""

    def get_text(self, url: str) -> str: ...


class StructuralSourceError(ValueError):
    """The designated source changed shape and cannot be mapped safely."""


class UnavailablePrivateDetailError(StructuralSourceError):
    """A listed detail page cannot establish the private-offer facts it needs."""


def _validate_fleasing_source_url(value: str) -> str:
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError as error:
        raise ValueError("Fleasing boundary URLs must be valid HTTPS URLs") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(
            "Fleasing boundary URLs must be absolute HTTPS URLs without credentials or fragments"
        )
    return value


FleasingSourceUrl: TypeAlias = Annotated[
    str,
    StringConstraints(min_length=1),
    AfterValidator(_validate_fleasing_source_url),
]
FleasingBoundaryState: TypeAlias = Literal[
    "known", "not_stated", "unclear", "conflicting", "not_applicable"
]
FleasingIdentityFailureCode: TypeAlias = Literal[
    "ambiguous_derived_configuration_id",
    "invalid_configuration_id",
    "duplicate_configuration_id",
]


class _FleasingBoundaryModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: (
            name.split("_")[0]
            + "".join(part.capitalize() for part in name.split("_")[1:])
        ),
        populate_by_name=True,
        extra="forbid",
        strict=True,
    )


class FleasingBoundaryEvidence(_FleasingBoundaryModel):
    source_url: FleasingSourceUrl
    wording: str = Field(min_length=1)


class FleasingBoundaryFact(_FleasingBoundaryModel):
    state: FleasingBoundaryState
    value: JsonValue | None = None
    value_dkk: int | None = None
    evidence: FleasingBoundaryEvidence

    @model_validator(mode="after")
    def known_values_are_present(self) -> "FleasingBoundaryFact":
        has_value = self.value is not None or self.value_dkk is not None
        if self.state == "known" and not has_value:
            raise ValueError("known Fleasing facts must carry a value")
        if self.state != "known" and has_value:
            raise ValueError("unavailable Fleasing facts must not carry a value")
        if self.value is not None and self.value_dkk is not None:
            raise ValueError("Fleasing facts must not carry two values")
        return self


class FleasingBoundaryIdentityFailure(_FleasingBoundaryModel):
    fact: Literal["sourceLocalConfigurationKey"]
    state: Literal["unclear", "conflicting"]
    code: FleasingIdentityFailureCode


class FleasingBoundaryCashFlowEvent(_FleasingBoundaryModel):
    meaning: str = Field(min_length=1)
    direction: Literal["payment", "receipt"]
    amount_dkk: int | float | None
    amount_basis: Literal["including_vat", "excluding_vat", "not_stated"]
    timing: Literal["acceptance_to_handover", "recurring", "normal_completion_end"]
    recurrence_count: int | None
    refundability: Literal["refundable", "not_refundable", "not_stated"]
    included_in_base: Literal[True]
    blocking_facts: list[str] | None = None
    evidence: FleasingBoundaryEvidence


class FleasingBoundarySourceDocument(_FleasingBoundaryModel):
    source_url: FleasingSourceUrl
    content_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    retrieved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class FleasingBoundarySourceMetadata(_FleasingBoundaryModel):
    parser_version: str = Field(min_length=1)
    documents: list[FleasingBoundarySourceDocument] = Field(min_length=1)


class FleasingBoundaryRecord(_FleasingBoundaryModel):
    """Validated transient record crossing from Fleasing parsing to ingress."""

    offer_identity: str = Field(min_length=1)
    provider: Literal["Fleasing"]
    provider_source_id: str = Field(min_length=1)
    canonical_offer_url: FleasingSourceUrl
    source_local_configuration_key: str = Field(min_length=1)
    vehicle_specification: FleasingBoundaryFact
    image_urls: list[FleasingSourceUrl]
    configuration_identity_failures: list[FleasingBoundaryIdentityFailure]
    upfront_payment: FleasingBoundaryFact
    private_consumer_eligibility: FleasingBoundaryFact
    private_consumer_amount_admissibility: FleasingBoundaryFact
    passenger_car_scope: FleasingBoundaryFact
    current_availability: FleasingBoundaryFact
    supported_leasing_form: FleasingBoundaryFact
    advertised_monthly_payment: FleasingBoundaryFact
    term_months: FleasingBoundaryFact
    base_cash_flow_stream: list[FleasingBoundaryCashFlowEvent] = Field(min_length=1)
    base_cash_flow_blockers: list[str] | None
    annual_mileage_km: FleasingBoundaryFact
    normal_end_mechanism: FleasingBoundaryFact
    residual_risk_allocation: FleasingBoundaryFact
    registration_tax_treatment: FleasingBoundaryFact
    service_arrangements: FleasingBoundaryFact
    exclusions: FleasingBoundaryFact
    exposure_scenarios: FleasingBoundaryFact
    source_metadata: FleasingBoundarySourceMetadata

    @model_validator(mode="after")
    def known_vehicle_has_supported_drivetrain(self) -> "FleasingBoundaryRecord":
        if self.vehicle_specification.state != "known":
            return self
        value = self.vehicle_specification.value
        if not isinstance(value, Mapping):
            raise ValueError("known Fleasing vehicle facts must be an object")
        drivetrain = value.get("drivetrain")
        if drivetrain not in {"gasoline", "diesel", "battery_electric"}:
            raise ValueError(
                "known Fleasing vehicle facts must establish a supported drivetrain"
            )
        return self


@dataclass(frozen=True)
class DiscoveredOffer:
    url: str
    source_fragment: str


@dataclass(frozen=True)
class FleasingSupportingEvidence:
    source_url: str
    source_html: str
    form_wording: str
    end_wording: str
    registration_tax_wording: str


@dataclass(frozen=True)
class FleasingDrivetrainEvidence:
    normalized_value: str
    source_wording: str


class FleasingAdapter:
    """Map Fleasing's first-party vehicle page and its private-pricing tab."""

    def __init__(self, http_client: TextHttpClient, retrieved_at: str) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at

    def collect(
        self, catalogue_url: str = FLEASING_CATALOGUE_URL
    ) -> list[dict[str, Any]]:
        catalogue_html = self._http_client.get_text(catalogue_url)
        supporting_url = urljoin(catalogue_url, "/flexleasing/")
        supporting_html = self._http_client.get_text(supporting_url)
        supporting_evidence = flexleasing_supporting_evidence(
            supporting_html, supporting_url
        )
        offers = catalogue_detail_offers(catalogue_html, catalogue_url)
        if not offers:
            if (
                passenger_car_catalogue_fact(catalogue_html, catalogue_url).get("state")
                == "known"
            ):
                return []
            raise StructuralSourceError(
                "Fleasing catalogue contains no designated detail links"
            )

        candidates: list[dict[str, Any]] = []
        for offer in offers:
            detail_html = self._http_client.get_text(offer.url)
            try:
                detail_candidates = map_detail_pages(
                    catalogue_url=catalogue_url,
                    catalogue_html=catalogue_html,
                    discovered_offer=offer,
                    detail_html=detail_html,
                    retrieved_at=self._retrieved_at,
                    supporting_evidence=supporting_evidence,
                )
            except UnavailablePrivateDetailError:
                detail_candidates = [
                    quarantined_unavailable_detail_candidate(
                        catalogue_url=catalogue_url,
                        catalogue_html=catalogue_html,
                        discovered_offer=offer,
                        detail_html=detail_html,
                        retrieved_at=self._retrieved_at,
                        supporting_evidence=supporting_evidence,
                    )
                ]
            candidates.extend(detail_candidates)
        return candidates

    def collect_boundary_records(
        self, catalogue_url: str = FLEASING_CATALOGUE_URL
    ) -> list[FleasingBoundaryRecord]:
        """Validate every fetched record before trusted Catalogue composition."""
        return [
            FleasingBoundaryRecord.model_validate(record)
            for record in self.collect(catalogue_url)
        ]


def catalogue_detail_offers(
    catalogue_html: str, catalogue_url: str
) -> list[DiscoveredOffer]:
    parser = CatalogueLinkParser()
    parser.feed(catalogue_html)
    parser.close()
    catalogue_host = urlparse(catalogue_url).hostname
    catalogue_parts = urlparse(catalogue_url)
    offers: list[DiscoveredOffer] = []
    seen_source_ids: set[str] = set()
    for href, text in parser.links:
        detail_url = urljoin(catalogue_url, href)
        parsed = urlparse(detail_url)
        try:
            detail_port = parsed.port
            catalogue_port = catalogue_parts.port
        except ValueError:
            continue
        same_origin = (
            parsed.hostname == catalogue_host
            and parsed.scheme == catalogue_parts.scheme
            and detail_port == catalogue_port
        )
        if not same_origin or parsed.path != "/bil/":
            continue
        query = parse_qs(parsed.query, keep_blank_values=True)
        if "vid" not in query:
            continue
        source_ids = query["vid"]
        if (
            parsed.fragment
            or len(source_ids) != 1
            or not re.fullmatch(r"[A-Za-z0-9_-]+", source_ids[0])
        ):
            raise StructuralSourceError(
                "Fleasing catalogue contains a malformed designated detail link"
            )
        source_id = source_ids[0]
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        offers.append(DiscoveredOffer(detail_url, f'href="{href}" {text}'.strip()))
    return offers


def catalogue_detail_urls(catalogue_html: str, catalogue_url: str) -> list[str]:
    """Expose the bounded detail enumeration for the source-adapter test seam."""
    return [
        offer.url for offer in catalogue_detail_offers(catalogue_html, catalogue_url)
    ]


def map_detail_page(
    *,
    catalogue_url: str,
    catalogue_html: str,
    discovered_offer: DiscoveredOffer,
    detail_html: str,
    retrieved_at: str,
    supporting_evidence: FleasingSupportingEvidence | None = None,
) -> dict[str, Any]:
    """Map the sole configuration exposed by a detail page."""
    candidates = map_detail_pages(
        catalogue_url=catalogue_url,
        catalogue_html=catalogue_html,
        discovered_offer=discovered_offer,
        detail_html=detail_html,
        retrieved_at=retrieved_at,
        supporting_evidence=supporting_evidence,
    )
    if len(candidates) != 1:
        raise StructuralSourceError(
            f"Fleasing detail {discovered_offer.url} contains multiple private configurations"
        )
    return candidates[0]


def map_detail_pages(
    *,
    catalogue_url: str,
    catalogue_html: str,
    discovered_offer: DiscoveredOffer,
    detail_html: str,
    retrieved_at: str,
    supporting_evidence: FleasingSupportingEvidence | None = None,
) -> list[dict[str, Any]]:
    detail = FleasingDetailParser()
    detail.feed(detail_html)
    detail.close()
    if (
        not detail.found_vehicle_info
        or not detail.found_private_tab
        or not detail.private_configurations
    ):
        raise UnavailablePrivateDetailError(
            f"Fleasing detail {discovered_offer.url} no longer contains vehicle information and a private-pricing tab"
        )

    source_id = source_id_from_url(discovered_offer.url)
    source_metadata = {
        "parserVersion": PARSER_VERSION,
        "documents": [
            source_document(catalogue_url, catalogue_html, retrieved_at),
            source_document(discovered_offer.url, detail_html, retrieved_at),
            *(
                [
                    source_document(
                        supporting_evidence.source_url,
                        supporting_evidence.source_html,
                        retrieved_at,
                    )
                ]
                if supporting_evidence is not None
                else []
            ),
        ],
    }
    vehicle = vehicle_specification(detail, discovered_offer.url)
    image_urls = exact_offer_image_urls(detail.image_urls, discovered_offer.url)
    catalogue_passenger_car_scope = passenger_car_catalogue_fact(
        catalogue_html, catalogue_url
    )
    configuration_id_counts = Counter(
        configuration_id
        for configuration_id, _ in detail.private_configurations
        if configuration_id is not None
    )
    derived_key_counts = Counter(
        configuration_key_from_private_terms(private_terms)
        for configuration_id, private_terms in detail.private_configurations
        if configuration_id is None
    )
    candidates: list[dict[str, Any]] = []
    for index, (configuration_id, private_terms) in enumerate(
        detail.private_configurations
    ):
        configuration_key, structural_reasons = configuration_identity(
            configuration_id,
            private_terms,
            index,
            configuration_id_counts,
            derived_key_counts,
        )
        candidates.append(
            map_private_configuration(
                catalogue_url=catalogue_url,
                discovered_offer=discovered_offer,
                detail=detail,
                private_terms=private_terms,
                configuration_key=configuration_key,
                structural_reasons=structural_reasons,
                source_id=source_id,
                source_metadata=source_metadata,
                vehicle=vehicle,
                image_urls=image_urls,
                catalogue_passenger_car_scope=catalogue_passenger_car_scope,
                supporting_evidence=supporting_evidence,
            )
        )
    return candidates


def map_private_configuration(
    *,
    catalogue_url: str,
    discovered_offer: DiscoveredOffer,
    detail: FleasingDetailParser,
    private_terms: Mapping[str, str],
    configuration_key: str,
    structural_reasons: list[dict[str, str]],
    source_id: str,
    source_metadata: dict[str, Any],
    vehicle: dict[str, Any],
    image_urls: list[str],
    catalogue_passenger_car_scope: dict[str, Any],
    supporting_evidence: FleasingSupportingEvidence | None,
) -> dict[str, Any]:
    private_eligibility = private_consumer_eligibility_fact(
        detail, discovered_offer.url
    )
    private_consumer_established = private_eligibility.get("state") == "known"
    monthly_payment = money_fact(
        private_terms,
        "Ydelse pr. måned",
        discovered_offer.url,
        private_consumer_established=private_consumer_established,
    )
    term_months = months_fact(private_terms, "Leasingperiode", discovered_offer.url)
    upfront_payment = money_fact(
        private_terms,
        "Udbetaling",
        discovered_offer.url,
        private_consumer_established=private_consumer_established,
    )
    amount_admissibility = private_consumer_amount_admissibility_fact(
        private_eligibility,
        monthly_payment,
        upfront_payment,
        discovered_offer.url,
    )
    supported_form = supported_leasing_form_fact(
        detail,
        private_terms,
        discovered_offer.url,
        supporting_evidence,
        private_consumer_established=private_consumer_established,
        leasing_forms=detail.leasing_forms,
    )
    normal_end = normal_end_mechanism_fact(
        private_terms,
        discovered_offer.url,
        supporting_evidence,
        private_consumer_established=private_consumer_established,
        leasing_forms=detail.leasing_forms,
    )
    candidate = {
        "offerIdentity": f"fleasing:{source_id}:{configuration_key}",
        "provider": "Fleasing",
        "providerSourceId": source_id,
        "canonicalOfferUrl": discovered_offer.url,
        "sourceLocalConfigurationKey": configuration_key,
        "vehicleSpecification": vehicle,
        "imageUrls": image_urls,
        "configurationIdentityFailures": structural_reasons,
        "upfrontPayment": upfront_payment,
        "privateConsumerEligibility": private_eligibility,
        "privateConsumerAmountAdmissibility": amount_admissibility,
        "passengerCarScope": passenger_car_fact(
            detail,
            discovered_offer.url,
            catalogue_passenger_car_scope,
        ),
        "currentAvailability": known_fact(
            True, catalogue_url, discovered_offer.source_fragment
        ),
        "supportedLeasingForm": supported_form,
        "advertisedMonthlyPayment": monthly_payment,
        "termMonths": term_months,
        "baseCashFlowStream": base_cash_flow_stream(
            upfront_payment, monthly_payment, term_months
        ),
        "baseCashFlowBlockers": (
            None if normal_end.get("state") == "known" else ["normalEndMechanism"]
        ),
        "annualMileageKm": not_stated_fact(
            discovered_offer.url, detail.private_tab_fragment
        ),
        "normalEndMechanism": normal_end,
        "residualRiskAllocation": residual_risk_allocation_fact(
            private_terms, discovered_offer.url
        ),
        "registrationTaxTreatment": registration_tax_treatment_fact(
            private_terms,
            discovered_offer.url,
            supporting_evidence,
            private_consumer_established=private_consumer_established,
            leasing_forms=detail.leasing_forms,
        ),
        "serviceArrangements": not_stated_fact(
            discovered_offer.url, detail.private_tab_fragment
        ),
        "exclusions": not_stated_fact(
            discovered_offer.url, detail.private_tab_fragment
        ),
        "exposureScenarios": not_stated_fact(
            discovered_offer.url, detail.private_tab_fragment
        ),
        "sourceMetadata": source_metadata,
    }
    return candidate


def quarantined_unavailable_detail_candidate(
    *,
    catalogue_url: str,
    catalogue_html: str,
    discovered_offer: DiscoveredOffer,
    detail_html: str,
    retrieved_at: str,
    supporting_evidence: FleasingSupportingEvidence | None = None,
) -> dict[str, Any]:
    """Retain a catalogue link whose detail page cannot support private-offer facts."""
    source_id = source_id_from_url(discovered_offer.url)
    unavailable_evidence = evidence(
        discovered_offer.url,
        'Missing required detail sections: class="vehicle-page-info" and id="privat".',
    )
    unavailable_detail_fact = {
        "state": "not_stated",
        "evidence": unavailable_evidence,
    }
    candidate = {
        "offerIdentity": f"fleasing:{source_id}:detail-unavailable",
        "provider": "Fleasing",
        "providerSourceId": source_id,
        "canonicalOfferUrl": discovered_offer.url,
        "sourceLocalConfigurationKey": "detail-unavailable",
        "vehicleSpecification": unavailable_detail_fact,
        "imageUrls": [],
        "configurationIdentityFailures": [],
        "upfrontPayment": unavailable_detail_fact,
        "privateConsumerEligibility": unavailable_detail_fact,
        "privateConsumerAmountAdmissibility": unavailable_detail_fact,
        "passengerCarScope": unavailable_detail_fact,
        "currentAvailability": unclear_fact(
            catalogue_url, discovered_offer.source_fragment
        ),
        "supportedLeasingForm": unavailable_detail_fact,
        "advertisedMonthlyPayment": unavailable_detail_fact,
        "termMonths": unavailable_detail_fact,
        "baseCashFlowStream": [
            {
                "meaning": "Privat prisoplysning er ikke tilgængelig",
                "direction": "payment",
                "amountDkk": None,
                "amountBasis": "not_stated",
                "timing": "recurring",
                "recurrenceCount": None,
                "refundability": "not_stated",
                "includedInBase": True,
                "blockingFacts": ["advertisedMonthlyPayment", "termMonths"],
                "evidence": unavailable_evidence,
            }
        ],
        "baseCashFlowBlockers": ["advertisedMonthlyPayment", "termMonths"],
        "annualMileageKm": unavailable_detail_fact,
        "normalEndMechanism": unavailable_detail_fact,
        "residualRiskAllocation": unavailable_detail_fact,
        "registrationTaxTreatment": unavailable_detail_fact,
        "serviceArrangements": unavailable_detail_fact,
        "exclusions": unavailable_detail_fact,
        "exposureScenarios": unavailable_detail_fact,
        "sourceMetadata": {
            "parserVersion": PARSER_VERSION,
            "documents": [
                source_document(catalogue_url, catalogue_html, retrieved_at),
                source_document(discovered_offer.url, detail_html, retrieved_at),
                *(
                    [
                        source_document(
                            supporting_evidence.source_url,
                            supporting_evidence.source_html,
                            retrieved_at,
                        )
                    ]
                    if supporting_evidence is not None
                    else []
                ),
            ],
        },
    }
    return candidate


def base_cash_flow_stream(
    upfront_payment: Mapping[str, Any],
    monthly_payment: Mapping[str, Any],
    term_months: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Preserve only evidenced lessee cash flows; residual value stays an external exposure."""
    return [
        payment_event("Udbetaling", upfront_payment, "acceptance_to_handover"),
        payment_event("Ydelse pr. måned", monthly_payment, "recurring", term_months),
    ]


def payment_event(
    meaning: str,
    amount_fact: Mapping[str, Any],
    timing: str,
    recurrence_fact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    amount = (
        amount_fact.get("valueDkk") if amount_fact.get("state") == "known" else None
    )
    if amount is None:
        blockers.append(
            "upfrontPayment"
            if timing == "acceptance_to_handover"
            else "advertisedMonthlyPayment"
        )

    recurrence_count = 1
    amount_evidence = evidence_value(amount_fact)
    wording = amount_evidence["wording"]
    if recurrence_fact is not None:
        recurrence_count = (
            recurrence_fact.get("value")
            if recurrence_fact.get("state") == "known"
            else None
        )
        if recurrence_count is None:
            blockers.append("termMonths")
        recurrence_wording = evidence_value(recurrence_fact)["wording"]
        wording = f"{wording}; {recurrence_wording}"

    event: dict[str, Any] = {
        "meaning": meaning,
        "direction": "payment",
        "amountDkk": amount,
        "amountBasis": "including_vat" if amount is not None else "not_stated",
        "timing": timing,
        "recurrenceCount": recurrence_count,
        "refundability": "not_refundable",
        "includedInBase": True,
        "evidence": {
            "sourceUrl": amount_evidence["sourceUrl"],
            "wording": wording,
        },
    }
    if blockers:
        event["blockingFacts"] = blockers
    return event


def evidence_value(fact: Mapping[str, Any]) -> dict[str, str]:
    value = fact.get("evidence")
    if not isinstance(value, Mapping):
        raise ValueError("payment fact must include evidence")
    source_url = value.get("sourceUrl")
    wording = value.get("wording")
    if not isinstance(source_url, str) or not isinstance(wording, str):
        raise ValueError("payment evidence must include sourceUrl and wording")
    return {"sourceUrl": source_url, "wording": wording}


def vehicle_specification(
    detail: "FleasingDetailParser", source_url: str
) -> dict[str, Any]:
    if not detail.make or not detail.trim:
        return not_stated_fact(source_url, detail.private_tab_fragment)
    drivetrain = drivetrain_fact(detail, source_url)
    if drivetrain.get("state") != "known":
        return drivetrain
    drivetrain_evidence = evidence_value(drivetrain)["wording"]
    return known_fact(
        {
            "make": detail.make,
            "model": detail.model,
            "trim": detail.trim,
            "drivetrain": drivetrain["value"],
        },
        source_url,
        f"{detail.make} {detail.model} {detail.trim}; {drivetrain_evidence}",
    )


def private_consumer_eligibility_fact(
    detail: "FleasingDetailParser", source_url: str
) -> dict[str, Any]:
    if detail.private_eligibility_fragment is not None:
        return known_fact(True, source_url, detail.private_eligibility_fragment)
    private_description = re.search(
        r"\b\d+\s+måneders\s+privatleasing\b",
        detail.description_text,
        flags=re.IGNORECASE,
    )
    if private_description is not None:
        return known_fact(True, source_url, private_description.group(0))
    return not_stated_fact(source_url, detail.private_tab_fragment)


def passenger_car_fact(
    detail: "FleasingDetailParser",
    source_url: str,
    catalogue_fact: dict[str, Any],
) -> dict[str, Any]:
    vehicle_types = set(detail.vehicle_types)
    if len(vehicle_types) > 1:
        return conflicting_fact(
            source_url,
            "; ".join(f"Køretøjstype {value}" for value in detail.vehicle_types),
        )
    if vehicle_types == {"Personbil"}:
        return known_fact(True, source_url, "Køretøjstype Personbil")
    if detail.vehicle_types:
        return unclear_fact(source_url, f"Køretøjstype {detail.vehicle_types[0]}")
    if catalogue_fact.get("state") == "known":
        return catalogue_fact
    return not_stated_fact(source_url, detail.private_tab_fragment)


def drivetrain_fact(detail: "FleasingDetailParser", source_url: str) -> dict[str, Any]:
    drivetrain_evidence = detail.drivetrain_evidence
    if not drivetrain_evidence:
        return not_stated_fact(source_url, "Drivmiddel")
    distinct_drivetrains = {
        evidence.normalized_value for evidence in drivetrain_evidence
    }
    source_wording = "; ".join(
        evidence.source_wording for evidence in drivetrain_evidence
    )
    if len(distinct_drivetrains) > 1:
        return conflicting_fact(source_url, source_wording)
    drivetrain_value = next(iter(distinct_drivetrains))
    if drivetrain_value == "unsupported":
        return unclear_fact(source_url, source_wording)
    return known_fact(drivetrain_value, source_url, source_wording)


def supported_leasing_form_fact(
    detail: "FleasingDetailParser",
    private_terms: Mapping[str, str],
    source_url: str,
    supporting_evidence: FleasingSupportingEvidence | None = None,
    *,
    private_consumer_established: bool = False,
    leasing_forms: list[str] | None = None,
) -> dict[str, Any]:
    leasing_form_values = {
        "Finansiel leasing": "financial",
        "Flexleasing": "flex",
        "Operationel leasing": "operational",
        "Hybrid leasing": "hybrid",
    }
    distinct_leasing_forms = set(detail.leasing_forms)
    if len(distinct_leasing_forms) > 1:
        return conflicting_fact(
            source_url,
            "; ".join(f"Leasingform {value}" for value in detail.leasing_forms),
        )
    leasing_form = detail.leasing_forms[0] if detail.leasing_forms else ""
    value = leasing_form_values.get(leasing_form)
    if value is not None:
        return known_fact(value, source_url, f"Leasingform {leasing_form}")
    if leasing_form:
        return unclear_fact(source_url, f"Leasingform {leasing_form}")
    if (
        flex_configuration_is_applicable(
            private_terms,
            private_consumer_established,
            leasing_forms=leasing_forms,
        )
        and supporting_evidence is not None
    ):
        return known_fact(
            "financial",
            supporting_evidence.source_url,
            supporting_evidence.form_wording,
        )
    return residual_value_fact(private_terms, source_url)


def normal_end_mechanism_fact(
    private_terms: Mapping[str, str],
    source_url: str,
    supporting_evidence: FleasingSupportingEvidence | None,
    *,
    private_consumer_established: bool = False,
    leasing_forms: list[str] | None = None,
) -> dict[str, Any]:
    if (
        flex_configuration_is_applicable(
            private_terms,
            private_consumer_established,
            leasing_forms=leasing_forms,
        )
        and supporting_evidence is not None
    ):
        return known_fact(
            "designate_third_party_buyer",
            supporting_evidence.source_url,
            supporting_evidence.end_wording,
        )
    return not_stated_fact(source_url, 'id="privat"')


def registration_tax_treatment_fact(
    private_terms: Mapping[str, str],
    source_url: str,
    supporting_evidence: FleasingSupportingEvidence | None,
    *,
    private_consumer_established: bool = False,
    leasing_forms: list[str] | None = None,
) -> dict[str, Any]:
    if (
        flex_configuration_is_applicable(
            private_terms,
            private_consumer_established,
            leasing_forms=leasing_forms,
        )
        and supporting_evidence is not None
    ):
        return known_fact(
            "proportional",
            supporting_evidence.source_url,
            supporting_evidence.registration_tax_wording,
        )
    return not_stated_fact(source_url, 'id="privat"')


def residual_risk_allocation_fact(
    private_terms: Mapping[str, str], source_url: str
) -> dict[str, Any]:
    return residual_value_fact(private_terms, source_url)


def residual_value_fact(
    private_terms: Mapping[str, str], source_url: str
) -> dict[str, Any]:
    residual_value = private_terms.get("Restværdi")
    if residual_value is None:
        return not_stated_fact(source_url, 'id="privat"')
    return unclear_fact(source_url, f"Restværdi {residual_value}")


def flex_configuration_is_applicable(
    private_terms: Mapping[str, str],
    private_consumer_established: bool,
    *,
    leasing_forms: list[str] | None = None,
) -> bool:
    """Scope generic flex evidence to an identified private residual-value row."""
    if not private_consumer_established:
        return False
    if any(
        form not in {"Finansiel leasing", "Flexleasing"} for form in leasing_forms or []
    ):
        return False
    residual_value = private_terms.get("Restværdi")
    if residual_value is None:
        return False
    return vat_states_in_wording(residual_value) == {"excluding_vat"} and bool(
        re.search(r"afgift", residual_value, flags=re.IGNORECASE)
    )


def passenger_car_catalogue_fact(
    catalogue_html: str, catalogue_url: str
) -> dict[str, Any]:
    parser = CatalogueLinkParser()
    parser.feed(catalogue_html)
    parser.close()
    for href, text in parser.links:
        if (
            urljoin(catalogue_url, href).rstrip("/") == catalogue_url.rstrip("/")
            and text.casefold() == "personbiler"
        ):
            return known_fact(
                True,
                catalogue_url,
                f'href="{href}" {text}',
            )
    return not_stated_fact(catalogue_url, "Personbiler")


def exact_offer_image_urls(image_sources: list[str], detail_url: str) -> list[str]:
    """Keep only audited vehicle images embedded by the exact detail page."""
    detail = urlparse(detail_url)
    image_urls: list[str] = []
    for image_source in image_sources:
        image_url = urljoin(detail_url, image_source.strip())
        parsed = urlparse(image_url)
        try:
            image_port = parsed.port
        except ValueError:
            continue
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            continue
        is_fleasing_upload = (
            parsed.hostname == detail.hostname
            and image_port == detail.port
            and parsed.path.startswith(FLEASING_UPLOAD_PATH_PREFIX)
            and not parsed.query
        )
        query = parse_qs(parsed.query, keep_blank_values=True)
        is_bilinfo_vehicle_image = (
            parsed.hostname == FLEASING_IMAGE_HOST
            and image_port is None
            and parsed.path.startswith(FLEASING_IMAGE_PATH_PREFIX)
            and not set(query) - {"class"}
        )
        if not is_fleasing_upload and not is_bilinfo_vehicle_image:
            continue
        normalized = parsed.geturl()
        if normalized not in image_urls:
            image_urls.append(normalized)
    return image_urls


def flexleasing_supporting_evidence(
    source_html: str,
    source_url: str = FLEASING_FLEXLEASING_URL,
) -> FleasingSupportingEvidence:
    parser = PageTextParser()
    parser.feed(source_html)
    parser.close()
    text = " ".join(parser.text_parts)
    applicability = required_source_fragment(
        text,
        r"Du kan se vores aktuelle udvalg af flexleasing biler på vores hjemmeside",
        "current flexleasing inventory applicability",
    )
    classification = required_source_fragment(
        text,
        r"Privatleasing\s*\(operationel leasing\)\s*og flexleasing\s*"
        r"\(finansiel leasing\)",
        "financial flexleasing classification",
    )
    end_wording = required_source_fragment(
        text,
        r"Til gengæld har du selv ansvar for at sælge bilen efter endt "
        r"leasingperiode, medmindre du selv vil købe bilen",
        "flexleasing end mechanism",
    )
    registration_tax_wording = required_source_fragment(
        text,
        r"Med flexleasing betales en månedlig afgift på bilen",
        "proportional registration-tax treatment",
    )
    return FleasingSupportingEvidence(
        source_url=source_url,
        source_html=source_html,
        form_wording=f"{applicability}; {classification}",
        end_wording=end_wording,
        registration_tax_wording=registration_tax_wording,
    )


def required_source_fragment(text: str, pattern: str, meaning: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise StructuralSourceError(
            f"Fleasing flexleasing explanation is missing {meaning}"
        )
    return match.group(0)


def configuration_key_from_private_terms(private_terms: Mapping[str, str]) -> str:
    selected_values = "\n".join(
        f"{label}:{value}" for label, value in sorted(private_terms.items())
    )
    return f"private-{hashlib.sha256(selected_values.encode('utf-8')).hexdigest()[:12]}"


def configuration_identity(
    explicit_id: str | None,
    private_terms: Mapping[str, str],
    index: int,
    id_counts: Mapping[str, int],
    derived_key_counts: Mapping[str, int],
) -> tuple[str, list[dict[str, str]]]:
    if explicit_id is None:
        derived_key = configuration_key_from_private_terms(private_terms)
        if derived_key_counts.get(derived_key, 0) > 1:
            return (
                f"{derived_key}-{index + 1}",
                [
                    {
                        "fact": "sourceLocalConfigurationKey",
                        "state": "unclear",
                        "code": "ambiguous_derived_configuration_id",
                    }
                ],
            )
        return derived_key, []
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", explicit_id) is None:
        fallback = configuration_key_from_private_terms(private_terms)
        return (
            f"{fallback}-{index + 1}",
            [
                {
                    "fact": "sourceLocalConfigurationKey",
                    "state": "unclear",
                    "code": "invalid_configuration_id",
                }
            ],
        )
    if id_counts.get(explicit_id, 0) > 1:
        return (
            f"private-{explicit_id}-{index + 1}",
            [
                {
                    "fact": "sourceLocalConfigurationKey",
                    "state": "conflicting",
                    "code": "duplicate_configuration_id",
                }
            ],
        )
    return f"private-{explicit_id}", []


def source_id_from_url(detail_url: str) -> str:
    source_ids = parse_qs(urlparse(detail_url).query).get("vid") or []
    if len(source_ids) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]+", source_ids[0]):
        raise StructuralSourceError(
            f"Fleasing detail URL has no vid identity: {detail_url}"
        )
    return source_ids[0]


def not_stated_fact(source_url: str, wording: str) -> dict[str, Any]:
    return unavailable_fact("not_stated", source_url, wording)


def unclear_fact(source_url: str, wording: str) -> dict[str, Any]:
    return unavailable_fact("unclear", source_url, wording)


def conflicting_fact(source_url: str, wording: str) -> dict[str, Any]:
    return unavailable_fact("conflicting", source_url, wording)


def money_fact(
    private_terms: Mapping[str, str],
    label: str,
    source_url: str,
    *,
    private_consumer_established: bool,
) -> dict[str, Any]:
    wording = private_terms.get(label)
    if wording is None:
        return not_stated_fact(source_url, 'id="privat"')
    amount = dkk_amount(wording)
    vat_states = vat_states_in_wording(wording)
    if amount is None:
        return {
            "state": "unclear",
            "evidence": evidence(source_url, f"{label} {wording}"),
        }
    if len(vat_states) > 1 or vat_states == {"excluding_vat"}:
        return {
            "state": "conflicting",
            "evidence": evidence(source_url, f"{label} {wording}"),
        }
    if not vat_states and not private_consumer_established:
        return {
            "state": "unclear",
            "evidence": evidence(source_url, f"{label} {wording}"),
        }
    return {
        "state": "known",
        "valueDkk": amount,
        "evidence": evidence(source_url, f"{label} {wording}"),
    }


def private_consumer_amount_admissibility_fact(
    private_eligibility: Mapping[str, Any],
    monthly_payment: Mapping[str, Any],
    upfront_payment: Mapping[str, Any],
    source_url: str,
) -> dict[str, Any]:
    if private_eligibility.get("state") != "known":
        return not_stated_fact(
            source_url,
            "Fleasing private-consumer payment VAT basis was not established.",
        )
    payment_facts = (upfront_payment, monthly_payment)
    conflicting = next(
        (fact for fact in payment_facts if fact.get("state") == "conflicting"),
        None,
    )
    if conflicting is not None:
        return {
            "state": "conflicting",
            "evidence": conflicting["evidence"],
        }
    wording = "; ".join(
        evidence_value(fact)["wording"]
        for fact in (private_eligibility, *payment_facts)
        if fact.get("state") == "known"
    )
    return known_fact(True, source_url, wording)


def vat_states_in_wording(wording: str) -> set[str]:
    states: set[str] = set()
    if re.search(r"\binkl(?:\.|usive)?\s*moms\b", wording, flags=re.IGNORECASE):
        states.add("including_vat")
    if re.search(
        r"\b(?:ekskl|excl|ex)(?:\.)?\s*moms\b|\buden\s+moms\b",
        wording,
        flags=re.IGNORECASE,
    ):
        states.add("excluding_vat")
    return states


def months_fact(
    private_terms: Mapping[str, str], label: str, source_url: str
) -> dict[str, Any]:
    wording = private_terms.get(label)
    if wording is None:
        return not_stated_fact(source_url, 'id="privat"')
    match = re.search(r"\b(\d+)\b", wording)
    if match is None:
        return {
            "state": "unclear",
            "evidence": evidence(source_url, f"{label} {wording}"),
        }
    return {
        "state": "known",
        "value": int(match.group(1)),
        "evidence": evidence(source_url, f"{label} {wording}"),
    }


def dkk_amount(wording: str) -> int | None:
    match = re.search(r"\b([\d.]+)\s*kr\.?", wording, flags=re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1).replace(".", ""))


class CatalogueLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text_parts).split())))
            self._href = None
            self._text_parts = []


class PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.text_parts.append(text)


class FleasingDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found_vehicle_info = False
        self.found_private_tab = False
        self.make = ""
        self.model = ""
        self.trim = ""
        self.image_urls: list[str] = []
        self.private_configurations: list[tuple[str | None, dict[str, str]]] = []
        self.private_tab_fragment = 'id="privat"'
        self.private_eligibility_fragment: str | None = None
        self.description_text = ""
        self.vehicle_types: list[str] = []
        self.leasing_forms: list[str] = []
        self.drivetrain_evidence: list[FleasingDrivetrainEvidence] = []
        self._vehicle_gallery_depth: int | None = None
        self._vehicle_info_depth: int | None = None
        self._vehicle_short_specs_depth: int | None = None
        self._private_tab_depth: int | None = None
        self._description_depth: int | None = None
        self._description_parts: list[str] = []
        self._private_configuration_depth: int | None = None
        self._private_configuration_id: str | None = None
        self._private_terms: dict[str, str] = {}
        self._depth = 0
        self._capturing_tag: str | None = None
        self._text_parts: list[str] = []
        self._definition_label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attributes = {name: value for name, value in attrs if value is not None}
        if tag == "div" and "vehicle-gallery" in attributes.get("class", "").split():
            self._vehicle_gallery_depth = self._depth
        if tag == "div" and "vehicle-page-info" in attributes.get("class", "").split():
            self.found_vehicle_info = True
            self._vehicle_info_depth = self._depth
        if (
            tag == "div"
            and "vehicle-page-short-specs" in attributes.get("class", "").split()
        ):
            self._vehicle_short_specs_depth = self._depth
        if tag == "div" and attributes.get("id") == "privat":
            self.found_private_tab = True
            self._private_tab_depth = self._depth
        if tag == "div" and attributes.get("id") == "description":
            self._description_depth = self._depth
            self._description_parts = []
        if self._in_vehicle_info() and tag == "img":
            for attribute in ("src", "data-src", "data-lazy-src"):
                image_url = attributes.get(attribute)
                if image_url:
                    self.image_urls.append(image_url)
            srcset = attributes.get("srcset")
            if srcset:
                self.image_urls.extend(
                    candidate.split()[0]
                    for candidate in srcset.split(",")
                    if candidate.split()
                )
        if self._in_vehicle_gallery():
            style = attributes.get("style", "")
            background_image = BACKGROUND_IMAGE_URL.search(style)
            if background_image:
                self.image_urls.append(background_image.group("url"))
        if (
            self._in_private_tab()
            and tag == "ul"
            and self._private_configuration_depth is None
        ):
            self._private_configuration_depth = self._depth
            self._private_configuration_id = attributes.get("data-configuration-id")
            self._private_terms = {}
        if self._in_vehicle_info() and tag in {"h1", "h3"}:
            self._capturing_tag = tag
            self._text_parts = []
        if self._in_vehicle_info() and tag in {"dt", "dd"}:
            self._capturing_tag = tag
            self._text_parts = []
        if self._in_vehicle_short_specs() and tag == "span":
            self._capturing_tag = tag
            self._text_parts = []
        if self._in_private_tab() and tag == "h2":
            self._capturing_tag = tag
            self._text_parts = []
        if self._in_private_tab() and tag == "li":
            self._capturing_tag = tag
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._description_depth is not None:
            self._description_parts.append(data)
        if self._capturing_tag is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capturing_tag:
            text = " ".join("".join(self._text_parts).split())
            if tag == "h1" and not self.make:
                self.make, self.model = split_make_and_model(text)
            elif tag == "h3" and not self.trim:
                self.trim = text
            elif tag == "dt":
                self._definition_label = text
            elif tag == "dd":
                if self._definition_label == "Køretøjstype":
                    self.vehicle_types.append(text)
                elif self._definition_label == "Leasingform":
                    self.leasing_forms.append(text)
                elif self._definition_label in {"Drivmiddel", "Brændstof"}:
                    self.drivetrain_evidence.append(
                        parse_drivetrain_evidence(
                            text, f"{self._definition_label} {text}"
                        )
                    )
                self._definition_label = ""
            elif tag == "span":
                label, value = split_vehicle_short_spec(text)
                if label == "Brændstof" and value is not None:
                    self.drivetrain_evidence.append(
                        parse_drivetrain_evidence(value, text)
                    )
            elif tag == "h2" and "Privatleasing" in text:
                self.private_eligibility_fragment = text
            elif tag == "li":
                label, value = split_private_term(text)
                if label and value:
                    self._private_terms[label] = value
            self._capturing_tag = None
            self._text_parts = []
        if self._private_configuration_depth == self._depth:
            if self._private_terms:
                self.private_configurations.append(
                    (self._private_configuration_id, self._private_terms)
                )
            self._private_configuration_depth = None
            self._private_configuration_id = None
            self._private_terms = {}
        if self._vehicle_info_depth == self._depth:
            self._vehicle_info_depth = None
        if self._vehicle_gallery_depth == self._depth:
            self._vehicle_gallery_depth = None
        if self._vehicle_short_specs_depth == self._depth:
            self._vehicle_short_specs_depth = None
        if self._private_tab_depth == self._depth:
            self._private_tab_depth = None
        if self._description_depth == self._depth:
            self.description_text = " ".join(" ".join(self._description_parts).split())
            self._description_depth = None
            self._description_parts = []
        self._depth -= 1

    def _in_vehicle_info(self) -> bool:
        return self._vehicle_info_depth is not None

    def _in_vehicle_gallery(self) -> bool:
        return self._vehicle_gallery_depth is not None

    def _in_vehicle_short_specs(self) -> bool:
        return self._vehicle_short_specs_depth is not None

    def _in_private_tab(self) -> bool:
        return self._private_tab_depth is not None


def split_make_and_model(value: str) -> tuple[str, str]:
    for make in ("Aston Martin", "Alfa Romeo", "Land Rover", "Mercedes-Benz"):
        if value.startswith(f"{make} "):
            return make, value.removeprefix(make).strip()
    pieces = value.split(maxsplit=1)
    if len(pieces) != 2:
        return value, ""
    return pieces[0], pieces[1]


def split_vehicle_short_spec(value: str) -> tuple[str | None, str | None]:
    label = "Brændstof:"
    if not value.startswith(label):
        return None, None
    return "Brændstof", value.removeprefix(label).strip()


def parse_drivetrain_evidence(
    value: str, source_wording: str
) -> FleasingDrivetrainEvidence:
    drivetrain_values = {
        "benzin": "gasoline",
        "diesel": "diesel",
        "el": "battery_electric",
        "elbil": "battery_electric",
        "elektrisk": "battery_electric",
    }
    return FleasingDrivetrainEvidence(
        normalized_value=drivetrain_values.get(value.casefold().strip(), "unsupported"),
        source_wording=source_wording,
    )


def split_private_term(value: str) -> tuple[str | None, str | None]:
    labels = ("Ydelse pr. måned", "Udbetaling", "Restværdi", "Leasingperiode")
    for label in labels:
        if value.startswith(label):
            return label, value.removeprefix(label).strip()
    return None, None
