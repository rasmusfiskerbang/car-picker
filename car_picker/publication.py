from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from car_picker.catalogue_model import (
    CatalogueDataset,
    CatalogueOffer,
    KnownFact,
    VehicleSpecification,
    from_legacy_dataset,
)
from car_picker.comparison import calculate_catalogue_offer_comparison
from car_picker.presentation_model import (
    CataloguePresentation,
    presentation_json_schema,
)


PRESENTATION_SCHEMA_VERSION = "catalogue-presentation/v1"
STATIC_ARTIFACT_FILENAMES = {
    "app.js",
    "index.html",
    "projection-schema.json",
    "projection.json",
    "styles.css",
}
FORBIDDEN_ARTIFACT_KEYS = {
    "contentSha256",
    "hash",
    "parserMetadata",
    "parserVersion",
    "quarantineReasons",
    "sourceMetadata",
}

PRESENTATION_SCHEMA = presentation_json_schema()


def build_site(dataset_path: Path, output_path: Path) -> None:
    """Project a canonical catalogue dataset and atomically replace a static site."""
    source = dict(read_json(dataset_path))
    dataset = from_legacy_dataset(
        source,
        require_complete_replacement=True,
    )
    projection = project_catalogue(dataset)
    validate_presentation_projection(projection)
    write_site_atomically(output_path, projection)


def read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Cannot read canonical catalogue dataset at {path}: {error}"
        ) from error
    return object_value(value, "canonical catalogue dataset")


def project_catalogue(dataset: CatalogueDataset) -> dict[str, Any]:
    return {
        "schemaVersion": PRESENTATION_SCHEMA_VERSION,
        "generatedAt": dataset.generated_at,
        "coverage": {
            "providers": [
                provider.model_dump(mode="json", by_alias=True)
                for provider in dataset.coverage.providers
            ]
        },
        "coverageEnded": [
            provider.model_dump(mode="json", by_alias=True)
            for provider in dataset.coverage_ended
        ],
        "offers": [project_offer(offer) for offer in dataset.catalogue_offers],
    }


def project_offer(offer: CatalogueOffer) -> dict[str, Any]:
    comparison_values = calculate_catalogue_offer_comparison(offer)
    source_url = canonical_source_url(offer)
    projected_offer = {
        "offerIdentity": offer.offer_identity,
        "provider": offer.provider,
        "providerSourceUrl": source_url,
        "vehicleSpecification": project_canonical_vehicle(offer),
        "supportedLeasingForm": serialize_fact(offer.supported_leasing_form),
        "providerFormLabel": project_canonical_provider_form_label(offer),
        "residualRiskAllocation": serialize_fact(offer.residual_risk_allocation),
        "registrationTaxTreatment": serialize_fact(offer.registration_tax_treatment),
        "serviceArrangements": serialize_fact(offer.service_arrangements),
        "exclusions": serialize_fact(offer.exclusions),
        "exposureScenarios": serialize_fact(offer.exposure_scenarios),
        "advertisedMonthlyPayment": serialize_fact(offer.advertised_monthly_payment),
        "upfrontCashRequirement": project_derived_money_fact(
            comparison_values["upfrontCashRequirement"], offer
        ),
        "nominalBaseOutlay": project_derived_money_fact(
            comparison_values["nominalBaseOutlay"], offer
        ),
        "nominalMonthlyEquivalent": project_derived_money_fact(
            comparison_values["nominalMonthlyEquivalent"], offer
        ),
        "operationReadiness": comparison_values["operationReadiness"],
        "termMonths": serialize_fact(offer.term_months),
        "annualMileageKm": serialize_fact(offer.annual_mileage_km),
        "normalEndMechanism": serialize_fact(offer.normal_end_mechanism),
    }
    projected_offer["cashFlowBreakdown"] = [
        {
            key: value
            for key, value in event.model_dump(
                mode="json",
                by_alias=True,
                exclude={"included_in_base"},
                exclude_none=False,
            ).items()
            if value is not None or key in {"amountDkk", "recurrenceCount"}
        }
        for event in offer.base_cash_flow_stream
    ]
    return projected_offer


