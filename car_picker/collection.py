"""Production Provider Adapter composition for the strict Catalogue seam."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Protocol, TypeVar, cast
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from car_picker import (
    BaseCashFlowEvent,
    CandidateAdmissionFacts,
    CandidateEvidence,
    CatalogueCandidate,
    CatalogueOffer,
    KnownFact,
    ProviderAdapter,
    ProviderId,
    QuarantineReason,
)
from car_picker.fleasing import (
    FleasingAdapter,
    FleasingBoundaryCashFlowEvent,
    FleasingBoundaryEvidence,
    FleasingBoundaryFact,
    FleasingBoundaryRecord,
    TextHttpClient,
)
from car_picker.provider_scope import (
    FLEASING_CATALOGUE_URL,
    TERMINALEN_CATALOGUE_URL,
)
from car_picker.terminalen import (
    TerminalenAdapter,
    TerminalenBoundaryEvidence,
    TerminalenBoundaryFact,
    TerminalenBoundaryMoneyFact,
    TerminalenBoundaryRecord,
    TerminalenBoundaryCashFlowEvent,
    TerminalenBoundaryServiceArrangement,
    TerminalenBoundaryVehicle,
)


class _CandidateSourceFact(Protocol):
    @property
    def state(self) -> str: ...

    @property
    def value(self) -> object | None: ...

    @property
    def evidence(self) -> object: ...


BoundaryValue = TypeVar("BoundaryValue")


class UrlLibHttpClient(TextHttpClient):
    """HTTP boundary for a designated source; fetched documents are never persisted."""

    def get_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "car-picker owner refresh"})
        with urlopen(  # noqa: S310 - source URLs are fixed by Provider composition.
            request, timeout=30
        ) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)


class FleasingProviderAdapter:
    """Map Fleasing source records to strict Candidates at the ingress."""

    provider_id: ProviderId = "fleasing"

    def __init__(
        self,
        http_client: TextHttpClient,
        retrieved_at: str,
        catalogue_url: str = FLEASING_CATALOGUE_URL,
    ) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at
        self._catalogue_url = catalogue_url

    def collect(self) -> list[CatalogueCandidate]:
        records = FleasingAdapter(
            self._http_client, retrieved_at=self._retrieved_at
        ).collect_boundary_records(self._catalogue_url)
        return [_map_fleasing_candidate(record) for record in records]


class TerminalenProviderAdapter:
    """Map Terminalen source records to strict Candidates at the ingress."""

    provider_id: ProviderId = "terminalen"

    def __init__(
        self,
        http_client: TextHttpClient,
        retrieved_at: str,
        catalogue_url: str = TERMINALEN_CATALOGUE_URL,
    ) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at
        self._catalogue_url = catalogue_url

    def collect(self) -> list[CatalogueCandidate]:
        records = TerminalenAdapter(
            self._http_client, retrieved_at=self._retrieved_at
        ).collect_boundary_records(self._catalogue_url)
        return [_map_terminalen_candidate(record) for record in records]


_STATIC_PROVIDER_ADAPTER_FACTORIES: Mapping[
    ProviderId, Callable[[TextHttpClient, str], ProviderAdapter]
] = MappingProxyType(
    {
        "fleasing": FleasingProviderAdapter,
        "terminalen": TerminalenProviderAdapter,
    }
)


def production_provider_adapters(
    http_client: TextHttpClient | None = None,
    *,
    retrieved_at: str | None = None,
) -> tuple[ProviderAdapter, ...]:
    """Compose the statically supported Provider Adapters in source order."""
    client = http_client or UrlLibHttpClient()
    source_time = retrieved_at or _now()
    return tuple(
        factory(client, source_time)
        for factory in _STATIC_PROVIDER_ADAPTER_FACTORIES.values()
    )


def _map_fleasing_candidate(record: FleasingBoundaryRecord) -> CatalogueCandidate:
    """Map Fleasing's source record to the strict Candidate at its ingress."""
    identity = record.offer_identity
    source_url = _normalized_https_url(record.canonical_offer_url)
    admission_facts = CandidateAdmissionFacts.model_validate(
        {
            "privateConsumerEligibility": _candidate_source_fact(
                record.private_consumer_eligibility,
                source_url,
                "Fleasing private-consumer eligibility was not established.",
            ),
            "privateConsumerAmountAdmissibility": _candidate_source_fact(
                record.private_consumer_amount_admissibility,
                source_url,
                "Fleasing private-consumer amount admissibility was not established.",
            ),
            "passengerCarScope": _candidate_source_fact(
                record.passenger_car_scope,
                source_url,
                "Fleasing passenger-car scope was not established.",
            ),
            "currentAvailability": _candidate_source_fact(
                record.current_availability,
                source_url,
                "Fleasing current availability was not established.",
            ),
            "supportedLeasingForm": _candidate_source_fact(
                record.supported_leasing_form,
                source_url,
                "Fleasing leasing form was not established.",
            ),
        }
    )
    candidate = CatalogueCandidate.model_validate(
        {
            "offerIdentity": identity,
            "providerId": "fleasing",
            "canonicalSourceUrl": source_url,
            "admissionFacts": admission_facts,
            "offer": _map_fleasing_offer(record, identity, source_url),
        }
    )
    candidate.admission_evidence_failures.extend(
        _fleasing_admission_evidence_failures(record, source_url)
    )
    return candidate


