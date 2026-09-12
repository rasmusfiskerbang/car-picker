from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Annotated, Any, Generic, Literal, TypeVar, cast
from urllib.parse import urljoin, urlparse

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

from car_picker.fleasing import StructuralSourceError, TextHttpClient
from car_picker.provider_contract import (
    evidence,
    source_document,
    unavailable_fact,
)


PARSER_VERSION = "terminalen-model-price-v3"
NAVIGATION_STATE_KEY = "G./api/navigation?culture=da-DK&levels=10"
AUDITED_IONIQ_5_MODEL_IDS = frozenset({"HY_IONIQ5", "HY_IONIQ5_NE_DK_IONIQ5_MY27"})
AUDITED_BATTERY_ELECTRIC_MODELS = frozenset(
    {"inster", "kona electric", "ioniq 5", "ioniq 6", "ioniq 9"}
)


@dataclass(frozen=True)
class PrivateConsumerAmountAssessment:
    """One typed ADR-0002 result shared by events and Candidate admission."""

    amount_basis: Literal["including_vat", "excluding_vat", "not_stated"]
    admissible: bool
    evidence_wording: str


def _validate_terminalen_source_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(
            "Terminalen boundary URLs must be absolute HTTPS URLs without credentials or fragments"
        )
    return value


TerminalenSourceUrl = Annotated[
    str,
    StringConstraints(min_length=1),
    AfterValidator(_validate_terminalen_source_url),
]
TerminalenBoundaryState = Literal[
    "known", "not_stated", "unclear", "conflicting", "not_applicable"
]
BoundaryValue = TypeVar("BoundaryValue")


class _TerminalenBoundaryModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: (
            name.split("_")[0]
            + "".join(part.capitalize() for part in name.split("_")[1:])
        ),
        populate_by_name=True,
        extra="forbid",
        strict=True,
    )


class TerminalenBoundaryEvidence(_TerminalenBoundaryModel):
    source_url: TerminalenSourceUrl
    wording: str = Field(min_length=1)


class TerminalenBoundaryVehicle(_TerminalenBoundaryModel):
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)


class TerminalenBoundaryServiceArrangement(_TerminalenBoundaryModel):
    category: str = Field(min_length=1)
    treatment: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class TerminalenBoundaryFact(_TerminalenBoundaryModel, Generic[BoundaryValue]):
    state: TerminalenBoundaryState
    value: BoundaryValue | None = None
    evidence: TerminalenBoundaryEvidence

    @model_validator(mode="after")
    def known_values_are_present(self) -> "TerminalenBoundaryFact[BoundaryValue]":
        if self.state == "known" and self.value is None:
            raise ValueError("known Terminalen facts must carry a value")
        if self.state != "known" and self.value is not None:
            raise ValueError("unavailable Terminalen facts must not carry a value")
        return self


class TerminalenBoundaryMoneyFact(_TerminalenBoundaryModel):
    state: TerminalenBoundaryState
    value_dkk: int | float | None = None
    scope: Literal["normal_completion_base_cash_flows"] | None = None
    evidence: TerminalenBoundaryEvidence

    @model_validator(mode="after")
    def known_values_are_present(self) -> "TerminalenBoundaryMoneyFact":
        has_value = self.value_dkk is not None
        if self.state == "known" and not has_value:
            raise ValueError("known Terminalen money facts must carry a value")
        if self.state != "known" and has_value:
            raise ValueError(
                "unavailable Terminalen money facts must not carry a value"
            )
        if self.state != "known" and self.scope is not None:
            raise ValueError(
                "unavailable Terminalen money facts must not carry a scope"
            )
        return self


class TerminalenBoundaryCashFlowEvent(_TerminalenBoundaryModel):
    meaning: str = Field(min_length=1)
    direction: Literal["payment", "receipt"]
    amount_dkk: int | float | None
    amount_basis: Literal["including_vat", "excluding_vat", "not_stated"]
    timing: Literal["acceptance_to_handover", "recurring", "normal_completion_end"]
    recurrence_count: int | None
    refundability: Literal["refundable", "not_refundable", "not_stated"]
    included_in_base: Literal[True]
    evidence: TerminalenBoundaryEvidence


