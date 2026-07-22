from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


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
                    "vehicleSpecification",
                    "supportedLeasingForm",
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
                    "vehicleSpecification": {"$ref": "#/$defs/valueFact"},
                    "supportedLeasingForm": {"$ref": "#/$defs/valueFact"},
                    "advertisedMonthlyPayment": {"$ref": "#/$defs/moneyFact"},
                    "upfrontCashRequirement": {"$ref": "#/$defs/moneyFact"},
                    "nominalBaseOutlay": {"$ref": "#/$defs/moneyFact"},
                    "nominalMonthlyEquivalent": {"$ref": "#/$defs/moneyFact"},
                    "termMonths": {"$ref": "#/$defs/valueFact"},
                    "annualMileageKm": {"$ref": "#/$defs/valueFact"},
                    "normalEndMechanism": {"$ref": "#/$defs/valueFact"},
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
    return {
        "offerIdentity": string_value(offer, "offerIdentity"),
        "provider": string_value(offer, "provider"),
        "vehicleSpecification": project_vehicle_specification(offer.get("vehicleSpecification")),
        "supportedLeasingForm": project_value_fact(offer.get("supportedLeasingForm")),
        "advertisedMonthlyPayment": project_money_fact(offer.get("advertisedMonthlyPayment")),
        "upfrontCashRequirement": project_money_fact(offer.get("upfrontCashRequirement")),
        "nominalBaseOutlay": project_money_fact(offer.get("nominalBaseOutlay")),
        "nominalMonthlyEquivalent": project_money_fact(offer.get("nominalMonthlyEquivalent")),
        "termMonths": project_value_fact(offer.get("termMonths")),
        "annualMileageKm": project_value_fact(offer.get("annualMileageKm")),
        "normalEndMechanism": project_value_fact(offer.get("normalEndMechanism")),
    }


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
        for field_name in ("offerIdentity", "provider"):
            string_value(projection_offer, field_name)
        for field_name in ("vehicleSpecification", "supportedLeasingForm"):
            validate_projected_fact(projection_offer.get(field_name), "value")
        for field_name in (
            "advertisedMonthlyPayment",
            "upfrontCashRequirement",
            "nominalBaseOutlay",
            "nominalMonthlyEquivalent",
        ):
            validate_projected_fact(projection_offer.get(field_name), "valueDkk")
        for field_name in ("termMonths", "annualMileageKm", "normalEndMechanism"):
            validate_projected_fact(projection_offer.get(field_name), "value")


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
    renderCatalogue(projection);
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

function renderCatalogue(projection) {{
  const catalogue = document.createElement("section");
  catalogue.className = "catalogue";
  const header = document.createElement("header");
  header.className = "site-header";
  header.append(heading("Bilvalg", 1), text("p", `Katalog genereret ${{formatDate(projection.generatedAt)}}`));
  catalogue.append(header, heading("Filtre og tilbud", 2), filterNote());
  const offers = document.createElement("div");
  offers.className = "offer-list";
  const filters = filterControls(projection.offers, (selectedForm) => renderOffers(offers, projection.offers, selectedForm));
  catalogue.append(filters, offers, coverage(projection.coverage), footer());
  renderOffers(offers, projection.offers, "all");
  root.replaceChildren(catalogue);
}}

function filterNote() {{
  const note = document.createElement("p");
  note.className = "filter-note";
  note.textContent = "Tilbud vises i neutral kildeorden. Filtre og fakta er ikke en personlig rangering.";
  return note;
}}