def _map_terminalen_candidate(record: TerminalenBoundaryRecord) -> CatalogueCandidate:
    """Map Terminalen's source record to the strict Candidate at its ingress."""
    identity = record.offer_identity
    source_url = _normalized_https_url(record.canonical_offer_url)
    admission_facts = CandidateAdmissionFacts.model_validate(
        {
            "privateConsumerEligibility": _candidate_source_fact(
                record.private_consumer_eligibility,
                source_url,
                "Terminalen private-consumer eligibility was not established.",
            ),
            "privateConsumerAmountAdmissibility": _candidate_source_fact(
                record.private_consumer_amount_admissibility,
                source_url,
                "Terminalen private-consumer amount admissibility was not established.",
            ),
            "passengerCarScope": _candidate_source_fact(
                record.passenger_car_scope,
                source_url,
                "Terminalen passenger-car scope was not established.",
            ),
            "currentAvailability": _candidate_source_fact(
                record.current_availability,
                source_url,
                "Terminalen current availability was not established.",
            ),
            "supportedLeasingForm": _candidate_source_fact(
                record.supported_leasing_form,
                source_url,
                "Terminalen leasing form was not established.",
            ),
        }
    )
    return CatalogueCandidate.model_validate(
        {
            "offerIdentity": identity,
            "providerId": "terminalen",
            "canonicalSourceUrl": source_url,
            "admissionFacts": admission_facts,
            "offer": _map_terminalen_offer(record, identity, source_url),
        }
    )


def _map_fleasing_offer(
    record: FleasingBoundaryRecord, identity: str, source_url: str
) -> CatalogueOffer | None:
    vehicle = _known_fleasing_vehicle(record.vehicle_specification)
    form = _known_fleasing_leasing_form(record.supported_leasing_form)
    term = _fleasing_known_source_value(record.term_months)
    if (
        vehicle is None
        or form is None
        or not isinstance(term, int)
        or isinstance(term, bool)
        or term <= 0
    ):
        return None
    events = _strict_cash_flow_events(
        record.base_cash_flow_stream,
        term,
    )
    if events is None:
        return None
    return _strict_offer(
        identity=identity,
        provider_id="fleasing",
        source_url=source_url,
        vehicle=_fleasing_vehicle_specification(vehicle),
        supported_form=form,
        provider_form_label=_fleasing_form_label(form),
        term=term,
        annual_mileage=_fleasing_strict_offer_fact(record.annual_mileage_km),
        normal_end=_fleasing_strict_offer_fact(record.normal_end_mechanism),
        residual_risk=_fleasing_strict_offer_fact(record.residual_risk_allocation),
        service_arrangements=_fleasing_strict_offer_fact(record.service_arrangements),
        image_urls=list(record.image_urls),
        events=events,
        advertised_total={"state": "not_stated"},
    )


def _map_terminalen_offer(
    record: TerminalenBoundaryRecord, identity: str, source_url: str
) -> CatalogueOffer | None:
    vehicle = record.vehicle_specification.value
    drivetrain = _known_terminalen_value(record.vehicle_drivetrain)
    form = _known_terminalen_value(record.supported_leasing_form)
    provider_form_label = _known_terminalen_value(record.provider_form_label)
    term = _known_terminalen_value(record.term_months)
    if (
        record.vehicle_specification.state != "known"
        or drivetrain != "battery_electric"
        or form is None
        or provider_form_label is None
        or term is None
        or term <= 0
    ):
        return None
    events = _strict_cash_flow_events(
        record.base_cash_flow_stream,
        term,
    )
    if events is None:
        return None
    vehicle_specification = _terminalen_vehicle_specification(vehicle, drivetrain)
    if vehicle_specification is None:
        return None
    return _strict_offer(
        identity=identity,
        provider_id="terminalen",
        source_url=source_url,
        vehicle=vehicle_specification,
        supported_form=form,
        provider_form_label=provider_form_label,
        term=term,
        annual_mileage=_strict_terminalen_offer_fact(record.annual_mileage_km),
        normal_end=_strict_terminalen_offer_fact(record.normal_end_mechanism),
        residual_risk=_strict_terminalen_offer_fact(record.residual_risk_allocation),
        service_arrangements=_terminalen_service_arrangements(
            record.service_arrangements
        ),
        image_urls=list(record.image_urls),
        events=events,
        advertised_total=_strict_terminalen_money_fact(
            record.provider_advertised_aggregate
        ),
    )


