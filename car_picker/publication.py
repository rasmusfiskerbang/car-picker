from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, JsonValue

from car_picker.catalogue_model import (
    CatalogueDataset,
    CatalogueOffer,
    KnownFact,
    VehicleSpecification,
)
from car_picker.comparison import (
    calculate_catalogue_offer_comparison,
    reconcile_provider_advertised_aggregate,
)
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
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
    dataset = CatalogueDataset.model_validate(read_json(dataset_path))
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
        "aggregateReconciliation": project_aggregate_reconciliation(offer),
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


def project_aggregate_reconciliation(offer: CatalogueOffer) -> dict[str, Any]:
    diagnostic = reconcile_provider_advertised_aggregate(
        offer.model_dump(mode="json", by_alias=True)
    )
    assertion = diagnostic["providerAdvertisedAggregate"]
    return {
        "status": diagnostic["status"],
        "providerAdvertisedAggregate": (
            None
            if assertion is None
            else {
                "valueDkk": assertion["valueDkk"],
                "evidence": assertion["evidence"],
            }
        ),
        "reconstructedNominalBaseOutlayDkk": diagnostic[
            "reconstructedNominalBaseOutlayDkk"
        ],
        "unexplainedDifferenceDkk": diagnostic["differenceDkk"],
        "toleranceDkk": diagnostic["toleranceDkk"],
    }


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


def serialize_fact(value: BaseModel | None) -> dict[str, Any]:
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
    output_path = output_path.absolute()
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
        build_frontend(staging_path)
        verify_static_artifact(staging_path)
        replace_directory(staging_path, output_path)


def build_frontend(staging_path: Path) -> None:
    """Generate the browser contract input and compile the production application."""
    generated_schema = FRONTEND_ROOT / "src/generated/presentation-schema.json"
    generated_schema.write_text(
        json.dumps(PRESENTATION_SCHEMA, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    environment = os.environ | {"CAR_PICKER_SITE_OUTPUT": str(staging_path)}
    if shutil.which("node", path=environment.get("PATH")) is None:
        codex_node_directory = Path(
            "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin"
        )
        if (codex_node_directory / "node").is_file():
            environment["PATH"] = (
                f"{codex_node_directory}{os.pathsep}{environment.get('PATH', '')}"
            )
    result = subprocess.run(
        ["pnpm", "build"],
        cwd=FRONTEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(
            output
            for output in (result.stdout.strip(), result.stderr.strip())
            if output
        )
        raise ValueError(f"frontend build failed: {detail}")


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
    index = (site_path / "index.html").read_text(encoding="utf-8")
    if 'type="module"' not in index or 'src="./app.js"' not in index:
        raise ValueError("static artifact browser application is incomplete")


def contains_forbidden_artifact_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in FORBIDDEN_ARTIFACT_KEYS or contains_forbidden_artifact_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_forbidden_artifact_key(item) for item in value)
    return False


def replace_directory(staging_path: Path, output_path: Path) -> None:
    """Publish an immutable artifact through one atomic pointer replacement."""
    if output_path.exists() and not output_path.is_symlink():
        raise ValueError(
            "existing static artifact predates atomic publication; "
            "move it aside before rebuilding"
        )
    identifier = uuid.uuid4().hex
    artifact_path = output_path.with_name(f".{output_path.name}.artifact-{identifier}")
    next_link = output_path.with_name(f".{output_path.name}.next-{identifier}")
    previous_artifact = output_path.resolve() if output_path.is_symlink() else None
    os.replace(staging_path, artifact_path)
    try:
        next_link.symlink_to(artifact_path.name, target_is_directory=True)
        os.replace(next_link, output_path)
    except BaseException:
        if next_link.is_symlink():
            next_link.unlink()
        if artifact_path.exists():
            shutil.rmtree(artifact_path)
        raise
    if (
        previous_artifact is not None
        and previous_artifact.parent == output_path.parent
        and previous_artifact.name.startswith(f".{output_path.name}.artifact-")
    ):
        shutil.rmtree(previous_artifact)


def object_value(value: JsonValue, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value
