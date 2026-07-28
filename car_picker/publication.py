from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from car_picker.comparison import calculate_comparison_values, is_time_ordered


PRESENTATION_SCHEMA_VERSION = "catalogue-presentation/v1"
FACT_STATES = {"known", "not_stated", "unclear", "conflicting", "not_applicable"}

PRESENTATION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://car-picker.local/schemas/catalogue-presentation-v1.json",
    "type": "object",
    "additionalProperties": False,
    "required": ["schemaVersion", "generatedAt", "coverage", "offers"],
    "properties": {
        "schemaVersion": {"const": PRESENTATION_SCHEMA_VERSION},
        "generatedAt": {"type": "string"},
        "coverage": {
            "type": "object",
            "additionalProperties": False,
            "required": ["providers"],
            "properties": {
                "providers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "designatedSource", "quarantinedCandidateCount"],
                        "properties": {
                            "name": {"type": "string"},
                            "designatedSource": {"type": "string"},
                            "quarantinedCandidateCount": {"type": "integer", "minimum": 0},
                        },
                    },
                }
            },
        },
        "offers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "offerIdentity",
                    "provider",
                    "providerSourceUrl",
                    "vehicleSpecification",
                    "supportedLeasingForm",
                    "providerFormLabel",
                    "residualRiskAllocation",
                    "registrationTaxTreatment",
                    "serviceArrangements",
                    "exclusions",
                    "exposureScenarios",
                    "advertisedMonthlyPayment",
                    "upfrontCashRequirement",
                    "nominalBaseOutlay",
                    "nominalMonthlyEquivalent",
                    "termMonths",
                    "annualMileageKm",
                    "normalEndMechanism",
                ],
                "properties": {
                    "offerIdentity": {"type": "string"},
                    "provider": {"type": "string"},
                    "providerSourceUrl": {"type": "string"},
                    "vehicleSpecification": {"$ref": "#/$defs/valueFact"},
                    "supportedLeasingForm": {"$ref": "#/$defs/valueFact"},
                    "providerFormLabel": {"$ref": "#/$defs/valueFact"},
                    "residualRiskAllocation": {"$ref": "#/$defs/valueFact"},
                    "registrationTaxTreatment": {"$ref": "#/$defs/valueFact"},
                    "serviceArrangements": {"$ref": "#/$defs/serviceListFact"},
                    "exclusions": {"$ref": "#/$defs/serviceListFact"},
                    "exposureScenarios": {"$ref": "#/$defs/exposureListFact"},
                    "advertisedMonthlyPayment": {"$ref": "#/$defs/moneyFact"},
                    "upfrontCashRequirement": {"$ref": "#/$defs/moneyFact"},
                    "nominalBaseOutlay": {"$ref": "#/$defs/moneyFact"},
                    "nominalMonthlyEquivalent": {"$ref": "#/$defs/moneyFact"},
                    "termMonths": {"$ref": "#/$defs/valueFact"},
                    "annualMileageKm": {"$ref": "#/$defs/valueFact"},
                    "normalEndMechanism": {"$ref": "#/$defs/valueFact"},
                    "cashFlowBreakdown": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/cashFlowEvent"},
                    },
                },
            },
        },
    },
    "$defs": {
        "evidence": {
            "type": "object",
            "additionalProperties": False,
            "required": ["sourceUrl", "wording"],
            "properties": {
                "sourceUrl": {"type": "string"},
                "wording": {"type": "string"},
            },
        },
        "moneyFact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["state", "evidence"],
            "properties": {
                "state": {"enum": sorted(FACT_STATES)},
                "valueDkk": {"type": "integer"},
                "evidence": {"$ref": "#/$defs/evidence"},
                "blockingFacts": {"type": "array", "items": {"type": "string"}},
            },
        },
        "valueFact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["state", "evidence"],
            "properties": {
                "state": {"enum": sorted(FACT_STATES)},
                "value": {"type": ["string", "integer"]},
                "evidence": {"$ref": "#/$defs/evidence"},
            },
        },
        "serviceListFact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["state", "evidence"],
            "properties": {
                "state": {"enum": sorted(FACT_STATES)},
                "value": {"type": "array", "items": {"$ref": "#/$defs/serviceArrangement"}},
                "evidence": {"$ref": "#/$defs/evidence"},
            },
        },
        "serviceArrangement": {
            "type": "object", "additionalProperties": False,
            "required": ["category", "treatment", "scope"],
            "properties": {
                "category": {"type": "string"},
                "treatment": {"enum": ["included", "optional", "required_external", "excluded"]},
                "scope": {"type": "string"},
            },
        },
        "exposureListFact": {
            "type": "object", "additionalProperties": False,
            "required": ["state", "evidence"],
            "properties": {
                "state": {"enum": sorted(FACT_STATES)},
                "value": {"type": "array", "items": {"$ref": "#/$defs/exposureScenario"}},
                "evidence": {"$ref": "#/$defs/evidence"},
            },
        },
        "exposureScenario": {
            "type": "object", "additionalProperties": False,
            "required": ["kind", "trigger", "requiredInputs"],
            "properties": {
                "kind": {"type": "string"}, "trigger": {"type": "string"},
                "requiredInputs": {"type": "array", "items": {"type": "string"}},
                "formula": {"type": "string"}, "amountDkk": {"type": "integer", "minimum": 0},
                "rateDkk": {"type": "integer", "minimum": 0}, "capDkk": {"type": "integer", "minimum": 0},
            },
        },
        "cashFlowEvent": {
            "type": "object",
            "additionalProperties": False,
            "required": ["meaning", "direction", "amountDkk", "amountBasis", "timing", "recurrenceCount", "refundability", "evidence"],
            "properties": {
                "meaning": {"type": "string"},
                "direction": {"type": "string"},
                "amountDkk": {"type": ["integer", "null"]},
                "amountBasis": {"type": "string"},
                "timing": {"type": "string"},
                "recurrenceCount": {"type": ["integer", "null"], "minimum": 1},
                "refundability": {"type": "string"},
                "blockingFacts": {"type": "array", "items": {"type": "string"}},
                "evidence": {"$ref": "#/$defs/evidence"},
            },
        },
    },
}


def build_site(dataset_path: Path, output_path: Path) -> None:
    """Project a canonical catalogue dataset and atomically replace a static site."""
    dataset = read_json(dataset_path)
    projection = project_catalogue(dataset)
    validate_presentation_projection(projection)
    write_site_atomically(output_path, projection)


def read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read canonical catalogue dataset at {path}: {error}") from error
    return object_value(value, "canonical catalogue dataset")


def project_catalogue(dataset: Mapping[str, Any]) -> dict[str, Any]:
    require_equal(dataset, "schemaVersion", "catalogue-dataset/v1")
    generated_at = string_value(dataset, "generatedAt")
    coverage = object_value(dataset.get("coverage"), "coverage")
    provider_rows = list_value(coverage.get("providers"), "coverage.providers")
    providers = [project_provider(object_value(row, "coverage provider")) for row in provider_rows]
    offer_rows = list_value(dataset.get("catalogueOffers"), "catalogueOffers")
    admitted_offers = [
        object_value(row, "catalogue offer")
        for row in offer_rows
        if admission_status(object_value(row, "catalogue offer")) == "admitted"
    ]
    return {
        "schemaVersion": PRESENTATION_SCHEMA_VERSION,
        "generatedAt": generated_at,
        "coverage": {"providers": providers},
        "offers": [project_offer(offer) for offer in admitted_offers],
    }