def _strict_offer(
    *,
    identity: str,
    provider_id: ProviderId,
    source_url: str,
    vehicle: dict[str, object],
    supported_form: str,
    provider_form_label: str,
    term: int,
    annual_mileage: dict[str, object],
    normal_end: dict[str, object],
    residual_risk: dict[str, object],
    service_arrangements: dict[str, object],
    image_urls: list[str],
    events: list[BaseCashFlowEvent],
    advertised_total: dict[str, object],
) -> CatalogueOffer:
    calculated_total, calculated_monthly = _strict_calculated_results(events, term)
    return CatalogueOffer.model_validate(
        {
            "offerIdentity": identity,
            "providerId": provider_id,
            "canonicalOfferUrl": source_url,
            "vehicleSpecification": vehicle,
            "imageUrls": image_urls,
            "supportedLeasingForm": supported_form,
            "providerFormLabel": provider_form_label,
            "termMonths": term,
            "annualMileageKm": annual_mileage,
            "normalEndMechanism": normal_end,
            "residualRiskAllocation": residual_risk,
            "serviceArrangements": service_arrangements,
            "baseCashFlowStream": [
                event.model_dump(mode="json", by_alias=True) for event in events
            ],
            "advertisedTotal": advertised_total,
            "calculatedTotal": calculated_total,
            "calculatedMonthlyTotal": calculated_monthly,
        }
    )


def _candidate_source_fact(
    raw_fact: _CandidateSourceFact, fallback_source_url: str, fallback_wording: str
) -> dict[str, object]:
    state = raw_fact.state
    value = raw_fact.value
    evidence = raw_fact.evidence
    if not isinstance(evidence, (FleasingBoundaryEvidence, TerminalenBoundaryEvidence)):
        raise ValueError("provider boundary fact has invalid evidence")
    source_url = _normalized_https_url(evidence.source_url)
    wording = evidence.wording.strip()
    evidence = CandidateEvidence.model_validate(
        {"sourceUrl": source_url, "wording": wording}
    )
    if state == "known" and value is not None:
        return {"state": state, "value": value, "evidence": evidence}
    return {
        "state": "not_stated" if state == "known" else state,
        "evidence": evidence,
    }


def _fleasing_admission_evidence_failures(
    record: FleasingBoundaryRecord, fallback_source_url: str
) -> list[QuarantineReason]:
    failures: list[QuarantineReason] = []
    if _known_fleasing_vehicle(record.vehicle_specification) is None:
        vehicle_state = record.vehicle_specification.state
        failures.append(
            _fleasing_quarantine_reason(
                criterion="candidate_shape",
                state=(
                    vehicle_state
                    if vehicle_state in {"not_stated", "unclear", "conflicting"}
                    else "unclear"
                ),
                code="candidate-shape.vehicle-kind-unknown",
                raw_evidence=record.vehicle_specification.evidence,
                fallback_source_url=fallback_source_url,
                fallback_excerpt=(
                    "Fleasing did not establish a supported first-party drivetrain."
                ),
            )
        )

    for criterion, payment, code, fallback_excerpt in (
        (
            "advertised_monthly_payment",
            record.advertised_monthly_payment,
            "advertised-monthly-payment.vat-conflicting",
            "Fleasing private monthly payment has a conflicting VAT basis.",
        ),
        (
            "upfront_payment",
            record.upfront_payment,
            "upfront-payment.vat-conflicting",
            "Fleasing private upfront payment has a conflicting VAT basis.",
        ),
    ):
        if payment.state != "conflicting":
            continue
        failures.append(
            _fleasing_quarantine_reason(
                criterion=criterion,
                state="conflicting",
                code=code,
                raw_evidence=payment.evidence,
                fallback_source_url=fallback_source_url,
                fallback_excerpt=fallback_excerpt,
            )
        )

    for failure in record.configuration_identity_failures:
        failures.append(
            _fleasing_quarantine_reason(
                criterion="offer_identity",
                state=failure.state,
                code=f"offer-identity.{failure.code.replace('_', '-')}",
                raw_evidence=None,
                fallback_source_url=fallback_source_url,
                fallback_excerpt=(
                    "Fleasing source-local configuration identity was "
                    f"{failure.code.replace('_', ' ')}."
                ),
            )
        )
    return failures