class TerminalenBoundarySourceDocument(_TerminalenBoundaryModel):
    source_url: TerminalenSourceUrl
    content_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    retrieved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TerminalenBoundarySourceMetadata(_TerminalenBoundaryModel):
    parser_version: str = Field(min_length=1)
    documents: list[TerminalenBoundarySourceDocument] = Field(min_length=1)


class TerminalenBoundaryRecord(_TerminalenBoundaryModel):
    """Validated transient Terminalen data crossing into composition."""

    offer_identity: str = Field(min_length=1)
    provider: Literal["Terminalen"]
    provider_source_id: str = Field(min_length=1)
    canonical_offer_url: TerminalenSourceUrl
    source_local_configuration_key: str = Field(min_length=1)
    vehicle_specification: TerminalenBoundaryFact[TerminalenBoundaryVehicle]
    vehicle_drivetrain: TerminalenBoundaryFact[str]
    private_consumer_eligibility: TerminalenBoundaryFact[bool]
    private_consumer_amount_admissibility: TerminalenBoundaryFact[bool]
    passenger_car_scope: TerminalenBoundaryFact[bool]
    current_availability: TerminalenBoundaryFact[bool]
    supported_leasing_form: TerminalenBoundaryFact[
        Literal["financial", "flex", "operational", "hybrid"]
    ]
    provider_form_label: TerminalenBoundaryFact[str]
    advertised_monthly_payment: TerminalenBoundaryMoneyFact
    provider_advertised_aggregate: TerminalenBoundaryMoneyFact
    term_months: TerminalenBoundaryFact[int]
    annual_mileage_km: TerminalenBoundaryFact[int]
    normal_end_mechanism: TerminalenBoundaryFact[str]
    residual_risk_allocation: TerminalenBoundaryFact[str]
    registration_tax_treatment: TerminalenBoundaryFact[JsonValue]
    base_cash_flow_stream: list[TerminalenBoundaryCashFlowEvent] = Field(min_length=1)
    service_arrangements: TerminalenBoundaryFact[
        list[TerminalenBoundaryServiceArrangement]
    ]
    exclusions: TerminalenBoundaryFact[list[TerminalenBoundaryServiceArrangement]]
    exposure_scenarios: TerminalenBoundaryFact[JsonValue]
    source_metadata: TerminalenBoundarySourceMetadata


class TerminalenAdapter:
    """Collect Terminalen's bounded model-price pages and their paired page API data."""

    def __init__(self, http_client: TextHttpClient, retrieved_at: str) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at

    def collect(self, catalogue_url: str) -> list[dict[str, Any]]:
        catalogue_html = self._http_client.get_text(catalogue_url)
        price_urls = model_price_urls(catalogue_html, catalogue_url)
        if not price_urls:
            raise StructuralSourceError(
                "Terminalen catalogue contains no model price pages"
            )
        candidates: list[dict[str, Any]] = []
        for price_url in price_urls:
            page_html = self._http_client.get_text(price_url)
            api_url = model_page_api_url(price_url)
            api_text = self._http_client.get_text(api_url)
            candidates.extend(
                map_model_page(
                    catalogue_url=catalogue_url,
                    catalogue_html=catalogue_html,
                    page_url=price_url,
                    page_html=page_html,
                    api_url=api_url,
                    api_text=api_text,
                    retrieved_at=self._retrieved_at,
                )
            )
        return candidates

    def collect_boundary_records(
        self, catalogue_url: str = "https://www.terminalen.dk/"
    ) -> list[TerminalenBoundaryRecord]:
        """Validate every fetched record before trusted Catalogue composition."""
        return [
            TerminalenBoundaryRecord.model_validate(record)
            for record in self.collect(catalogue_url)
        ]