def project_derived_money_fact(
    value: Mapping[str, Any], offer: CatalogueOffer
) -> dict[str, Any]:
    calculation = {
        "method": "base_cash_flow_stream",
        "inputEvidence": [
            event.evidence.model_dump(mode="json", by_alias=True)
            for event in offer.base_cash_flow_stream
        ],
    }
    if value["state"] == "known":
        return {
            "state": "known",
            "valueDkk": value["valueDkk"],
            "calculation": calculation,
        }
    return {
        "state": "not_stated",
        "calculation": calculation,
        "blockingFacts": value["blockingFacts"],
    }


def serialize_fact(value: Any) -> dict[str, Any]:
    if value is None:
        raise ValueError("admitted catalogue offer requires public comparison facts")
    return cast(
        dict[str, Any],
        value.model_dump(mode="json", by_alias=True, exclude_none=True),
    )


def project_canonical_vehicle(offer: CatalogueOffer) -> dict[str, Any]:
    fact = serialize_fact(offer.vehicle_specification)
    if isinstance(offer.vehicle_specification, KnownFact) and isinstance(
        offer.vehicle_specification.value, VehicleSpecification
    ):
        vehicle = offer.vehicle_specification.value
        fact["value"] = " ".join(
            part for part in (vehicle.make, vehicle.model, vehicle.trim) if part
        )
    return fact


def project_canonical_provider_form_label(offer: CatalogueOffer) -> dict[str, Any]:
    if offer.provider_form_label is not None:
        return serialize_fact(offer.provider_form_label)
    fact = serialize_fact(offer.supported_leasing_form)
    if fact["state"] == "known":
        fact["value"] = offer.supported_leasing_form.evidence.wording
    return fact


def canonical_source_url(offer: CatalogueOffer) -> str:
    if offer.canonical_offer_url:
        return offer.canonical_offer_url
    return offer.base_cash_flow_stream[0].evidence.source_url


def validate_presentation_projection(projection: Mapping[str, Any]) -> None:
    """Validate the browser contract before it is published."""
    CataloguePresentation.model_validate(projection)