def _fleasing_quarantine_reason(
    *,
    criterion: str,
    state: str,
    code: str,
    raw_evidence: FleasingBoundaryEvidence | None,
    fallback_source_url: str,
    fallback_excerpt: str,
) -> QuarantineReason:
    source_url = fallback_source_url
    excerpt = fallback_excerpt
    if raw_evidence is not None:
        source_url = _normalized_https_url(raw_evidence.source_url)
        excerpt = raw_evidence.wording.strip()[:500]
    return QuarantineReason.model_validate(
        {
            "criterion": criterion,
            "state": state,
            "code": code,
            "evidence": [{"sourceUrl": source_url, "excerpt": excerpt}],
        }
    )


def _fleasing_known_source_value(raw_fact: FleasingBoundaryFact) -> object | None:
    if raw_fact.state != "known":
        return None
    return raw_fact.value


def _known_fleasing_leasing_form(
    raw_fact: FleasingBoundaryFact,
) -> str | None:
    value = _fleasing_known_source_value(raw_fact)
    if value in {"financial", "flex", "operational", "hybrid"}:
        return cast(str, value)
    return None


def _known_fleasing_vehicle(
    raw_fact: FleasingBoundaryFact,
) -> Mapping[str, object] | None:
    value = _fleasing_known_source_value(raw_fact)
    if not isinstance(value, Mapping):
        return None
    make = value.get("make")
    model = value.get("model")
    drivetrain = value.get("drivetrain")
    if (
        not isinstance(make, str)
        or not make.strip()
        or not isinstance(model, str)
        or not model.strip()
        or drivetrain not in {"gasoline", "diesel", "battery_electric"}
    ):
        return None
    return cast(Mapping[str, object], value)


def _fleasing_strict_offer_fact(
    raw_fact: FleasingBoundaryFact,
) -> dict[str, object]:
    if raw_fact.state == "known":
        return {"state": "known", "value": raw_fact.value}
    return {"state": raw_fact.state}


def _known_terminalen_value(
    raw_fact: TerminalenBoundaryFact[BoundaryValue],
) -> BoundaryValue | None:
    if raw_fact.state != "known":
        return None
    return raw_fact.value


def _strict_terminalen_offer_fact(
    raw_fact: TerminalenBoundaryFact[BoundaryValue],
) -> dict[str, object]:
    if raw_fact.state == "known":
        return {"state": "known", "value": raw_fact.value}
    return {"state": raw_fact.state}


def _strict_terminalen_money_fact(
    raw_fact: TerminalenBoundaryMoneyFact,
) -> dict[str, object]:
    if raw_fact.state == "known":
        return {"state": "known", "value": {"amountDkk": raw_fact.value_dkk}}
    return {"state": raw_fact.state}


def _fleasing_vehicle_specification(
    vehicle: Mapping[str, object],
) -> dict[str, object]:
    shared = _shared_vehicle_specification(vehicle)
    drivetrain = vehicle["drivetrain"]
    if drivetrain == "battery_electric":
        return {
            "kind": "battery_electric",
            **shared,
            "batteryCapacity": {"state": "not_stated"},
            "wltpRangeKm": {"state": "not_stated"},
            "maxChargingPower": {"state": "not_stated"},
            "chargingTime10To80Minutes": {"state": "not_stated"},
        }
    if drivetrain not in {"gasoline", "diesel"}:
        raise ValueError("Fleasing vehicle kind requires supported drivetrain evidence")
    return {
        "kind": "combustion",
        **shared,
        "fuelType": drivetrain,
        "fuelEfficiencyKmPerLiter": {"state": "not_stated"},
    }


def _terminalen_vehicle_specification(
    vehicle: TerminalenBoundaryVehicle | None, drivetrain: str | None
) -> dict[str, object] | None:
    if vehicle is None:
        return None
    shared = _shared_vehicle_specification(vehicle)
    if drivetrain == "battery_electric":
        return {
            "kind": "battery_electric",
            **shared,
            "batteryCapacity": {"state": "not_stated"},
            "wltpRangeKm": {"state": "not_stated"},
            "maxChargingPower": {"state": "not_stated"},
            "chargingTime10To80Minutes": {"state": "not_stated"},
        }
    return None