def model_price_urls(catalogue_html: str, catalogue_url: str) -> list[str]:
    parser = NavigationStateParser()
    parser.feed(catalogue_html)
    parser.close()
    if parser.state_text is None:
        raise StructuralSourceError(
            "Terminalen catalogue is missing its designated navigation state"
        )
    try:
        state = json.loads(parser.state_text)
    except json.JSONDecodeError as error:
        raise StructuralSourceError(
            "Terminalen catalogue navigation state is malformed JSON"
        ) from error
    if not isinstance(state, Mapping):
        raise StructuralSourceError(
            "Terminalen catalogue navigation state is malformed: root must be an object"
        )
    navigation = state.get(NAVIGATION_STATE_KEY)
    if navigation is None:
        raise StructuralSourceError(
            "Terminalen catalogue navigation state is missing its navigation response"
        )
    if not isinstance(navigation, Mapping) or not isinstance(
        navigation.get("body"), list
    ):
        raise StructuralSourceError(
            "Terminalen catalogue navigation state is malformed: "
            "navigation body must be an array"
        )

    origin = urlparse(catalogue_url)
    scope_prefix = (
        "/nye-biler/hyundai/"
        if origin.path == "/terminalen"
        else origin.path.rstrip("/") + "/"
    )
    urls: list[str] = []
    for node in navigation_nodes(navigation["body"]):
        href = node.get("url")
        if node.get("template") != "modelSubpage":
            continue
        if not isinstance(href, str) or not href:
            raise StructuralSourceError(
                "Terminalen catalogue modelSubpage requires a URL"
            )
        url = urljoin(catalogue_url, href)
        parsed = urlparse(url)
        if (
            parsed.scheme == origin.scheme
            and parsed.hostname == origin.hostname
            and parsed.port == origin.port
            and parsed.username is None
            and parsed.password is None
            and parsed.path.startswith(scope_prefix)
            and re.fullmatch(
                f"{re.escape(scope_prefix)}[^/]+/pris-og-udstyr", parsed.path
            )
            and not parsed.query
            and not parsed.fragment
            and url not in urls
        ):
            urls.append(url)
    return urls


def navigation_nodes(value: object) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(value, list):
        for child in value:
            nodes.extend(navigation_nodes(child))
    elif isinstance(value, dict):
        node = cast(dict[str, Any], value)
        nodes.append(node)
        if "children" in node:
            children = node["children"]
            if not isinstance(children, list):
                raise StructuralSourceError(
                    "Terminalen catalogue navigation node children must be an array"
                )
            nodes.extend(navigation_nodes(children))
    else:
        raise StructuralSourceError(
            "Terminalen catalogue navigation children must contain objects"
        )
    return nodes


def model_page_api_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/api/page/url?url={parsed.path}&culture=da-DK"