def write_site_atomically(output_path: Path, projection: Mapping[str, Any]) -> None:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".car-picker-site-", dir=output_path.parent
    ) as staging_root:
        staging_path = Path(staging_root) / "site"
        staging_path.mkdir()
        (staging_path / "projection.json").write_text(
            json.dumps(projection, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        (staging_path / "projection-schema.json").write_text(
            json.dumps(PRESENTATION_SCHEMA, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        (staging_path / "index.html").write_text(index_html(), encoding="utf-8")
        (staging_path / "app.js").write_text(browser_app(), encoding="utf-8")
        (staging_path / "styles.css").write_text(stylesheet(), encoding="utf-8")
        verify_static_artifact(staging_path)
        replace_directory(staging_path, output_path)


def verify_static_artifact(site_path: Path) -> None:
    """Reject an incomplete or internally detailed static artifact before publication."""
    entries = tuple(site_path.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in entries):
        raise ValueError("static artifact must contain only approved regular files")
    files = {path.name for path in entries}
    if files != STATIC_ARTIFACT_FILENAMES:
        raise ValueError("static artifact contains unexpected or missing files")
    projection = read_json(site_path / "projection.json")
    validate_presentation_projection(projection)
    schema = read_json(site_path / "projection-schema.json")
    if schema != PRESENTATION_SCHEMA:
        raise ValueError(
            "static artifact must export the presentation serialization schema"
        )
    if contains_forbidden_artifact_key(projection):
        raise ValueError("static artifact projection contains internal metadata")
    app = (site_path / "app.js").read_text(encoding="utf-8")
    index = (site_path / "index.html").read_text(encoding="utf-8")
    if (
        'fetch("projection.json"' not in app
        or "hashchange" not in app
        or 'src="app.js"' not in index
    ):
        raise ValueError("static artifact browser application is incomplete")
    validate_javascript_delimiters(app)


def validate_javascript_delimiters(source: str) -> None:
    """Reject browser output with unclosed syntax delimiters before it replaces the site."""
    closing_for = {"(": ")", "[": "]", "{": "}"}
    delimiters: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(source):
        character = source[index]
        next_character = source[index + 1] if index + 1 < len(source) else ""
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character == "/" and next_character == "/":
            index = source.find("\n", index + 2)
            if index == -1:
                break
            continue
        elif character == "/" and next_character == "*":
            comment_end = source.find("*/", index + 2)
            if comment_end == -1:
                raise ValueError(
                    "static artifact browser application has an unclosed comment"
                )
            index = comment_end + 2
            continue
        elif character in closing_for:
            delimiters.append(character)
        elif character in closing_for.values():
            if not delimiters or closing_for[delimiters.pop()] != character:
                raise ValueError(
                    "static artifact browser application has mismatched delimiters"
                )
        index += 1
    if quote is not None or delimiters:
        raise ValueError(
            "static artifact browser application has unclosed syntax delimiters"
        )


def contains_forbidden_artifact_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in FORBIDDEN_ARTIFACT_KEYS or contains_forbidden_artifact_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_forbidden_artifact_key(item) for item in value)
    return False


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
  catalogue.append(filters, comparison, offers, coverage(projection.coverage, projection.coverageEnded, projection.generatedAt), footer(projection.generatedAt));
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
  input.placeholder = "Fx Hyundai IONIQ 5";
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
  page.append(back, offerCard(offer), footer(projection.generatedAt)); root.replaceChildren(page);
}}

function renderComparison(projection, identities) {{
  const offers = identities.map(decodeURIComponent).map((identity) => projection.offers.find((offer) => offer.offerIdentity === identity)).filter(Boolean);
  if (offers.length < 2) return root.replaceChildren(message("Sammenligning kan ikke vises", "Vælg mindst to tilbud fra kataloget."));
  const page = document.createElement("section"); page.className = "catalogue";
  const back = document.createElement("a"); back.href = "#"; back.textContent = "Tilbage til kataloget";
  page.append(back, heading("Sammenlign tilbud", 1), comparisonTable(offers), footer(projection.generatedAt)); root.replaceChildren(page);
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
      formula: "rate_times_input", requiredInputCount: 1, requiredInputKinds: ["excess_distance_km"], requiresRate: true,
      calculate: (scenario, inputs) => inputs[0] * scenario.rateDkk,
      arithmetic: (scenario, inputs) => `${{scenario.requiredInputs[0]}} (${{formatNumber(inputs[0])}}) × ${{money(scenario.rateDkk)}}`,
    }},
    residual_shortfall: {{
      formula: "residual_value_minus_sale_proceeds", requiredInputCount: 2, requiredInputKinds: ["residual_value_dkk", "sale_proceeds_dkk"], requiresFormula: true,
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
    && (!calculation.requiredInputKinds || (Array.isArray(scenario.inputKinds) && calculation.requiredInputKinds.every((kind, index) => scenario.inputKinds[index] === kind)))
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
  if (fact.calculation) {{
    summary.textContent = `Beregning for ${{label}}`;
    const method = text("p", "Beregnet fra tilbuddets dokumenterede betalingsstrøm.");
    evidence.append(summary, method);
    fact.calculation.inputEvidence.forEach((input) => {{
      const link = document.createElement("a");
      link.href = input.sourceUrl;
      link.textContent = input.wording;
      link.rel = "noreferrer";
      evidence.append(link);
    }});
    return evidence;
  }}
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
    providerAdvertisedAggregateMismatch: "udbyderens samlede beløb stemmer ikke med betalingsstrømmen",
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

function coverage(coverage, coverageEnded, generatedAt) {{
  const section = document.createElement("section");
  section.className = "coverage";
  section.append(
    heading("Katalogets dækning", 2),
    text("p", `Katalogdatasættet blev genereret ${{formatDate(generatedAt)}}.`),
    text("p", "Dækkede udbydere og deres udpegede tilbudskilder i neutral kildeorden:"),
  );
  coverage.providers.forEach((provider) => section.append(text("p", `${{provider.name}} · ${{provider.designatedSource}} · ${{provider.quarantinedCandidateCount}} kandidater holdt tilbage.`)));
  coverageEnded.forEach((provider) => section.append(text("p", `Dækning af ${{provider.name}} sluttede ${{formatDate(provider.coverageEndedAt)}}.`)));
  section.append(
    text("p", "Kataloget dækker muligvis ikke hele det danske marked."),
    text("p", "Dette viser aktiv katalogdækning, ikke vurderingen af andre udbydere."),
  );
  return section;
}}

function footer(generatedAt) {{
  const element = document.createElement("footer");
  element.append(
    text("p", `Katalogdatasættet blev genereret ${{formatDate(generatedAt)}}.`),
    text("p", "Tilbud kan være ændret eller udløbet siden data blev indsamlet. Filtrering er ikke personlig rangering."),
  );
  return element;
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