function filterControls(offers, onFormChange) {{
  const controls = document.createElement("div");
  controls.className = "filters";
  const label = document.createElement("label");
  label.textContent = "Leasingform";
  const select = document.createElement("select");
  select.name = "leasing-form";
  const forms = [...new Set(offers
    .filter((offer) => offer.supportedLeasingForm.state === "known")
    .map((offer) => offer.supportedLeasingForm.value))];
  select.append(option("all", "Alle former"), ...forms.map((form) => option(form, formLabel(form))));
  select.addEventListener("change", () => onFormChange(select.value));
  label.append(select);
  controls.append(label);
  return controls;
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

function renderOffers(container, offers, selectedForm) {{
  const visibleOffers = selectedForm === "all"
    ? offers
    : offers.filter((offer) => offer.supportedLeasingForm.state === "known" && offer.supportedLeasingForm.value === selectedForm);
  container.replaceChildren(...visibleOffers.map(offerCard));
}}

function offerCard(offer) {{
  const card = document.createElement("article");
  card.className = "offer-card";
  card.append(heading(vehicleLabel(offer.vehicleSpecification), 3), text("p", offer.provider, "provider"), text("p", endSentence(offer.normalEndMechanism), "end-mechanism"));
  const facts = document.createElement("dl");
  facts.className = "facts";
  facts.append(
    factRow("Leasingform", offer.supportedLeasingForm, formLabel),
    factRow("Annonceret månedlig ydelse", offer.advertisedMonthlyPayment, money),
    factRow("Kontant behov ved start", offer.upfrontCashRequirement, money),
    factRow("Nominelt basisudlæg", offer.nominalBaseOutlay, money),
    factRow("Nominelt månedligt gennemsnit", offer.nominalMonthlyEquivalent, money),
    factRow("Fuld løbetid", offer.termMonths, (value) => `${{value}} måneder`),
    factRow("Kilometer om året", offer.annualMileageKm, (value) => `${{formatNumber(value)}} km`),
    factRow("Normal afslutning", offer.normalEndMechanism, String),
  );
  card.append(facts);
  return card;
}}

function vehicleLabel(fact) {{
  return fact.state === "known" ? fact.value : `Køretøj: ${{factLabels[fact.state]}}`;
}}

function endSentence(fact) {{
  return fact.state === "known" ? fact.value : `Normal afslutning: ${{factLabels[fact.state]}}.`;
}}

function factRow(label, fact, formatter) {{
  const row = document.createElement("div");
  const title = document.createElement("dt");
  title.textContent = label;
  const value = document.createElement("dd");
  value.textContent = fact.state === "known" ? formatter(fact.valueDkk ?? fact.value) : factLabels[fact.state];
  const evidence = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = `Kilde for ${{label}}`;
  const wording = text("p", fact.evidence.wording);
  const link = document.createElement("a");
  link.href = fact.evidence.sourceUrl;
  link.textContent = "Åbn udpeget førstehåndskilde";
  link.rel = "noreferrer";
  evidence.append(summary, wording, link);
  row.append(title, value, evidence);
  return row;
}}

function coverage(coverage) {{
  const section = document.createElement("section");
  section.className = "coverage";
  section.append(heading("Dækning", 2));
  coverage.providers.forEach((provider) => section.append(text("p", `${{provider.name}} · ${{provider.designatedSource}} · ${{provider.quarantinedCandidateCount}} i karantæne`)));
  return section;
}}

function footer() {{
  return text("footer", "Tilbud kan være ændret eller udløbet siden data blev indsamlet. Kataloget er ikke en personlig rangering.");
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
body { margin: 0; }
.catalogue, .message { width: min(100% - 2rem, 72rem); margin: 0 auto; padding: 2.5rem 0; }
.site-header { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; border-bottom: 1px solid #ced6cf; padding-bottom: 1.25rem; }
h1, h2, h3 { font-family: Fraunces, serif; margin: 0; color: #183128; }
h1 { font-size: clamp(2rem, 6vw, 3.5rem); }
h2 { margin-top: 2.5rem; font-size: 1.4rem; }
h3 { font-size: 1.45rem; }
.filter-note, footer { color: #52645b; }
.filters { margin: 1rem 0; padding: .9rem 1rem; background: #e8f0e8; border-radius: .75rem; }
.filters label { display: grid; gap: .35rem; width: min(100%, 18rem); font-weight: 700; }
.filters select { border: 1px solid #9db9a4; border-radius: .35rem; padding: .55rem; color: #21322c; background: #fff; font: inherit; }
.offer-list { display: grid; gap: 1rem; margin-top: 1rem; }
.offer-card { background: #fff; border: 1px solid #dfe4df; border-radius: 1rem; padding: clamp(1.25rem, 3vw, 2rem); box-shadow: 0 10px 30px #26372b0b; }
.provider { color: #52645b; font-weight: 700; margin: .5rem 0 1rem; }
.end-mechanism { border-left: .25rem solid #9db9a4; padding-left: .75rem; font-weight: 500; }
.facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem 1.5rem; margin: 1.5rem 0 0; }
.facts > div { border-top: 1px solid #e7ebe6; padding-top: .75rem; }
dt { color: #52645b; font-size: .9rem; }
dd { margin: .25rem 0 .4rem; font-weight: 700; }
details { font-size: .875rem; color: #52645b; }
details p { margin: .5rem 0; }
a { color: #195c49; }
.coverage { margin-top: 2rem; padding: 1rem 1.25rem; background: #e8f0e8; border-radius: .75rem; }
footer { margin-top: 2rem; font-size: .875rem; }
@media (max-width: 38rem) { .site-header { display: block; } .site-header p { margin-bottom: 0; } .facts { grid-template-columns: 1fr; } }
"""