def project_provider(provider: Mapping[str, Any]) -> dict[str, Any]:
    count = provider.get("quarantinedCandidateCount")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("coverage provider.quarantinedCandidateCount must be a non-negative integer")
    return {
        "name": string_value(provider, "name"),
        "designatedSource": string_value(provider, "designatedSource"),
        "quarantinedCandidateCount": count,
    }


def project_offer(offer: Mapping[str, Any]) -> dict[str, Any]:
    require_equal(offer, "admissionStatus", "admitted")
    comparison_values = calculate_comparison_values(offer)
    projected_offer = {
        "offerIdentity": string_value(offer, "offerIdentity"),
        "provider": string_value(offer, "provider"),
        "providerSourceUrl": derived_value_source_url(offer),
        "vehicleSpecification": project_vehicle_specification(offer.get("vehicleSpecification")),
        "supportedLeasingForm": project_value_fact(offer.get("supportedLeasingForm")),
        "providerFormLabel": project_provider_form_label(offer.get("supportedLeasingForm")),
        "residualRiskAllocation": project_value_fact(offer.get("residualRiskAllocation")),
        "registrationTaxTreatment": project_registration_tax_fact(offer.get("registrationTaxTreatment")),
        "serviceArrangements": project_list_fact(offer.get("serviceArrangements"), valid_service_arrangement),
        "exclusions": project_list_fact(offer.get("exclusions"), valid_service_arrangement),
        "exposureScenarios": project_list_fact(offer.get("exposureScenarios"), valid_exposure_scenario),
        "advertisedMonthlyPayment": project_money_fact(offer.get("advertisedMonthlyPayment")),
        "upfrontCashRequirement": project_derived_money_fact(comparison_values["upfrontCashRequirement"], offer),
        "nominalBaseOutlay": project_derived_money_fact(comparison_values["nominalBaseOutlay"], offer),
        "nominalMonthlyEquivalent": project_derived_money_fact(comparison_values["nominalMonthlyEquivalent"], offer),
        "termMonths": project_value_fact(offer.get("termMonths")),
        "annualMileageKm": project_value_fact(offer.get("annualMileageKm")),
        "normalEndMechanism": project_value_fact(offer.get("normalEndMechanism")),
    }
    if isinstance(offer.get("baseCashFlowStream"), list):
        breakdown = project_cash_flow_breakdown(offer["baseCashFlowStream"])
        if breakdown:
            projected_offer["cashFlowBreakdown"] = breakdown
    return projected_offer


def project_derived_money_fact(value: Mapping[str, Any], offer: Mapping[str, Any]) -> dict[str, Any]:
    evidence = {
        "sourceUrl": derived_value_source_url(offer),
        "wording": "Beregnet af tjenesten fra betalingsstrømmen.",
    }
    if value["state"] == "known":
        return {"state": "known", "valueDkk": value["valueDkk"], "evidence": evidence}
    return {"state": "not_stated", "evidence": evidence, "blockingFacts": value["blockingFacts"]}


def derived_value_source_url(offer: Mapping[str, Any]) -> str:
    canonical_url = offer.get("canonicalOfferUrl")
    if isinstance(canonical_url, str) and canonical_url:
        return canonical_url
    events = offer.get("baseCashFlowStream")
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, Mapping):
                continue
            evidence = event.get("evidence")
            source_url = evidence.get("sourceUrl") if isinstance(evidence, Mapping) else None
            if isinstance(source_url, str) and source_url:
                return source_url
    for field_name in ("upfrontCashRequirement", "nominalBaseOutlay", "nominalMonthlyEquivalent"):
        fact = offer.get(field_name)
        if isinstance(fact, Mapping):
            evidence = fact.get("evidence")
            if isinstance(evidence, Mapping):
                source_url = evidence.get("sourceUrl")
                if isinstance(source_url, str) and source_url:
                    return source_url
    raise ValueError("base cash-flow stream requires at least one source URL")


def project_cash_flow_breakdown(events: list[Any]) -> list[dict[str, Any]]:
    if not all(isinstance(event, Mapping) for event in events):
        return []
    event_rows = [event for event in events if isinstance(event, Mapping)]
    if not is_time_ordered(event_rows) or not all(cash_flow_event_has_presentation_shape(event) for event in event_rows):
        return []
    return [
        project_cash_flow_event(event)
        for event in event_rows
    ]


def cash_flow_event_has_presentation_shape(event: Mapping[str, Any]) -> bool:
    required_strings = ("meaning", "direction", "amountBasis", "timing", "refundability")
    evidence = event.get("evidence")
    return (
        all(isinstance(event.get(field), str) and event[field] for field in required_strings)
        and isinstance(evidence, Mapping)
        and isinstance(evidence.get("sourceUrl"), str)
        and bool(evidence["sourceUrl"])
        and isinstance(evidence.get("wording"), str)
        and bool(evidence["wording"])
        and valid_or_missing_cash_flow_number(event.get("amountDkk"))
        and valid_or_missing_recurrence_count(event.get("recurrenceCount", 1))
        and (
            (
                event.get("amountDkk") is not None
                and event.get("recurrenceCount", 1) is not None
            )
            or has_precise_blocking_facts(event.get("blockingFacts"))
        )
    )


def has_precise_blocking_facts(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)


def project_cash_flow_event(event: Mapping[str, Any]) -> dict[str, Any]:
    amount, recurrence_count, blocking_facts = checked_cash_flow_event_values(event, "base cash-flow event")
    evidence_value = object_value(event.get("evidence"), "base cash-flow evidence")
    projected_event = {
        "meaning": string_value(event, "meaning"),
        "direction": string_value(event, "direction"),
        "amountDkk": amount,
        "amountBasis": amount_basis(event),
        "timing": string_value(event, "timing"),
        "recurrenceCount": recurrence_count,
        "refundability": string_value(event, "refundability"),
        "evidence": {
            "sourceUrl": string_value(evidence_value, "sourceUrl"),
            "wording": string_value(evidence_value, "wording"),
        },
    }
    if blocking_facts:
        projected_event["blockingFacts"] = blocking_facts
    return projected_event


def valid_or_missing_cash_flow_number(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0)


def valid_or_missing_recurrence_count(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 1)


def checked_cash_flow_event_values(event: Mapping[str, Any], context: str) -> tuple[Any, Any, list[str]]:
    recurrence_count = event.get("recurrenceCount", 1)
    amount = event.get("amountDkk")
    blocking_facts = string_list_value(event.get("blockingFacts", []), f"{context} blockingFacts")
    if not valid_or_missing_recurrence_count(recurrence_count):
        raise ValueError(f"{context} recurrenceCount must be a positive integer or null")
    if not valid_or_missing_cash_flow_number(amount):
        raise ValueError(f"{context} amountDkk must be a non-negative integer or null")
    if (amount is None or recurrence_count is None) and not blocking_facts:
        raise ValueError(f"missing {context} values require precise blocking facts")
    return amount, recurrence_count, blocking_facts


def amount_basis(event: Mapping[str, Any]) -> str:
    basis = string_value(event, "amountBasis")
    if basis not in {"including_vat", "excluding_vat", "not_stated"}:
        raise ValueError("base cash-flow event amountBasis must be a supported amount basis")
    return basis


def admission_status(offer: Mapping[str, Any]) -> str:
    status = string_value(offer, "admissionStatus")
    if status not in {"admitted", "quarantined"}:
        raise ValueError(f"Unknown admission status: {status}")
    return status


def project_vehicle_specification(value: Any) -> dict[str, Any]:
    fact = project_fact(value)
    if fact["state"] == "known":
        specification = object_value(object_value(value, "vehicle specification").get("value"), "vehicle value")
        fact["value"] = " ".join(
            string_value(specification, field_name) for field_name in ("make", "model", "trim")
        )
    return fact