def _shared_vehicle_specification(
    vehicle: Mapping[str, object] | TerminalenBoundaryVehicle,
) -> dict[str, object]:
    if isinstance(vehicle, TerminalenBoundaryVehicle):
        make = vehicle.make
        model = vehicle.model
        trim = None
    else:
        make = vehicle["make"]
        model = vehicle["model"]
        trim = vehicle.get("trim")
    return {
        "make": make,
        "model": model,
        "trim": {"state": "known", "value": trim}
        if isinstance(trim, str) and trim.strip()
        else {"state": "not_stated"},
        "modelYear": {"state": "not_stated"},
        "firstRegistrationYear": {"state": "not_stated"},
        "bodyStyle": {"state": "not_stated"},
        "odometerKm": {"state": "not_stated"},
    }


def _looks_battery_electric(model: str) -> bool:
    normalized = model.casefold().strip()
    return normalized in {
        "i4",
        "inster",
        "ioniq 5",
        "ioniq 6",
        "taycan",
    }


def _fleasing_form_label(form: str) -> str:
    return {
        "financial": "Finansiel leasing",
        "flex": "Flexleasing",
        "operational": "Operationel leasing",
        "hybrid": "Hybrid leasing",
    }[form]


def _terminalen_service_arrangements(
    raw_fact: TerminalenBoundaryFact[list[TerminalenBoundaryServiceArrangement]],
) -> dict[str, object]:
    if raw_fact.state != "known":
        return {"state": raw_fact.state}
    if raw_fact.value is None:
        return {"state": "not_stated"}
    values: list[dict[str, object]] = []
    for raw_value in raw_fact.value:
        values.append(
            {
                "category": "service",
                "treatment": raw_value.treatment,
                "summary": raw_value.scope,
                "limits": {"state": "not_stated"},
            }
        )
    return {"state": "known", "value": values}


def _strict_cash_flow_events(
    raw_stream: Sequence[
        FleasingBoundaryCashFlowEvent | TerminalenBoundaryCashFlowEvent
    ],
    term: int,
) -> list[BaseCashFlowEvent] | None:
    if not raw_stream:
        return None
    events: list[BaseCashFlowEvent] = []
    for event_index, raw_event in enumerate(raw_stream, start=1):
        timing = raw_event.timing
        if timing == "recurring":
            recurrence_count = raw_event.recurrence_count
            if (
                not isinstance(recurrence_count, int)
                or isinstance(recurrence_count, bool)
                or recurrence_count <= 0
                or recurrence_count > term
            ):
                return None
            months = range(1, recurrence_count + 1)
            kind = "lease_payment"
        elif timing == "acceptance_to_handover":
            months = (0,)
            kind = "initial_payment"
        elif timing == "normal_completion_end":
            months = (term,)
            kind = "other"
        else:
            months = (0,)
            kind = "other"
        amount = raw_event.amount_dkk
        if isinstance(amount, (int, float)) and not isinstance(amount, bool):
            amount_fact: dict[str, object] = {"state": "known", "value": amount}
        else:
            amount_fact = {"state": "not_stated"}
        refundability = raw_event.refundability
        if refundability in {"refundable", "not_refundable"}:
            refundability_fact: dict[str, object] = {
                "state": "known",
                "value": refundability,
            }
        else:
            refundability_fact = {"state": "not_stated"}
        direction = raw_event.direction
        if direction not in {"payment", "receipt"}:
            direction = "payment"
        for month in months:
            events.append(
                BaseCashFlowEvent.model_validate(
                    {
                        "key": f"source-event-{event_index}-{month}",
                        "month": month,
                        "kind": kind,
                        "direction": direction,
                        "amount": amount_fact,
                        "refundability": refundability_fact,
                    }
                )
            )
    return events


def _strict_calculated_results(
    events: list[BaseCashFlowEvent], term: int
) -> tuple[dict[str, object], dict[str, object]]:
    reasons: list[dict[str, object]] = []
    total = 0.0
    for event in events:
        if not isinstance(event.amount, KnownFact):
            reasons.append(
                {
                    "code": "fact_unavailable",
                    "field": "baseCashFlowStream.amount",
                    "eventKey": event.key,
                    "factState": event.amount.state,
                }
            )
            continue
        amount = event.amount.value
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("strict cash-flow amounts must be numeric")
        total += float(amount) * (1 if event.direction == "payment" else -1)
    if reasons:
        result = {"state": "unavailable", "reasons": reasons}
        return result, result
    return (
        {"state": "available", "value": {"amountDkk": round(total, 2)}},
        {
            "state": "available",
            "value": {"amountDkk": round(total / term, 2)},
        },
    )


def _normalized_https_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("source payload URLs must be absolute HTTPS URLs")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "FleasingProviderAdapter",
    "TerminalenProviderAdapter",
    "UrlLibHttpClient",
    "production_provider_adapters",
]
