from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ORDINARY_ROUNDING_TOLERANCE_DKK = 1
NORMAL_COMPLETION_BASE_CASH_FLOW_SCOPE = "normal_completion_base_cash_flows"


def calculate_comparison_values(offer: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Derive normal-completion comparison values from one base cash-flow stream."""
    events = offer.get("baseCashFlowStream")
    if not isinstance(events, list):
        unavailable = unavailable_value("baseCashFlowStream")
        return {
            "upfrontCashRequirement": unavailable,
            "nominalBaseOutlay": unavailable,
            "nominalMonthlyEquivalent": calculate_nominal_monthly_equivalent(
                unavailable, offer.get("termMonths")
            ),
        }
    if not is_time_ordered(events):
        unavailable = unavailable_value("baseCashFlowStream")
        return {
            "upfrontCashRequirement": unavailable,
            "nominalBaseOutlay": unavailable,
            "nominalMonthlyEquivalent": calculate_nominal_monthly_equivalent(
                unavailable, offer.get("termMonths")
            ),
        }

    upfront = calculate_upfront_cash_requirement(events)
    nominal_outlay = calculate_nominal_base_outlay(
        events, offer.get("baseCashFlowBlockers")
    )
    if reconcile_provider_advertised_aggregate(offer)["status"] == "mismatch":
        nominal_outlay = unavailable_value("providerAdvertisedAggregateMismatch")
    monthly_equivalent = calculate_nominal_monthly_equivalent(
        nominal_outlay, offer.get("termMonths")
    )
    return {
        "upfrontCashRequirement": upfront,
        "nominalBaseOutlay": nominal_outlay,
        "nominalMonthlyEquivalent": monthly_equivalent,
    }


def reconcile_provider_advertised_aggregate(offer: Mapping[str, Any]) -> dict[str, Any]:
    """Compare a same-scope provider aggregate assertion with reconstructed base cash flows."""
    assertion = provider_aggregate_assertion(offer)
    events = offer.get("baseCashFlowStream")
    reconstructed = (
        calculate_nominal_base_outlay(events, offer.get("baseCashFlowBlockers"))
        if isinstance(events, list) and is_time_ordered(events)
        else unavailable_value("baseCashFlowStream")
    )
    diagnostic = {
        "offerIdentity": offer.get("offerIdentity"),
        "providerAdvertisedAggregate": assertion,
        "reconstructedNominalBaseOutlayDkk": reconstructed.get("valueDkk"),
        "reconstructedEvents": reconstructed_events(events),
        "differenceDkk": None,
        "toleranceDkk": ORDINARY_ROUNDING_TOLERANCE_DKK,
        "recurrenceCounts": recurrence_counts(events),
        "vatBases": vat_bases(events),
        "evidenceReferences": aggregate_evidence_references(assertion, events),
        "investigationPrompts": investigation_prompts(assertion, reconstructed),
    }
    if assertion is None:
        diagnostic["status"] = "not_available"
        return diagnostic
    if reconstructed["state"] != "known":
        diagnostic["status"] = "not_reconstructed"
        return diagnostic
    difference = assertion["valueDkk"] - reconstructed["valueDkk"]
    diagnostic["differenceDkk"] = difference
    if difference == 0:
        diagnostic["status"] = "matching"
    elif abs(difference) <= ORDINARY_ROUNDING_TOLERANCE_DKK:
        diagnostic["status"] = "within_ordinary_rounding_tolerance"
    else:
        diagnostic["status"] = "mismatch"
    return diagnostic


def provider_aggregate_assertion(offer: Mapping[str, Any]) -> dict[str, Any] | None:
    value = offer.get("providerAdvertisedAggregate")
    if not isinstance(value, Mapping):
        return None
    amount = value.get("valueDkk")
    evidence = value.get("evidence")
    if (
        value.get("state") != "known"
        or value.get("scope") != NORMAL_COMPLETION_BASE_CASH_FLOW_SCOPE
        or not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount < 0
        or not has_evidence(evidence)
    ):
        return None
    return {
        "valueDkk": amount,
        "scope": NORMAL_COMPLETION_BASE_CASH_FLOW_SCOPE,
        "evidence": {
            "sourceUrl": evidence["sourceUrl"],
            "wording": evidence["wording"],
        },
    }


def recurrence_counts(events: Any) -> list[int]:
    if not isinstance(events, list):
        return []
    return [
        event.get("recurrenceCount", 1)
        for event in events
        if isinstance(event, Mapping)
        and isinstance(event.get("recurrenceCount", 1), int)
    ]


def reconstructed_events(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        return []
    return [
        {
            "meaning": event.get("meaning"),
            "direction": event.get("direction"),
            "amountDkk": event.get("amountDkk"),
            "recurrenceCount": event.get("recurrenceCount", 1),
            "amountBasis": event.get("amountBasis"),
            "evidence": event.get("evidence"),
        }
        for event in events
        if isinstance(event, Mapping) and event.get("includedInBase") is True
    ]


def vat_bases(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []
    return sorted(
        {
            event["amountBasis"]
            for event in events
            if isinstance(event, Mapping) and isinstance(event.get("amountBasis"), str)
        }
    )


def aggregate_evidence_references(
    assertion: Mapping[str, Any] | None, events: Any
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    if assertion is not None:
        references.append(dict(assertion["evidence"]))
    if isinstance(events, list):
        for event in events:
            if isinstance(event, Mapping) and has_evidence(event.get("evidence")):
                references.append(dict(event["evidence"]))
    return references


def investigation_prompts(
    assertion: Mapping[str, Any] | None, reconstructed: Mapping[str, Any]
) -> list[str]:
    if assertion is None:
        return [
            "Find a provider-advertised aggregate for the same normal-completion base cash-flow scope."
        ]
    if reconstructed["state"] != "known":
        return [
            "Verify every base cash-flow amount, recurrence, VAT basis, and normal-completion timing."
        ]
    return [
        "Verify that the provider aggregate covers the same normal-completion cash flows.",
        "Check recurrence counts, VAT basis, and any end-of-term fees against their source evidence.",
    ]


def calculate_upfront_cash_requirement(events: list[Any]) -> dict[str, Any]:
    blocking_facts = invalid_event_facts(
        events, relevant_timing="acceptance_to_handover"
    )
    if blocking_facts:
        return unavailable_value(*blocking_facts)
    return known_value(
        sum(payment_amount(event) for event in events if is_upfront_payment(event))
    )


def calculate_nominal_base_outlay(
    events: list[Any], completion_blockers: Any
) -> dict[str, Any]:
    blocking_facts = invalid_event_facts(events)
    blocking_facts.extend(blocking_fact_list(completion_blockers, "baseCashFlowStream"))
    if blocking_facts:
        return unavailable_value(*blocking_facts)
    return known_value(
        sum(signed_amount(event) for event in events if is_base_event(event))
    )


def calculate_nominal_monthly_equivalent(
    nominal_outlay: Mapping[str, Any], term_months: Any
) -> dict[str, Any]:
    if nominal_outlay["state"] != "known":
        blocking_facts = list(nominal_outlay["blockingFacts"])
        if not isinstance(term_months, Mapping) or term_months.get("state") != "known":
            blocking_facts.append("termMonths")
        return unavailable_value(*blocking_facts)
    if not isinstance(term_months, Mapping) or term_months.get("state") != "known":
        return unavailable_value("termMonths")
    months = term_months.get("value")
    if not isinstance(months, int) or isinstance(months, bool) or months <= 0:
        return unavailable_value("termMonths")
    return known_value(round_to_nearest_dkk(nominal_outlay["valueDkk"], months))


def round_to_nearest_dkk(amount_dkk: int, months: int) -> int:
    """Round a nominal monthly equivalent half away from zero to a whole DKK."""
    if amount_dkk < 0:
        return -round_to_nearest_dkk(-amount_dkk, months)
    return (amount_dkk * 2 + months) // (months * 2)


def invalid_event_facts(
    events: list[Any], relevant_timing: str | None = None
) -> list[str]:
    blocking_facts: list[str] = []
    for event in events:
        if not isinstance(event, Mapping):
            return ["baseCashFlowStream"]
        if not is_base_event(event):
            blocking_facts.append("baseCashFlowStream")
            continue
        timing = event.get("timing")
        if relevant_timing is not None and timing != relevant_timing:
            if timing in {
                "acceptance_to_handover",
                "recurring",
                "normal_completion_end",
            }:
                continue
        if not valid_event(event):
            blocking_facts.extend(event_blocking_facts(event))
    return sorted(set(blocking_facts))


def valid_event(event: Mapping[str, Any]) -> bool:
    amount = event.get("amountDkk")
    recurrence_count = event.get("recurrenceCount", 1)
    return (
        event.get("includedInBase") is True
        and event.get("direction") in {"payment", "receipt"}
        and event.get("timing")
        in {"acceptance_to_handover", "recurring", "normal_completion_end"}
        and event.get("amountBasis") in {"including_vat", "excluding_vat", "not_stated"}
        and isinstance(amount, int)
        and not isinstance(amount, bool)
        and amount >= 0
        and isinstance(recurrence_count, int)
        and not isinstance(recurrence_count, bool)
        and recurrence_count > 0
        and has_event_evidence(event)
    )


def event_blocking_facts(event: Mapping[str, Any]) -> list[str]:
    blockers = event.get("blockingFacts")
    if (
        isinstance(blockers, list)
        and blockers
        and all(isinstance(blocker, str) and blocker for blocker in blockers)
    ):
        return blockers
    return ["baseCashFlowStream"]


def blocking_fact_list(value: Any, fallback: str) -> list[str]:
    if isinstance(value, list) and all(
        isinstance(item, str) and item for item in value
    ):
        return value
    return [] if value is None else [fallback]


def is_base_event(event: Mapping[str, Any]) -> bool:
    return event.get("includedInBase") is True


def is_time_ordered(events: list[Any]) -> bool:
    timing_order = {
        "acceptance_to_handover": 0,
        "recurring": 1,
        "normal_completion_end": 2,
    }
    previous_phase = -1
    for event in events:
        if not isinstance(event, Mapping) or event.get("includedInBase") is not True:
            return False
        phase = timing_order.get(event.get("timing"))
        if phase is None or phase < previous_phase:
            return False
        previous_phase = phase
    return True


def has_event_evidence(event: Mapping[str, Any]) -> bool:
    return has_evidence(event.get("evidence"))


def has_evidence(evidence: Any) -> bool:
    return (
        isinstance(evidence, Mapping)
        and isinstance(evidence.get("sourceUrl"), str)
        and bool(evidence["sourceUrl"])
        and isinstance(evidence.get("wording"), str)
        and bool(evidence["wording"])
    )


def is_upfront_payment(event: Mapping[str, Any]) -> bool:
    return (
        is_base_event(event)
        and event.get("timing") == "acceptance_to_handover"
        and event.get("direction") == "payment"
    )


def payment_amount(event: Mapping[str, Any]) -> int:
    return event["amountDkk"] * event.get("recurrenceCount", 1)


def signed_amount(event: Mapping[str, Any]) -> int:
    amount = payment_amount(event)
    return amount if event["direction"] == "payment" else -amount


def known_value(amount_dkk: int) -> dict[str, Any]:
    return {"state": "known", "valueDkk": amount_dkk}


def unavailable_value(*blocking_facts: str) -> dict[str, Any]:
    return {"state": "not_stated", "blockingFacts": sorted(set(blocking_facts))}