def project_money_fact(value: Any) -> dict[str, Any]:
    return project_known_value_fact(
        value,
        "valueDkk",
        lambda amount: isinstance(amount, int) and not isinstance(amount, bool),
        "Known money facts require an integer valueDkk",
    )


def project_value_fact(value: Any) -> dict[str, Any]:
    return project_known_value_fact(
        value,
        "value",
        lambda known_value: isinstance(known_value, (str, int)) and not isinstance(known_value, bool),
        "Known value facts require a string or integer value",
    )


def project_provider_form_label(value: Any) -> dict[str, Any]:
    fact = project_fact(value)
    if fact["state"] == "known":
        fact["value"] = fact["evidence"]["wording"]
    return fact


def project_registration_tax_fact(value: Any) -> dict[str, Any]:
    return project_known_value_fact(
        value, "value", lambda known_value: known_value in {"full", "proportional"},
        "Known registration-tax treatment must be full or proportional",
    )


def project_list_fact(value: Any, valid_item: Callable[[Mapping[str, Any]], bool]) -> dict[str, Any]:
    fact = project_fact(value)
    if fact["state"] == "known":
        items = list_value(object_value(value, "offer fact").get("value"), "offer fact value")
        if not all(isinstance(item, Mapping) and valid_item(item) for item in items):
            raise ValueError("Known detail facts require supported structured values")
        fact["value"] = [dict(item) for item in items]
    return fact


def valid_service_arrangement(value: Mapping[str, Any]) -> bool:
    return (
        all(isinstance(value.get(field), str) and value[field] for field in ("category", "treatment", "scope"))
        and value["treatment"] in {"included", "optional", "required_external", "excluded"}
    )


def valid_exposure_scenario(value: Mapping[str, Any]) -> bool:
    inputs = value.get("requiredInputs")
    return (
        all(isinstance(value.get(field), str) and value[field] for field in ("kind", "trigger"))
        and isinstance(inputs, list)
        and all(isinstance(item, str) and item for item in inputs)
        and all(
            key not in value or (isinstance(value[key], int) and not isinstance(value[key], bool) and value[key] >= 0)
            for key in ("amountDkk", "rateDkk", "capDkk")
        )
        and ("formula" not in value or (isinstance(value["formula"], str) and value["formula"]))
    )


def project_known_value_fact(
    value: Any,
    value_key: str,
    is_valid: Callable[[Any], bool],
    error_message: str,
) -> dict[str, Any]:
    fact = project_fact(value)
    if fact["state"] == "known":
        known_value = object_value(value, "offer fact").get(value_key)
        if not is_valid(known_value):
            raise ValueError(error_message)
        fact[value_key] = known_value
    return fact


def project_fact(value: Any) -> dict[str, Any]:
    fact = object_value(value, "offer fact")
    state = string_value(fact, "state")
    if state not in FACT_STATES:
        raise ValueError(f"Unknown offer fact state: {state}")
    evidence = object_value(fact.get("evidence"), "source evidence")
    return {
        "state": state,
        "evidence": {
            "sourceUrl": string_value(evidence, "sourceUrl"),
            "wording": string_value(evidence, "wording"),
        },
    }


def validate_presentation_projection(projection: Mapping[str, Any]) -> None:
    """Validate the browser contract before it is published."""
    require_equal(projection, "schemaVersion", PRESENTATION_SCHEMA_VERSION)
    string_value(projection, "generatedAt")
    coverage = object_value(projection.get("coverage"), "coverage")
    for provider in list_value(coverage.get("providers"), "coverage.providers"):
        project_provider(object_value(provider, "coverage provider"))
    offers = list_value(projection.get("offers"), "offers")
    for offer in offers:
        projection_offer = object_value(offer, "presentation offer")
        for field_name in ("offerIdentity", "provider", "providerSourceUrl"):
            string_value(projection_offer, field_name)
        for field_name in ("vehicleSpecification", "supportedLeasingForm", "providerFormLabel", "residualRiskAllocation"):
            validate_projected_fact(projection_offer.get(field_name), "value")
        validate_projected_fact(projection_offer.get("registrationTaxTreatment"), "value")
        for field_name in ("serviceArrangements", "exclusions", "exposureScenarios"):
            validate_projected_list_fact(projection_offer.get(field_name))
        for field_name in (
            "advertisedMonthlyPayment",
            "upfrontCashRequirement",
            "nominalBaseOutlay",
            "nominalMonthlyEquivalent",
        ):
            validate_projected_fact(projection_offer.get(field_name), "valueDkk")
        for field_name in ("termMonths", "annualMileageKm", "normalEndMechanism"):
            validate_projected_fact(projection_offer.get(field_name), "value")
        if "cashFlowBreakdown" in projection_offer:
            for event in list_value(projection_offer["cashFlowBreakdown"], "cashFlowBreakdown"):
                validate_projected_cash_flow_event(object_value(event, "cash-flow event"))


def validate_projected_fact(value: Any, value_key: str) -> None:
    fact = object_value(value, "presentation offer fact")
    state = string_value(fact, "state")
    if state not in FACT_STATES:
        raise ValueError(f"Unknown offer fact state: {state}")
    evidence = object_value(fact.get("evidence"), "source evidence")
    string_value(evidence, "sourceUrl")
    string_value(evidence, "wording")
    if state == "known" and value_key not in fact:
        raise ValueError(f"Known presentation offer fact requires {value_key}")


def validate_projected_list_fact(value: Any) -> None:
    fact = object_value(value, "presentation list fact")
    state = string_value(fact, "state")
    if state not in FACT_STATES:
        raise ValueError(f"Unknown presentation fact state: {state}")
    evidence = object_value(fact.get("evidence"), "source evidence")
    string_value(evidence, "sourceUrl")
    string_value(evidence, "wording")
    if state == "known":
        list_value(fact.get("value"), "known presentation list fact value")


def validate_projected_cash_flow_event(event: Mapping[str, Any]) -> None:
    for field_name in ("meaning", "direction", "timing", "refundability"):
        string_value(event, field_name)
    amount_basis(event)
    checked_cash_flow_event_values(event, "cash-flow event")
    evidence = object_value(event.get("evidence"), "cash-flow event evidence")
    string_value(evidence, "sourceUrl")
    string_value(evidence, "wording")