def map_model_page(
    *,
    catalogue_url: str,
    catalogue_html: str,
    page_url: str,
    page_html: str,
    api_url: str,
    api_text: str,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(api_text)
    except json.JSONDecodeError as error:
        raise StructuralSourceError(
            f"Terminalen page API at {api_url} did not return JSON"
        ) from error
    if (
        not isinstance(payload, Mapping)
        or payload.get("url") != urlparse(page_url).path
    ):
        raise StructuralSourceError(
            "Terminalen page API does not match the same model-price path"
        )
    if payload.get("template") != "modelSubpage":
        raise StructuralSourceError("Terminalen page API is not a model-price page")
    (
        rows,
        private_eligibility_wording,
        provider_form_wording,
        legal_wording,
        end_wording,
    ) = private_lease_rows(payload)
    if not rows:
        return []
    model_id = required_string(payload, "pimModelId")
    vehicle = object_value(payload.get("vehicleData"), "Terminalen vehicleData")
    brand = required_string(vehicle, "brand")
    model = required_string(vehicle, "model")
    vehicle_wording = json.dumps(vehicle, ensure_ascii=False, separators=(",", ":"))
    passenger_car_scope = passenger_car_fact(api_url, model_id, vehicle)
    vehicle_drivetrain = audited_vehicle_drivetrain_fact(api_url, model_id, model)
    current_availability = availability_fact(
        api_url, payload, private_eligibility_wording
    )
    documents = [
        source_document(catalogue_url, catalogue_html, retrieved_at),
        source_document(page_url, page_html, retrieved_at),
        source_document(api_url, api_text, retrieved_at),
    ]
    return [
        map_configuration(
            row,
            page_url=page_url,
            api_url=api_url,
            model_id=model_id,
            brand=brand,
            model=model,
            vehicle_wording=vehicle_wording,
            vehicle_drivetrain=vehicle_drivetrain,
            passenger_car_scope=passenger_car_scope,
            current_availability=current_availability,
            private_eligibility_wording=private_eligibility_wording,
            provider_form_wording=provider_form_wording,
            end_wording=end_wording,
            legal_wording=legal_wording,
            documents=documents,
        )
        for row in rows
    ]


def map_configuration(
    row: Mapping[str, Any],
    *,
    page_url: str,
    api_url: str,
    model_id: str,
    brand: str,
    model: str,
    vehicle_wording: str,
    vehicle_drivetrain: dict[str, Any],
    passenger_car_scope: dict[str, Any],
    current_availability: dict[str, Any],
    private_eligibility_wording: str,
    provider_form_wording: str,
    end_wording: str,
    legal_wording: str,
    documents: list[dict[str, str]],
) -> dict[str, Any]:
    configuration_id = required_string(row, "configurationId")
    wording = required_string(row, "sourceWording")
    monthly = required_int(row, "monthlyPaymentDkk")
    upfront = required_int(row, "upfrontPaymentDkk")
    term = required_int(row, "termMonths")
    aggregate = required_int(row, "aggregatePaymentDkk")
    card_evidence = evidence(api_url, wording)
    vehicle_evidence = evidence(api_url, vehicle_wording)
    vat_assessment = private_consumer_amount_basis(
        combined_wording(wording, legal_wording)
    )
    payment_evidence = evidence(api_url, vat_assessment.evidence_wording)
    mileage = mileage_fact(api_url, legal_wording)
    end_fee = inspection_fee(legal_wording)
    events = [
        event(
            "Udbetaling",
            upfront,
            "acceptance_to_handover",
            1,
            vat_assessment.amount_basis,
            payment_evidence,
        ),
        event(
            "Månedlig ydelse",
            monthly,
            "recurring",
            term,
            vat_assessment.amount_basis,
            payment_evidence,
        ),
    ]
    if end_fee is not None:
        events.append(
            event(
                "Inspektionsgebyr",
                end_fee,
                "normal_completion_end",
                1,
                vat_assessment.amount_basis,
                evidence(api_url, legal_wording),
            )
        )
    candidate = {
        "offerIdentity": f"terminalen:{model_id}:{configuration_id}",
        "provider": "Terminalen",
        "providerSourceId": model_id,
        "canonicalOfferUrl": page_url,
        "sourceLocalConfigurationKey": configuration_id,
        "vehicleSpecification": known(
            {"make": brand, "model": model}, vehicle_evidence
        ),
        "vehicleDrivetrain": vehicle_drivetrain,
        "privateConsumerEligibility": known(
            True,
            evidence(api_url, private_eligibility_wording),
        ),
        "privateConsumerAmountAdmissibility": private_consumer_amount_admissibility_fact(
            api_url, vat_assessment
        ),
        "passengerCarScope": passenger_car_scope,
        "currentAvailability": current_availability,
        "supportedLeasingForm": operational_form_fact(api_url, end_wording),
        "providerFormLabel": known(
            provider_form_wording,
            evidence(api_url, provider_form_wording),
        ),
        "advertisedMonthlyPayment": money(monthly, payment_evidence),
        "providerAdvertisedAggregate": {
            **money(aggregate, card_evidence),
            "scope": "normal_completion_base_cash_flows",
        },
        "termMonths": known(term, card_evidence),
        "annualMileageKm": mileage,
        "normalEndMechanism": normal_end_fact(api_url, end_wording),
        "residualRiskAllocation": residual_risk_fact(api_url, end_wording),
        "registrationTaxTreatment": not_stated(api_url, legal_wording),
        "baseCashFlowStream": events,
        "serviceArrangements": service_arrangements_fact(api_url, legal_wording),
        "exclusions": exclusions_fact(api_url, legal_wording),
        "exposureScenarios": not_stated(api_url, legal_wording),
        "sourceMetadata": {"parserVersion": PARSER_VERSION, "documents": documents},
    }
    return candidate


def event(
    meaning: str,
    amount: int,
    timing: str,
    recurrence_count: int,
    amount_basis: str,
    evidence: dict[str, str],
) -> dict[str, Any]:
    return {
        "meaning": meaning,
        "direction": "payment",
        "amountDkk": amount,
        "amountBasis": amount_basis,
        "timing": timing,
        "recurrenceCount": recurrence_count,
        "refundability": "not_refundable",
        "includedInBase": True,
        "evidence": evidence,
    }


def known(value: JsonValue, evidence: dict[str, str]) -> dict[str, Any]:
    return {"state": "known", "value": value, "evidence": evidence}


def money(value: int, evidence: dict[str, str]) -> dict[str, Any]:
    return {"state": "known", "valueDkk": value, "evidence": evidence}


def not_stated(source_url: str, wording: str) -> dict[str, Any]:
    return unavailable_fact("not_stated", source_url, wording)


def private_lease_rows(
    payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str, str, str, str]:
    grid = list_value(payload.get("grid"), "Terminalen grid")
    rows: list[dict[str, Any]] = []
    private_eligibility_wording = ""
    provider_form_wording = ""
    legal_wording = ""
    end_wording = ""
    in_private_leasing = False
    price_block_found = False
    for section in grid:
        for content in list_value(
            object_value(section, "Terminalen grid section").get("content"),
            "Terminalen grid content",
        ):
            block = object_value(content, "Terminalen content block")
            if block.get("alias") == "anchor":
                in_private_leasing = block.get("anchorId") == "privatleasing"
                if in_private_leasing:
                    provider_form_wording = "Privatleasing"
                    private_eligibility_wording = json.dumps(
                        {"alias": "anchor", "anchorId": "privatleasing"},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                continue
            if not in_private_leasing:
                continue
            if block.get("alias") == "imagetextpicker":
                columns = block.get("columns")
                if not isinstance(columns, list):
                    raise StructuralSourceError(
                        "Terminalen private lease card block requires columns"
                    )
                column_values = [
                    object_value(column, "Terminalen leasing column")
                    for column in columns
                ]
                column_texts = [
                    html_text(required_string(value, "text")) for value in column_values
                ]
                is_price_block = any(
                    re.search(r"kr\.?\s*/\s*md", text, flags=re.IGNORECASE)
                    and "Samlet betaling i perioden" in text
                    for text in column_texts
                )
                if not price_block_found and is_price_block:
                    price_block_found = True
                    for value, text in zip(column_values, column_texts, strict=True):
                        rows.append(
                            lease_row(
                                required_string(value, "title"),
                                text,
                            )
                        )
                    continue
                for value, text in zip(column_values, column_texts, strict=True):
                    if required_string(value, "title") == "Privatleasing":
                        end_wording = text
            if block.get("alias") == "richtext":
                text = html_text(required_string(block, "text"))
                legal_wording = f"{legal_wording}; {text}" if legal_wording else text
    return (
        rows,
        private_eligibility_wording,
        provider_form_wording,
        legal_wording,
        end_wording,
    )


def lease_row(title: str, text: str) -> dict[str, Any]:
    monthly = money_in(text, r"([\d.]+)\s*kr\.?\s*/\s*md")
    upfront = optional_money_in(text, r"Udbetaling:\s*([\d.]+)\s*kr")
    if upfront is None:
        upfront = money_in(text, r"^([\d.]+)\s*kr\.")
    term = integer_in(text, r"Periode:\s*(\d+)\s*mdr")
    aggregate = money_in(text, r"Samlet betaling i perioden:\s*([\d.]+)\s*kr")
    configuration_values = json.dumps(
        {
            "title": title.strip(),
            "monthlyPaymentDkk": monthly,
            "upfrontPaymentDkk": upfront,
            "termMonths": term,
            "aggregatePaymentDkk": aggregate,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return {
        "configurationId": f"private-{hashlib.sha256(configuration_values.encode('utf-8')).hexdigest()[:12]}",
        "trim": title,
        "monthlyPaymentDkk": monthly,
        "upfrontPaymentDkk": upfront,
        "termMonths": term,
        "aggregatePaymentDkk": aggregate,
        "sourceWording": text,
    }


def html_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value).replace("&nbsp;", " ").split())


def money_in(value: str, pattern: str) -> int:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    if match is None:
        raise StructuralSourceError(
            "Terminalen leasing card is missing an explicit DKK amount"
        )
    return int(match.group(1).replace(".", ""))


def optional_money_in(value: str, pattern: str) -> int | None:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    return None if match is None else int(match.group(1).replace(".", ""))


def integer_in(value: str, pattern: str) -> int:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    if match is None:
        raise StructuralSourceError(
            "Terminalen leasing card is missing an explicit term"
        )
    return int(match.group(1))


def private_consumer_amount_basis(wording: str) -> PrivateConsumerAmountAssessment:
    """Apply ADR-0002 after the source establishes private-consumer eligibility."""
    states_in_wording: set[str] = set()
    if re.search(r"\binkl(?:\.|usive)?\s*moms\b", wording, flags=re.IGNORECASE):
        states_in_wording.add("including_vat")
    if re.search(
        r"(?:\b(?:ekskl(?:\.|usive)?|excl(?:\.|usive|uding)?|ex)\s*moms\b"
        r"|\buden\s+moms\b"
        r"|\b(?:ikke|ej)\s+inkl(?:\.|usive)?\s*moms\b"
        r"|\bmoms\s+(?:er\s+)?(?:ikke|ej)\s+inkluderet\b)",
        wording,
        flags=re.IGNORECASE,
    ):
        states_in_wording.add("excluding_vat")

    if len(states_in_wording) > 1:
        return PrivateConsumerAmountAssessment(
            amount_basis="not_stated",
            admissible=False,
            evidence_wording=wording,
        )
    if states_in_wording == {"excluding_vat"}:
        return PrivateConsumerAmountAssessment(
            amount_basis="excluding_vat",
            admissible=False,
            evidence_wording=wording,
        )
    return PrivateConsumerAmountAssessment(
        amount_basis="including_vat",
        admissible=True,
        evidence_wording=wording,
    )


def private_consumer_amount_admissibility_fact(
    source_url: str, assessment: PrivateConsumerAmountAssessment
) -> dict[str, Any]:
    if assessment.admissible:
        return known(True, evidence(source_url, assessment.evidence_wording))
    return unavailable_fact("conflicting", source_url, assessment.evidence_wording)


def combined_wording(card_wording: str, legal_wording: str) -> str:
    return card_wording if not legal_wording else f"{card_wording}; {legal_wording}"


def combined_evidence(
    source_url: str, card_wording: str, legal_wording: str
) -> dict[str, str]:
    return evidence(source_url, combined_wording(card_wording, legal_wording))


def mileage_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(
        r"(\d{1,3}(?:\.\d{3})*)\s*km\s*/\s*år", legal_wording, flags=re.IGNORECASE
    )
    if match is None:
        return not_stated(source_url, legal_wording)
    return known(
        int(match.group(1).replace(".", "")),
        evidence(source_url, match.group(0)),
    )


def passenger_car_fact(
    source_url: str, model_id: str, vehicle: Mapping[str, Any]
) -> dict[str, Any]:
    vehicle_type = vehicle.get("vehicleType")
    if vehicle_type is None:
        body_type = vehicle.get("bodyType")
        model = vehicle.get("model")
        if (
            model_id in AUDITED_IONIQ_5_MODEL_IDS
            and isinstance(model, str)
            and model.casefold() == "ioniq 5"
            and isinstance(body_type, str)
            and body_type.casefold() == "suv"
        ):
            return known(
                True,
                evidence(
                    source_url,
                    json.dumps(
                        {"bodyType": body_type},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ),
            )
        if body_type is not None:
            return unclear(
                source_url,
                json.dumps(
                    {"bodyType": body_type},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
        return not_stated(source_url, json.dumps(vehicle, ensure_ascii=False))
    if not isinstance(vehicle_type, str):
        return unclear(source_url, json.dumps({"vehicleType": vehicle_type}))
    if vehicle_type.casefold() == "personbil":
        return known(
            True,
            {
                "sourceUrl": source_url,
                "wording": json.dumps(
                    {"vehicleType": vehicle_type},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        )
    return unclear(source_url, vehicle_type)


def audited_vehicle_drivetrain_fact(
    source_url: str, model_id: str, model: str
) -> dict[str, Any]:
    normalized_model = " ".join(model.casefold().split())
    wording = json.dumps(
        {
            "pimModelId": model_id,
            "model": model,
            "drivetrain": "battery_electric",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if normalized_model in AUDITED_BATTERY_ELECTRIC_MODELS:
        return known("battery_electric", evidence(source_url, wording))
    return unavailable_fact("not_stated", source_url, wording)


def availability_fact(
    source_url: str,
    payload: Mapping[str, Any],
    private_eligibility_wording: str,
) -> dict[str, Any]:
    is_current = payload.get("isCurrent")
    wording = json.dumps(
        {"isCurrent": is_current},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if is_current is None:
        page_identity = {
            "url": payload.get("url"),
            "template": payload.get("template"),
        }
        return known(
            True,
            evidence(
                source_url,
                (
                    f"{json.dumps(page_identity, ensure_ascii=False, separators=(',', ':'))}; "
                    f"{private_eligibility_wording}"
                ),
            ),
        )
    if is_current is True:
        return known(True, evidence(source_url, wording))
    return unclear(source_url, wording)


def unclear(source_url: str, wording: str) -> dict[str, Any]:
    return {
        "state": "unclear",
        "evidence": evidence(source_url, wording),
    }


def inspection_fee(legal_wording: str) -> int | None:
    amount = re.search(r"gebyr på\s*([\d.]+)\s*kr", legal_wording, flags=re.IGNORECASE)
    if amount is None or not re.search(
        r"Gebyret opkræves sammen med sidste ydelse", legal_wording, flags=re.IGNORECASE
    ):
        return None
    return int(amount.group(1).replace(".", ""))


def normal_end_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    if re.search(r"afleverer du bilen", end_wording, flags=re.IGNORECASE):
        return known("return_to_provider", evidence(source_url, end_wording))
    return not_stated(source_url, end_wording)


def residual_risk_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    if re.search(r"ikke .*værditab", end_wording, flags=re.IGNORECASE):
        return known("provider", evidence(source_url, end_wording))
    return not_stated(source_url, end_wording)


def operational_form_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    has_return = normal_end_fact(source_url, end_wording)["state"] == "known"
    has_provider_risk = residual_risk_fact(source_url, end_wording)["state"] == "known"
    if has_return and has_provider_risk:
        return known("operational", evidence(source_url, end_wording))
    return not_stated(source_url, end_wording)


def service_arrangements_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(
        r"inkl\.\s*(alle fabriksanbefalede services)",
        legal_wording,
        flags=re.IGNORECASE,
    )
    if match is None:
        return not_stated(source_url, legal_wording)
    return known(
        [
            {
                "category": "manufacturer_recommended_service",
                "treatment": "included",
                "scope": match.group(1),
            }
        ],
        evidence(source_url, match.group(0)),
    )


def exclusions_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(
        r"Prisen er ekskl\.\s*([^.]*)", legal_wording, flags=re.IGNORECASE
    )
    if match is None:
        return not_stated(source_url, legal_wording)
    categories = (
        ("co2_fee", "CO2-afgift"),
        ("insurance", "forsikring"),
        ("tyres", "ekstra dæk"),
    )
    return known(
        [
            {"category": category, "treatment": "excluded", "scope": source_term}
            for category, source_term in categories
            if source_term.casefold() in match.group(1).casefold()
        ],
        evidence(source_url, match.group(0)),
    )


def required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise StructuralSourceError(f"Terminalen API requires {key}")
    return item


def required_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool) or item < 0:
        raise StructuralSourceError(
            f"Terminalen API requires a non-negative integer {key}"
        )
    return item


def object_value(value: JsonValue, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise StructuralSourceError(f"{name} must be an object")
    return value


def list_value(value: JsonValue, name: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise StructuralSourceError(f"{name} must be an array")
    return value


class NavigationStateParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_navigation_state = False
        self._state_parts: list[str] = []
        self.state_text: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if (
            tag == "script"
            and attributes.get("id") == "terminalen-ncg-state"
            and attributes.get("type") == "application/json"
        ):
            self._in_navigation_state = True

    def handle_data(self, data: str) -> None:
        if self._in_navigation_state:
            self._state_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_navigation_state:
            self.state_text = "".join(self._state_parts)
            self._in_navigation_state = False