def write_site_atomically(output_path: Path, projection: Mapping[str, Any]) -> None:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".car-picker-site-", dir=output_path.parent) as staging_root:
        staging_path = Path(staging_root) / "site"
        staging_path.mkdir()
        (staging_path / "projection.json").write_text(
            json.dumps(projection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        (staging_path / "index.html").write_text(index_html(), encoding="utf-8")
        (staging_path / "app.js").write_text(browser_app(), encoding="utf-8")
        (staging_path / "styles.css").write_text(stylesheet(), encoding="utf-8")
        replace_directory(staging_path, output_path)


def replace_directory(staging_path: Path, output_path: Path) -> None:
    backup_path = output_path.with_name(f".{output_path.name}.previous")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    if output_path.exists():
        os.replace(output_path, backup_path)
    try:
        os.replace(staging_path, output_path)
    except BaseException:
        if backup_path.exists():
            os.replace(backup_path, output_path)
        raise
    if backup_path.exists():
        shutil.rmtree(backup_path)


def object_value(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def list_value(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return value


def string_list_value(value: Any, name: str) -> list[str]:
    items = list_value(value, name)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{name} must contain non-empty strings")
    return items


def string_value(value: Mapping[str, Any], name: str) -> str:
    field_value = value.get(name)
    if not isinstance(field_value, str) or not field_value:
        raise ValueError(f"{name} must be a non-empty string")
    return field_value


def require_equal(value: Mapping[str, Any], name: str, expected: str) -> None:
    if value.get(name) != expected:
        raise ValueError(f"{name} must equal {expected}")


def index_html() -> str:
    return """<!doctype html>
<html lang=\"da\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Bilvalg</title>
    <link rel=\"stylesheet\" href=\"styles.css\">
  </head>
  <body>
    <main id=\"app\" aria-live=\"polite\"></main>
    <script type=\"module\" src=\"app.js\"></script>
  </body>
</html>
"""


def browser_app() -> str:
    schema = json.dumps(PRESENTATION_SCHEMA, ensure_ascii=False, separators=(",", ":"))
    return f"""const presentationSchema = {schema};

const factLabels = {{
  known: "Oplyst",
  not_stated: "Ikke oplyst",
  unclear: "Uklart",
  conflicting: "Modstridende",
  not_applicable: "Ikke relevant",
}};

const root = document.querySelector("#app");

start();

async function start() {{
  try {{
    const response = await fetch("projection.json", {{ cache: "no-store" }});
    if (!response.ok) throw new Error("Katalogdata kunne ikke hentes.");
    const projection = await response.json();
    validateProjection(projection, presentationSchema, "$", presentationSchema);
    validateKnownFactValues(projection);
    window.addEventListener("hashchange", () => renderApplication(projection));
    renderApplication(projection);
  }} catch (error) {{
    root.replaceChildren(message("Kataloget kan ikke vises", "Katalogdata bestod ikke den nødvendige kontrol."));
    console.error(error);
  }}
}}

function validateProjection(value, schema, location, rootSchema) {{
  if (schema.$ref) {{
    const target = schema.$ref.replace("#/$defs/", "");
    validateProjection(value, rootSchema.$defs[target], location, rootSchema);
    return;
  }}
  if (schema.const !== undefined && value !== schema.const) throw new Error(`${{location}} has an invalid constant`);
  if (schema.enum && !schema.enum.includes(value)) throw new Error(`${{location}} has an invalid value`);
  if (schema.type && !matchesType(value, schema.type)) throw new Error(`${{location}} has an invalid type`);
  if (schema.type === "object") {{
    for (const required of schema.required || []) {{
      if (!Object.hasOwn(value, required)) throw new Error(`${{location}} is missing ${{required}}`);
    }}
    if (schema.additionalProperties === false) {{
      for (const key of Object.keys(value)) {{
        if (!Object.hasOwn(schema.properties || {{}}, key)) throw new Error(`${{location}} has unexpected ${{key}}`);
      }}
    }}
    for (const [key, childSchema] of Object.entries(schema.properties || {{}})) {{
      if (Object.hasOwn(value, key)) validateProjection(value[key], childSchema, `${{location}}.${{key}}`, rootSchema);
    }}
  }}
  if (schema.type === "array") {{
    value.forEach((item, index) => validateProjection(item, schema.items, `${{location}}[${{index}}]`, rootSchema));
  }}
  if (schema.minimum !== undefined && value < schema.minimum) throw new Error(`${{location}} is below minimum`);
}}

function matchesType(value, expected) {{
  const types = Array.isArray(expected) ? expected : [expected];
  return types.some((type) => (
    (type === "object" && value !== null && typeof value === "object" && !Array.isArray(value)) ||
    (type === "array" && Array.isArray(value)) ||
    (type === "string" && typeof value === "string") ||
    (type === "null" && value === null) ||
    (type === "integer" && Number.isInteger(value))
  ));
}}

function validateKnownFactValues(projection) {{
  for (const offer of projection.offers) {{
    for (const key of ["advertisedMonthlyPayment", "upfrontCashRequirement", "nominalBaseOutlay", "nominalMonthlyEquivalent"]) {{
      if (offer[key].state === "known" && !Number.isInteger(offer[key].valueDkk)) throw new Error(`${{key}} needs a DKK value`);
    }}
    for (const key of ["termMonths", "annualMileageKm", "normalEndMechanism"]) {{
      if (offer[key].state === "known" && !Object.hasOwn(offer[key], "value")) throw new Error(`${{key}} needs a value`);
    }}
    for (const key of ["vehicleSpecification", "supportedLeasingForm"]) {{
      if (offer[key].state === "known" && !Object.hasOwn(offer[key], "value")) throw new Error(`${{key}} needs a value`);
    }}
  }}
}}

function renderApplication(projection) {{
  const route = location.hash.slice(1);
  if (route.startsWith("compare=")) return renderComparison(projection, route.slice(8).split(",").filter(Boolean));
  if (route.startsWith("offer=")) return renderDetailRoute(projection, route.slice(6));
  renderCatalogue(projection);
}}

function renderCatalogue(projection) {{
  const catalogue = document.createElement("section");
  catalogue.className = "catalogue";
  const header = document.createElement("header");
  header.className = "site-header";
  header.append(heading("Bilvalg", 1), text("p", `Katalog genereret ${{formatDate(projection.generatedAt)}}`));
  catalogue.append(header, heading("Filtre og tilbud", 2), filterNote());
  const offers = document.createElement("div");
  offers.className = "offer-list";
  const selected = new Set();
  const comparison = comparisonControl(selected);
  const refreshComparison = () => {{}};
  const filters = filterControls(projection.offers, (filters) => renderOffers(offers, projection.offers, filters, selected, refreshComparison));
  catalogue.append(filters, comparison, offers, coverage(projection.coverage), footer());
  renderOffers(offers, projection.offers, initialFilters(), selected, refreshComparison);
  root.replaceChildren(catalogue);
}}

function filterNote() {{
  const note = document.createElement("p");
  note.className = "filter-note";
  note.textContent = "Tilbud vises i neutral kildeorden. Filtre og fakta er ikke en personlig rangering.";
  return note;
}}

function initialFilters() {{
  return {{ search: "", form: "all", residualRisk: "all", vehicle: "all", upfrontMaximum: "", termMaximum: "", mileageMaximum: "" }};
}}

function filterControls(offers, onChange) {{
  const controls = document.createElement("div");
  controls.className = "filters";
  const filters = initialFilters();
  const update = () => onChange(filters);
  const selectFilters = [
    {{ label: "Leasingform", id: "leasing-form", allLabel: "Alle former", field: "supportedLeasingForm", key: "form", formatter: formLabel }},
    {{ label: "Restværdirisiko", id: "residual-risk", allLabel: "Alle fordelinger", field: "residualRiskAllocation", key: "residualRisk", formatter: residualRiskLabel }},
    {{ label: "Køretøj", id: "vehicle", allLabel: "Alle køretøjer", field: "vehicleSpecification", key: "vehicle", formatter: String }},
  ];
  controls.append(
    textFilter(filters, update),
    ...selectFilters.map((specification) => selectFilter(specification, offers, filters, update)),
    maximumFilter("Højeste kontante behov ved start", "upfront-maximum", filters, "upfrontMaximum", update),
    maximumFilter("Højeste fulde løbetid", "term-maximum", filters, "termMaximum", update, "måneder"),
    maximumFilter("Højeste kilometer om året", "mileage-maximum", filters, "mileageMaximum", update, "km"),
  );
  return controls;
}}

function textFilter(filters, update) {{
  const label = controlLabel("Søg efter bil eller udbyder", "catalogue-search");
  const input = document.createElement("input");
  input.id = "catalogue-search";
  input.name = "search";
  input.type = "search";
  input.placeholder = "Fx Hyundai eller Terminalen";
  input.addEventListener("input", () => {{ filters.search = input.value; update(); }});
  label.append(input);
  return label;
}}

function selectFilter(specification, offers, filters, update) {{
  const label = controlLabel(specification.label, specification.id);
  const select = document.createElement("select");
  select.id = specification.id;
  select.name = specification.id;
  select.append(option("all", specification.allLabel), ...knownValues(offers, specification.field).map((value) => option(value, specification.formatter(value))));
  select.addEventListener("change", () => {{ filters[specification.key] = select.value; update(); }});
  label.append(select);
  return label;
}}

function maximumFilter(labelText, name, filters, key, update, suffix = "kr.") {{
  const label = controlLabel(labelText, name);
  const input = document.createElement("input");
  input.id = name;
  input.name = name;
  input.type = "number";
  input.min = "0";
  input.step = "1";
  input.inputMode = "numeric";
  input.placeholder = suffix;
  input.addEventListener("input", () => {{ filters[key] = input.value; update(); }});
  label.append(input);
  return label;
}}

function controlLabel(labelText, controlId) {{
  const label = document.createElement("label");
  label.htmlFor = controlId;
  label.textContent = labelText;
  return label;
}}

function knownValues(offers, field) {{
  return [...new Set(offers
    .filter((offer) => offer[field].state === "known")
    .map((offer) => offer[field].value))];
}}

function option(value, label) {{
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}}

function formLabel(value) {{
  return value === "operational" ? "Operationel" : value === "financial" ? "Finansiel" : value;
}}

function residualRiskLabel(value) {{
  return value === "provider" ? "Udbyderen bærer risikoen" : value === "lessee" ? "Den kommende leasingtager bærer risikoen" : value;
}}

function registrationTaxLabel(value) {{
  return value === "full" ? "Betalt fuldt" : value === "proportional" ? "Betales forholdsmæssigt" : value;
}}

function renderOffers(container, offers, filters, selected = new Set(), onSelectionChange = () => {{}}) {{
  const visibleOffers = offers.filter((offer) => matchesFilters(offer, filters));
  container.replaceChildren(...visibleOffers.map((offer) => offerCard(offer, selected, onSelectionChange)));
  if (visibleOffers.length === 0) container.append(emptyState());
}}

function matchesFilters(offer, filters) {{
  const query = filters.search.trim().toLocaleLowerCase("da-DK");
  return (
    (!query || searchableOfferText(offer).toLocaleLowerCase("da-DK").includes(query)) &&
    matchesKnownValue(offer.supportedLeasingForm, filters.form) &&
    matchesKnownValue(offer.residualRiskAllocation, filters.residualRisk) &&
    matchesKnownValue(offer.vehicleSpecification, filters.vehicle) &&
    matchesMaximum(offer.upfrontCashRequirement, filters.upfrontMaximum) &&
    matchesMaximum(offer.termMonths, filters.termMaximum) &&
    matchesMaximum(offer.annualMileageKm, filters.mileageMaximum)
  );
}}

function searchableOfferText(offer) {{
  return `${{offer.provider}} ${{offer.vehicleSpecification.state === "known" ? offer.vehicleSpecification.value : ""}}`;
}}

function matchesKnownValue(fact, selectedValue) {{
  return selectedValue === "all" || (fact.state === "known" && fact.value === selectedValue);
}}

function matchesMaximum(fact, maximum) {{
  return maximum === "" || (fact.state === "known" && fact.valueDkk !== undefined && fact.valueDkk <= Number(maximum)) || (fact.state === "known" && fact.value !== undefined && fact.value <= Number(maximum));
}}

function emptyState() {{
  const section = document.createElement("section");
  section.className = "empty-state";
  section.append(heading("Ingen tilbud matcher dine filtre", 3), text("p", "Prøv at ændre eller fjerne et filter. Kataloget dækker ikke nødvendigvis hele det danske marked."));
  return section;
}}

function comparisonControl(selected) {{
  const section = document.createElement("section"); section.className = "comparison-control";
  const link = document.createElement("a");
  link.href = "#compare=";
  link.textContent = "Sammenlign valgte tilbud";
  link.addEventListener("click", (event) => {{
    if (selected.size < 2) {{ event.preventDefault(); section.append(text("p", "Vælg mindst to tilbud for at sammenligne dem.")); return; }}
    event.preventDefault(); location.hash = `compare=${{[...selected].map(encodeURIComponent).join(",")}}`;
  }});
  section.append(link);
  return section;
}}

function renderDetailRoute(projection, identity) {{
  const offer = projection.offers.find((row) => row.offerIdentity === decodeURIComponent(identity));
  if (!offer) return root.replaceChildren(message("Tilbuddet kan ikke vises", "Tilbuddet findes ikke i dette katalog."));
  const page = document.createElement("section"); page.className = "catalogue";
  const back = document.createElement("a"); back.href = "#"; back.textContent = "Tilbage til kataloget";
  page.append(back, offerCard(offer)); root.replaceChildren(page);
}}

function renderComparison(projection, identities) {{
  const offers = identities.map(decodeURIComponent).map((identity) => projection.offers.find((offer) => offer.offerIdentity === identity)).filter(Boolean);
  if (offers.length < 2) return root.replaceChildren(message("Sammenligning kan ikke vises", "Vælg mindst to tilbud fra kataloget."));
  const page = document.createElement("section"); page.className = "catalogue";
  const back = document.createElement("a"); back.href = "#"; back.textContent = "Tilbage til kataloget";
  page.append(back, heading("Sammenlign tilbud", 1), comparisonTable(offers)); root.replaceChildren(page);
}}

function comparisonTable(offers) {{
  const fields = [
    ["Køretøj", "vehicleSpecification", vehicleLabel], ["Kontant behov ved start", "upfrontCashRequirement", money],
    ["Nominelt basisudlæg", "nominalBaseOutlay", money], ["Nominelt månedligt gennemsnit", "nominalMonthlyEquivalent", money],
    ["Annonceret månedlig ydelse", "advertisedMonthlyPayment", money], ["Fuld løbetid", "termMonths", (v) => `${{v}} måneder`],
    ["Kilometer om året", "annualMileageKm", (v) => `${{formatNumber(v)}} km`], ["Normal afslutning", "normalEndMechanism", endMechanismLabel],
    ["Restværdirisiko", "residualRiskAllocation", residualRiskLabel], ["Registreringsafgift", "registrationTaxTreatment", registrationTaxLabel],
    ["Udbyderens formbetegnelse", "providerFormLabel", String], ["Serviceordninger", "serviceArrangements", serviceListValue],
    ["Udelukket eller eksternt", "exclusions", serviceListValue], ["Betingede eksponeringer", "exposureScenarios", exposureListValue],
  ];
  const wrap = document.createElement("div"); wrap.className = "comparison-scroll";
  const table = document.createElement("table"); table.className = "comparison-table";
  const header = document.createElement("tr"); header.append(document.createElement("th")); offers.forEach((offer) => header.append(text("th", `${{offer.provider}} · ${{vehicleLabel(offer.vehicleSpecification)}} · ${{offer.offerIdentity}}`))); table.append(header);
  fields.forEach(([label, key, formatter]) => {{ const row = document.createElement("tr"); row.append(text("th", label)); offers.forEach((offer) => row.append(comparisonValue(offer[key], formatter))); table.append(row); }});
  wrap.append(table); return wrap;
}}

function serviceListValue(value) {{ return value.map(serviceArrangementText).join(" · "); }}
function exposureListValue(value) {{ return value.map(exposureText).join(" · "); }}
function comparisonValue(fact, formatter) {{ const cell = document.createElement("td"); cell.append(text("p", fact.state === "known" ? formatter(fact.valueDkk ?? fact.value) : unavailableFactText(fact)), evidenceDetails("sammenligningsfelt", fact)); return cell; }}

function offerCard(offer, selected = new Set(), onSelectionChange = () => {{}}) {{
  const card = document.createElement("article");
  card.className = "offer-card";
  const selection = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox"; checkbox.checked = selected.has(offer.offerIdentity);
  checkbox.addEventListener("change", () => {{ checkbox.checked ? selected.add(offer.offerIdentity) : selected.delete(offer.offerIdentity); onSelectionChange(); }});
  selection.append(checkbox, " Vælg til sammenligning");
  const detailLink = document.createElement("a"); detailLink.href = `#offer=${{encodeURIComponent(offer.offerIdentity)}}`; detailLink.textContent = "Åbn detaljevisning";
  card.append(heading(vehicleLabel(offer.vehicleSpecification), 3), text("p", offer.provider, "provider"), selection, text("p", endSentence(offer.normalEndMechanism), "end-mechanism"), detailLink);
  const facts = document.createElement("dl");
  facts.className = "facts";
  facts.append(
    factRow("Leasingform", offer.supportedLeasingForm, formLabel),
    factRow("Restværdirisiko", offer.residualRiskAllocation, residualRiskLabel),
    factRow("Annonceret månedlig ydelse", offer.advertisedMonthlyPayment, money, "Oplyst af udbyderen"),
    factRow("Kontant behov ved start", offer.upfrontCashRequirement, money, "Beregnet af tjenesten"),
    factRow("Nominelt basisudlæg", offer.nominalBaseOutlay, money, "Beregnet af tjenesten"),
    factRow("Nominelt månedligt gennemsnit", offer.nominalMonthlyEquivalent, money, "Beregnet af tjenesten"),
    factRow("Fuld løbetid", offer.termMonths, (value) => `${{value}} måneder`),
    factRow("Kilometer om året", offer.annualMileageKm, (value) => `${{formatNumber(value)}} km`),
    factRow("Normal afslutning", offer.normalEndMechanism, endMechanismLabel),
  );
  card.append(facts);
  card.append(offerDetail(offer));
  if (offer.cashFlowBreakdown && offer.cashFlowBreakdown.length > 0) card.append(cashFlowBreakdown(offer.cashFlowBreakdown, offer));
  return card;
}}

function vehicleLabel(fact) {{
  return fact.state === "known" ? fact.value : `Køretøj: ${{factLabels[fact.state]}}`;
}}

function endSentence(fact) {{
  return fact.state === "known" ? endMechanismLabel(fact.value) : `Normal afslutning: ${{unavailableFactText(fact)}}`;
}}

function endMechanismLabel(value) {{
  const labels = {{
    return_to_provider: "Bilen afleveres til udbyderen ved normal udløb.",
    designate_third_party_buyer: "Den kommende leasingtager skal anvise en tredjepartskøber ved normal udløb.",
    mandatory_purchase_or_payoff: "Den kommende leasingtager skal købe bilen eller betale den aftalte restforpligtelse ved normal udløb.",
  }};
  return labels[value] || "Udbyderen har ikke beskrevet en normal afslutning med en standardiseret mekanisme.";
}}

function offerDetail(offer) {{
  const detail = document.createElement("details");
  detail.className = "offer-detail";
  detail.append(text("summary", "Se aftalens vilkår, usikkerheder og kilder"));
  const content = document.createElement("section");
  content.append(
    heading("Normal afslutning", 4),
    factRow("Normal afslutning", offer.normalEndMechanism, endMechanismLabel),
    factRow("Restværdirisiko", offer.residualRiskAllocation, residualRiskLabel),
    factRow("Registreringsafgift", offer.registrationTaxTreatment, registrationTaxLabel),
    factRow("Udbyderens formbetegnelse", offer.providerFormLabel, String),
    heading("Service og eksterne omkostninger", 4),
    listFact("Serviceordninger", offer.serviceArrangements, serviceArrangementText),
    listFact("Udelukket eller eksternt", offer.exclusions, serviceArrangementText),
    heading("Betingede eksponeringer", 4),
    exposureScenarioListFact(offer.exposureScenarios),
    providerSource(offer),
  );
  detail.append(content);
  return detail;
}}

function listFact(label, fact, itemText) {{
  const section = document.createElement("section");
  section.className = "detail-fact";
  section.append(heading(label, 5));
  if (fact.state === "known") {{
    const list = document.createElement("ul");
    fact.value.forEach((item) => list.append(text("li", itemText(item))));
    section.append(list);
  }} else {{
    section.append(text("p", unavailableFactText(fact)));
  }}
  section.append(evidenceDetails(label, fact));
  return section;
}}

function serviceArrangementText(item) {{
  const treatments = {{ included: "inkluderet", optional: "valgfri", required_external: "påkrævet eksternt", excluded: "udelukket" }};
  return `${{item.category}}: ${{treatments[item.treatment] || item.treatment}}. ${{item.scope}}`;
}}

function exposureText(item) {{
  const values = [];
  if (item.formula) values.push(scenarioFormulaLabel(item.formula));
  if (item.rateDkk !== undefined) values.push(`${{money(item.rateDkk)}} pr. enhed`);
  if (item.capDkk !== undefined) values.push(`loft ${{money(item.capDkk)}}`);
  if (item.amountDkk !== undefined) values.push(`fast beløb ${{money(item.amountDkk)}}`);
  const inputs = item.requiredInputs.length ? ` Kræver: ${{item.requiredInputs.join(", ")}}.` : " Beløb er ikke oplyst.";
  return `${{item.kind}}: ${{item.trigger}}${{inputs}}${{values.length ? ` Regel: ${{values.join(", ")}}.` : ""}}`;
}}

function scenarioFormulaLabel(value) {{
  const labels = {{
    rate_times_input: "sats × input",
    residual_value_minus_sale_proceeds: "max(0, aftalt restværdi − salgsprovenu)",
    fixed_amount: "fast beløb",
  }};
  return labels[value] || value;
}}

function exposureScenarioListFact(fact) {{
  const section = document.createElement("section");
  section.className = "detail-fact exposure-scenarios";
  section.append(heading("Mulige betalinger", 5));
  if (fact.state === "known") {{
    fact.value.forEach((scenario, index) => {{
      const item = document.createElement("section");
      item.className = "exposure-scenario";
      item.append(text("p", exposureText(scenario)), scenarioCalculationExample(scenario, index));
      section.append(item);
    }});
  }} else {{
    section.append(text("p", unavailableFactText(fact)));
  }}
  section.append(evidenceDetails("Mulige betalinger", fact));
  return section;
}}

function scenarioCalculationExample(scenario, scenarioIndex) {{
  const section = document.createElement("section");
  section.className = "scenario-calculation";
  const calculation = standardizedScenarioCalculation(scenario);
  if (calculation === null || !scenarioCanBeCalculated(scenario, calculation)) {{
    section.append(text("p", `${{scenario.kind}} kan ikke beregnes uden en dokumenteret regel og alle nødvendige input.`));
    return section;
  }}
  section.append(
    heading("Dit beregningseksempel", 6),
    text("p", "Dette er den kommende leasingtagers beregningseksempel, ikke en prognose."),
    text("p", "Beregningen ændrer ikke tilbudets viste basisbeløb eller rækkefølge."),
  );
  const result = document.createElement("output");
  result.className = "scenario-result";
  if (calculation.formula === "fixed_amount") {{
    renderScenarioResult(result, scenario, calculation, []);
    section.append(result);
    return section;
  }}
  const inputs = scenario.requiredInputs.map((inputName, inputIndex) => {{
    const identifier = `scenario-${{scenarioIndex}}-${{inputIndex}}`;
    const inputLabel = controlLabel(inputName, identifier);
    const input = document.createElement("input");
    input.id = identifier;
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.inputMode = "numeric";
    inputLabel.append(input);
    section.append(inputLabel);
    return input;
  }});
  const refreshResult = () => renderScenarioResult(result, scenario, calculation, inputs.map((input) => input.value));
  inputs.forEach((input) => input.addEventListener("input", refreshResult));
  section.append(result);
  refreshResult();
  return section;
}}

function standardizedScenarioCalculation(scenario) {{
  const definitions = {{
    excess_mileage: {{
      formula: "rate_times_input", requiredInputCount: 1, requiresRate: true,
      calculate: (scenario, inputs) => inputs[0] * scenario.rateDkk,
      arithmetic: (scenario, inputs) => `${{scenario.requiredInputs[0]}} (${{formatNumber(inputs[0])}}) × ${{money(scenario.rateDkk)}}`,
    }},
    residual_shortfall: {{
      formula: "residual_value_minus_sale_proceeds", requiredInputCount: 2, requiresFormula: true,
      requiredInputNames: ["Aftalt restværdi", "Salgsprovenu"],
      calculate: (_scenario, inputs) => Math.max(0, inputs[0] - inputs[1]),
      arithmetic: (scenario, inputs) => `max(0, ${{scenario.requiredInputs[0]}} (${{formatNumber(inputs[0])}}) − ${{scenario.requiredInputs[1]}} (${{formatNumber(inputs[1])}}))`,
    }},
    fixed_fee: {{
      formula: "fixed_amount", requiredInputCount: 0, requiresAmount: true,
      calculate: (scenario) => scenario.amountDkk,
      arithmetic: (scenario) => `fast beløb ${{money(scenario.amountDkk)}}`,
    }},
  }};
  const definition = definitions[scenario.kind];
  if (definition === undefined || (definition.requiresFormula && scenario.formula !== definition.formula)) return null;
  return !scenario.formula || scenario.formula === definition.formula ? definition : null;
}}

function scenarioCanBeCalculated(scenario, calculation) {{
  return scenario.requiredInputs.length === calculation.requiredInputCount
    && (!calculation.requiredInputNames || calculation.requiredInputNames.every((name, index) => scenario.requiredInputs[index] === name))
    && (!calculation.requiresRate || Number.isInteger(scenario.rateDkk))
    && (!calculation.requiresAmount || Number.isInteger(scenario.amountDkk));
}}

function renderScenarioResult(result, scenario, calculation, rawInputs) {{
  const inputs = rawInputs.map((value) => Number(value));
  if (rawInputs.length && (!rawInputs.every((value) => value !== "" && Number.isInteger(Number(value)) && Number(value) >= 0))) {{
    result.textContent = "Udfyld alle nødvendige input med hele, ikke-negative tal for at se eksemplet.";
    return;
  }}
  const amount = calculateScenarioExample(scenario, calculation, inputs);
  const arithmetic = scenarioArithmetic(scenario, calculation, inputs);
  const cappedArithmetic = Number.isInteger(scenario.capDkk)
    ? `min(${{arithmetic}}, loft ${{money(scenario.capDkk)}})`
    : arithmetic;
  result.textContent = `Regnestykke: ${{cappedArithmetic}} = ${{money(amount)}}.`;
}}

function calculateScenarioExample(scenario, calculation, inputs) {{
  const uncappedAmount = calculation.calculate(scenario, inputs);
  return Number.isInteger(scenario.capDkk) ? Math.min(uncappedAmount, scenario.capDkk) : uncappedAmount;
}}

function scenarioArithmetic(scenario, calculation, inputs) {{
  return calculation.arithmetic(scenario, inputs);
}}

function providerSource(offer) {{
  const paragraph = text("p", "Kontrollér altid aktuel pris og vilkår hos udbyderen.");
  const link = document.createElement("a");
  link.href = offer.providerSourceUrl;
  link.textContent = "Åbn udbyderens førstehåndskilde";
  link.rel = "noreferrer";
  paragraph.append(" ", link);
  return paragraph;
}}

function factRow(label, fact, formatter, origin = "Oplyst af udbyderen") {{
  const row = document.createElement("div");
  const title = document.createElement("dt");
  title.textContent = label;
  const value = document.createElement("dd");
  value.textContent = fact.state === "known" ? formatter(fact.valueDkk ?? fact.value) : unavailableFactText(fact);
  const originLabel = text("p", origin, "fact-origin");
  const evidence = evidenceDetails(label, fact);
  row.append(title, value, originLabel, evidence);
  return row;
}}

function evidenceDetails(label, fact) {{
  const evidence = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = `Kilde for ${{label}}`;
  const wording = text("p", fact.evidence.wording);
  const link = document.createElement("a");
  link.href = fact.evidence.sourceUrl;
  link.textContent = "Åbn udpeget førstehåndskilde";
  link.rel = "noreferrer";
  evidence.append(summary, wording, link);
  return evidence;
}}

function unavailableFactText(fact) {{
  const blockers = (fact.blockingFacts || []).map(blockingFactLabel);
  const explanations = {{
    not_stated: "Ikke oplyst af udbyderen.",
    unclear: "Udbyderens formulering kan ikke tolkes sikkert.",
    conflicting: "Kilderne modsiger hinanden.",
    not_applicable: "Ikke relevant for dette tilbud.",
  }};
  const stateText = explanations[fact.state] || factLabels[fact.state] || "Ikke oplyst";
  return blockers.length ? `${{stateText}} Mangler: ${{blockers.join(", ")}}.` : stateText;
}}

function blockingFactLabel(value) {{
  const labels = {{
    baseCashFlowStream: "en fuldstændig betalingsstrøm",
    termMonths: "fuld løbetid",
    advertisedMonthlyPayment: "annonceret månedlig ydelse",
    upfrontPayment: "udbetaling",
    normalEndMechanism: "normal afslutningsmekanisme",
  }};
  return labels[value] || value;
}}

function cashFlowBreakdown(events, offer) {{
  const section = document.createElement("details");
  section.className = "cash-flow-breakdown";
  const summary = document.createElement("summary");
  summary.textContent = "Betalingsstrøm bag beregningerne";
  const intro = text("p", "Hver linje indgår én gang i de viste beregninger. Beløb er nominelle og forudsætter normal afslutning.");
  const list = document.createElement("ul");
  events.forEach((event) => {{
    const item = document.createElement("li");
    const amount = event.amountDkk === null ? unavailableFactText(event) : money(event.amountDkk);
    const recurrence = event.recurrenceCount === null
      ? unavailableFactText(event)
      : event.recurrenceCount === 1 ? "én gang" : `${{event.recurrenceCount}} gange`;
    item.append(`[${{events.indexOf(event) + 1}}] ${{event.meaning}}: ${{cashFlowDirection(event.direction)}} ${{amount}} (${{amountBasisLabel(event.amountBasis)}}) · ${{recurrence}} · ${{cashFlowTiming(event.timing)}}. `);
    const source = document.createElement("a");
    source.href = event.evidence.sourceUrl;
    source.textContent = "Kildetekst";
    source.rel = "noreferrer";
    source.title = event.evidence.wording;
    item.append(source);
    list.append(item);
  }});
  section.append(summary, intro, list, calculationEquations(events, offer));
  return section;
}}

function calculationEquations(events, offer) {{
  const section = document.createElement("section");
  section.className = "calculation-equations";
  section.append(heading("Regnestykker", 4));
  const equations = document.createElement("ul");
  const upfrontReferences = eventReferences(events, (event) => event.direction === "payment" && event.timing === "acceptance_to_handover");
  appendEquation(equations, "Kontant behov ved start", upfrontReferences, offer.upfrontCashRequirement);
  const nominalReferences = eventReferences(events, () => true, true);
  appendEquation(equations, "Nominelt basisudlæg", nominalReferences, offer.nominalBaseOutlay);
  if (offer.nominalMonthlyEquivalent.state === "known" && offer.nominalBaseOutlay.state === "known" && offer.termMonths.state === "known") {{
    equations.append(text("li", `Nominelt månedligt gennemsnit = ${{money(offer.nominalBaseOutlay.valueDkk)}} / ${{offer.termMonths.value}} måneder = ${{money(offer.nominalMonthlyEquivalent.valueDkk)}} (afrundet til nærmeste kr.).`));
  }} else {{
    equations.append(text("li", `Nominelt månedligt gennemsnit: ${{unavailableFactText(offer.nominalMonthlyEquivalent)}}.`));
  }}
  section.append(equations);
  return section;
}}

function eventReferences(events, predicate, signed = false) {{
  return events
    .map((event, index) => ({{ event, index }}))
    .filter((entry) => entry.event.amountDkk !== null && entry.event.recurrenceCount !== null && predicate(entry.event))
    .map((entry) => `${{signed && entry.event.direction === "receipt" ? "−" : "+"}}[${{entry.index + 1}}]`)
    .join(" ")
    .replace(/^\\+/, "") || "ingen dokumenterede poster";
}}

function appendEquation(list, label, references, value) {{
  const result = value.state === "known" ? money(value.valueDkk) : unavailableFactText(value);
  list.append(text("li", `${{label}} = ${{references}} = ${{result}}.`));
}}

function cashFlowDirection(value) {{
  return value === "receipt" ? "forventet modtagelse" : value === "payment" ? "betaling" : "uafklaret betaling eller modtagelse";
}}

function amountBasisLabel(value) {{
  return value === "including_vat" ? "inkl. moms" : value === "excluding_vat" ? "ekskl. moms" : "ukendt beløbsgrundlag";
}}

function cashFlowTiming(value) {{
  const labels = {{
    acceptance_to_handover: "fra accept til udlevering",
    recurring: "løbende i perioden",
    normal_completion_end: "ved normal afslutning",
  }};
  return labels[value] || value;
}}

function coverage(coverage) {{
  const section = document.createElement("section");
  section.className = "coverage";
  section.append(heading("Dækning", 2));
  coverage.providers.forEach((provider) => section.append(text("p", `${{provider.name}} · ${{provider.designatedSource}} · ${{provider.quarantinedCandidateCount}} i karantæne`)));
  return section;
}}

function footer() {{
  return text("footer", "Tilbud kan være ændret eller udløbet siden data blev indsamlet. Filtrering er ikke personlig rangering.");
}}

function message(title, detail) {{
  const section = document.createElement("section");
  section.className = "message";
  section.append(heading(title, 1), text("p", detail));
  return section;
}}

function heading(value, level) {{
  return text(`h${{level}}`, value);
}}

function text(tagName, value, className) {{
  const element = document.createElement(tagName);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}}

function money(value) {{
  return `${{formatNumber(value)}} kr.`;
}}

function formatNumber(value) {{
  return new Intl.NumberFormat("da-DK").format(value);
}}

function formatDate(value) {{
  return new Intl.DateTimeFormat("da-DK", {{ dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Copenhagen" }}).format(new Date(value));
}}
"""


def stylesheet() -> str:
    return """@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600&display=swap');

:root { color: #21322c; background: #f6f5f0; font-family: "DM Sans", sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; overflow-x: hidden; }
.catalogue, .message { width: min(100% - 2rem, 72rem); margin: 0 auto; padding: 2.5rem 0; }
.site-header { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; border-bottom: 1px solid #ced6cf; padding-bottom: 1.25rem; }
h1, h2, h3 { font-family: Fraunces, serif; margin: 0; color: #183128; }
h1 { font-size: clamp(2rem, 6vw, 3.5rem); }
h2 { margin-top: 2.5rem; font-size: 1.4rem; }
h3 { font-size: 1.45rem; }
.filter-note, footer { color: #52645b; }
.filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: .8rem; margin: 1rem 0; padding: .9rem 1rem; background: #e8f0e8; border-radius: .75rem; }
.filters label { display: grid; gap: .35rem; min-width: 0; font-weight: 700; }
.filters input, .filters select { width: 100%; min-width: 0; border: 1px solid #9db9a4; border-radius: .35rem; padding: .55rem; color: #21322c; background: #fff; font: inherit; }
.offer-list { display: grid; gap: 1rem; margin-top: 1rem; }
.empty-state { padding: 1.5rem; border: 1px dashed #9db9a4; border-radius: .75rem; background: #fff; }
.offer-card { background: #fff; border: 1px solid #dfe4df; border-radius: 1rem; padding: clamp(1.25rem, 3vw, 2rem); box-shadow: 0 10px 30px #26372b0b; }
.provider { color: #52645b; font-weight: 700; margin: .5rem 0 1rem; }
.end-mechanism { border-left: .25rem solid #9db9a4; padding-left: .75rem; font-weight: 500; }
.facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem 1.5rem; margin: 1.5rem 0 0; }
.facts > div { border-top: 1px solid #e7ebe6; padding-top: .75rem; }
dt { color: #52645b; font-size: .9rem; }
dd { margin: .25rem 0 .4rem; font-weight: 700; }
.fact-origin { margin: -.15rem 0 .45rem; color: #52645b; font-size: .78rem; }
details { font-size: .875rem; color: #52645b; }
details p { margin: .5rem 0; }
.cash-flow-breakdown, .offer-detail { margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid #e7ebe6; }
.offer-detail > summary { font-weight: 700; cursor: pointer; }
.offer-detail section { margin-top: 1rem; }
.offer-detail h4, .offer-detail h5 { margin: 1rem 0 .4rem; }
.detail-fact ul { margin: .35rem 0; padding-left: 1.2rem; }
.comparison-control { margin: 1rem 0; font-weight: 700; }
.comparison-scroll { overflow-x: auto; max-width: 100%; }
.comparison-table { border-collapse: separate; border-spacing: 0; min-width: max-content; width: 100%; }
.comparison-table th, .comparison-table td { min-width: 15rem; padding: .75rem; vertical-align: top; text-align: left; border-bottom: 1px solid #dfe4df; background: #fff; }
.comparison-table th:first-child { position: sticky; left: 0; z-index: 1; min-width: 12rem; background: #e8f0e8; }
.cash-flow-breakdown ul { margin: .65rem 0 0; padding-left: 1.2rem; }
.cash-flow-breakdown li + li { margin-top: .45rem; }
.calculation-equations { margin-top: 1rem; }
.calculation-equations h4 { margin: 0; }
.exposure-scenario { margin: .75rem 0; padding: .75rem; border-left: 3px solid #9bbda5; background: #f6faf6; }
.exposure-scenario > p { margin-top: 0; }
.scenario-calculation { margin-top: .6rem; }
.scenario-calculation h6 { margin: 0 0 .35rem; font-size: 1rem; }
.scenario-calculation p { margin: .35rem 0; }
.scenario-calculation label { display: grid; gap: .25rem; max-width: 16rem; }
.scenario-calculation input { padding: .4rem; font: inherit; }
.scenario-result { display: block; margin-top: .6rem; font-weight: 700; }
a { color: #195c49; }
.coverage { margin-top: 2rem; padding: 1rem 1.25rem; background: #e8f0e8; border-radius: .75rem; }
footer { margin-top: 2rem; font-size: .875rem; }
@media (max-width: 38rem) { .site-header { display: block; } .site-header p { margin-bottom: 0; } .facts { grid-template-columns: 1fr; } }
"""
