from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, NoReturn

import typer
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from car_picker import (
    ActiveProvider,
    AvailableResult,
    CatalogueSite,
    Catalogue,
    CatalogueDataset as StrictCatalogueDataset,
    CatalogueOffer as StrictCatalogueOffer,
    CatalogueRefreshError,
    CatalogueRefreshFailure,
    CatalogueRefreshReport,
    DEFAULT_LEGAL_RECORD,
    InactiveProvider,
    InactiveReason,
    KnownFact,
    MaterializedResult,
    OfferIdentity,
    ProviderId,
    ProviderRecordInvalid,
    ProviderRegistry,
    ProviderRegistrySnapshot,
    ProviderStatus,
    QuarantinedCandidate,
    RegistryInvalid,
    RefreshFailureCategory,
    UnavailableFact,
    production_provider_adapters,
    validate_legal_release,
    validate_repository_history,
)
from car_picker import SiteBuildError


app = typer.Typer(
    help="Build the static evidence-backed leasing catalogue.",
    no_args_is_help=True,
    rich_markup_mode=None,
)


@dataclass(frozen=True)
class CliState:
    workspace: Path
    json_output: bool


class CliReportModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class CatalogueOfferReport(CliReportModel):
    kind: Literal["catalogue-offer"]
    offer: StrictCatalogueOffer


class QuarantinedCandidateReport(CliReportModel):
    kind: Literal["quarantined-candidate"]
    quarantined_candidate: QuarantinedCandidate = Field(alias="quarantinedCandidate")


@app.callback()
def root_callback(
    context: typer.Context,
    workspace: Annotated[
        Path,
        typer.Option(
            "--workspace",
            "-C",
            help="Workspace root containing the conventional Registry and artefacts.",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Render a stable JSON report."),
    ] = False,
) -> None:
    context.ensure_object(dict)
    context.obj["state"] = CliState(
        workspace=workspace.resolve(), json_output=json_output
    )


provider_app = typer.Typer(
    help="Inspect and replace complete Provider Registry records.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(provider_app, name="provider")

_PROVIDER_ID_ADAPTER = TypeAdapter(ProviderId)
_PROVIDER_STATUS_ADAPTER = TypeAdapter(ProviderStatus)
_INACTIVE_REASON_ADAPTER = TypeAdapter(InactiveReason)
_OFFER_IDENTITY_ADAPTER = TypeAdapter(OfferIdentity)


def parse_provider_id(value: str) -> ProviderId:
    try:
        return _PROVIDER_ID_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise typer.BadParameter(
            "must be a lowercase hyphenated Provider ID"
        ) from error


def parse_provider_status(value: str) -> ProviderStatus:
    try:
        return _PROVIDER_STATUS_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise typer.BadParameter("must be active or inactive") from error


def parse_inactive_reason(value: str) -> InactiveReason:
    try:
        return _INACTIVE_REASON_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise typer.BadParameter("must be deferred, ineligible, or blocked") from error


def parse_offer_identity(value: str) -> OfferIdentity:
    try:
        return _OFFER_IDENTITY_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise typer.BadParameter("must be a valid Offer Identity") from error


catalogue_app = typer.Typer(
    help="Refresh and inspect the active strict Catalogue Dataset.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(catalogue_app, name="catalogue")


@catalogue_app.command(
    "inspect",
    help="Inspect the active Dataset, one Offer, or one Quarantined Candidate.",
)
def inspect_catalogue_command(
    context: typer.Context,
    offer_identity: Annotated[
        OfferIdentity | None,
        typer.Argument(
            parser=parse_offer_identity,
            help="Optional exact Offer Identity or Quarantined Candidate identity.",
        ),
    ] = None,
) -> None:
    state = cli_state(context)
    catalogue = Catalogue(state.workspace)
    dataset_path = catalogue.dataset_path
    try:
        inspected = catalogue.inspect(offer_identity)
    except LookupError as error:
        emit_catalogue_error(
            state,
            dataset_path,
            CatalogueRefreshError.operational(
                "catalogue.record_not_found", str(error)
            ).failure,
        )
    except ValueError as error:
        emit_catalogue_error(
            state,
            dataset_path,
            CatalogueRefreshError.operational(
                "catalogue.dataset_invalid",
                f"cannot inspect the active Catalogue Dataset: {error}",
            ).failure,
        )

    if isinstance(inspected, StrictCatalogueDataset):
        emit_catalogue_dataset(state, inspected)
        return
    if isinstance(inspected, QuarantinedCandidate):
        emit_quarantined_candidate(state, inspected)
        return
    emit_catalogue_offer(state, inspected)


def emit_catalogue_dataset(
    state: CliState,
    dataset: StrictCatalogueDataset,
) -> None:
    serialized = dataset.model_dump(mode="json", by_alias=True)
    if state.json_output:
        typer.echo(
            json.dumps(
                {"kind": "catalogue-dataset", "dataset": serialized},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    lines = [
        "Catalogue Dataset",
        f"Schema version: {serialized['schemaVersion']}",
        f"Generated at: {serialized['generatedAt']}",
        f"Providers: {len(dataset.providers)}",
        f"Catalogue Offers: {len(dataset.offers)}",
        f"Quarantined Candidates: {len(dataset.quarantined_candidates)}",
    ]
    if dataset.offers:
        lines.append("Offer Identities:")
        lines.extend(f"  {offer.offer_identity}" for offer in dataset.offers)
    if dataset.quarantined_candidates:
        lines.append("Quarantined Candidate Identities:")
        lines.extend(
            f"  {candidate.offer_identity}"
            for candidate in dataset.quarantined_candidates
        )
    lines.extend(
        [
            "Complete Dataset Record:",
            _serialize_human_record(serialized),
        ]
    )
    typer.echo("\n".join(lines))


def emit_catalogue_offer(
    state: CliState,
    offer: StrictCatalogueOffer,
) -> None:
    vehicle = offer.vehicle_specification
    vehicle_name = f"{vehicle.make} {vehicle.model}"
    if isinstance(vehicle.trim, KnownFact):
        vehicle_name += f" {vehicle.trim.value}"
    lines = [
        f"Catalogue Offer: {offer.offer_identity}",
        f"Provider: {offer.provider_id}",
        f"Vehicle: {vehicle_name}",
        f"Leasing form: {offer.supported_leasing_form}",
        f"Term: {offer.term_months} months",
        f"Source: {offer.canonical_offer_url}",
        f"Images: {len(offer.image_urls)}",
        f"Advertised Total: {_format_fact(offer.advertised_total)}",
        "Base Cash-flow Stream:",
    ]
    for event in offer.base_cash_flow_stream:
        amount = (
            f"{event.amount.value} DKK"
            if isinstance(event.amount, KnownFact)
            else f"{event.amount.state}"
        )
        lines.append(f"  month {event.month} — {event.key}: {event.direction} {amount}")
    lines.extend(
        [
            f"Calculated Total: {_format_result(offer.calculated_total)}",
            "Calculated Monthly Total: "
            f"{_format_result(offer.calculated_monthly_total)}",
            f"Service arrangements: {_format_fact(offer.service_arrangements)}",
        ]
    )
    _emit_catalogue_record(
        state,
        CatalogueOfferReport(kind="catalogue-offer", offer=offer),
        tuple(lines),
        "Complete Offer Record",
    )


def emit_quarantined_candidate(
    state: CliState,
    candidate: QuarantinedCandidate,
) -> None:
    lines = [
        f"Quarantined Candidate: {candidate.offer_identity}",
        f"Provider: {candidate.provider_id}",
        f"Canonical source: {candidate.canonical_source_url}",
        "Quarantine reasons:",
    ]
    for reason in candidate.reasons:
        lines.append(f"  {reason.criterion} — {reason.state} [{reason.code}]")
        for evidence in reason.evidence:
            lines.append(f"    {evidence.source_url}: {evidence.excerpt}")
    _emit_catalogue_record(
        state,
        QuarantinedCandidateReport(
            kind="quarantined-candidate",
            quarantined_candidate=candidate,
        ),
        tuple(lines),
        "Compact Candidate Record",
    )


def _emit_catalogue_record(
    state: CliState,
    report: CatalogueOfferReport | QuarantinedCandidateReport,
    human_lines: tuple[str, ...],
    record_heading: str,
) -> None:
    if state.json_output:
        typer.echo(
            json.dumps(
                report.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    record = (
        report.offer
        if isinstance(report, CatalogueOfferReport)
        else report.quarantined_candidate
    )
    typer.echo(
        "\n".join(
            [
                *human_lines,
                f"{record_heading}:",
                _serialize_human_record(record.model_dump(mode="json", by_alias=True)),
            ]
        )
    )


def _format_fact(fact: object) -> str:
    if isinstance(fact, KnownFact):
        return str(fact.value)
    if isinstance(fact, UnavailableFact):
        return fact.state
    raise TypeError("expected a Catalogue Fact")


def _serialize_human_record(serialized: object) -> str:
    return json.dumps(serialized, ensure_ascii=False, indent=2, sort_keys=True)


def _format_result(result: MaterializedResult) -> str:
    if isinstance(result, AvailableResult):
        return f"{result.value.amount_dkk:g} DKK"
    return "unavailable (" + ", ".join(reason.code for reason in result.reasons) + ")"


def emit_catalogue_error(
    state: CliState,
    path: Path,
    failure: CatalogueRefreshFailure,
) -> NoReturn:
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "category": failure.category,
                        "code": failure.code,
                        "message": failure.message,
                    },
                    "safeState": {"catalogueDataset": str(path), "unchanged": True},
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            err=True,
        )
    else:
        typer.echo(
            f"error [{failure.code}] ({failure.category}): {failure.message}",
            err=True,
        )
        typer.echo(
            f"safe state: active Catalogue Dataset at {path} is unchanged", err=True
        )
    raise typer.Exit(code=catalogue_refresh_exit_code(failure.category))


@provider_app.command("inspect", help="Inspect the ordered Provider Registry.")
def inspect_provider_command(
    context: typer.Context,
    provider_id: Annotated[
        ProviderId | None,
        typer.Argument(
            parser=parse_provider_id,
            help="Optional stable Provider ID to inspect.",
        ),
    ] = None,
) -> None:
    state = cli_state(context)
    registry_path = provider_registry_path(state.workspace)
    registry = open_provider_registry_or_exit(state, registry_path)
    snapshot = registry.snapshot()
    if provider_id is None:
        emit_provider_snapshot(state, snapshot)
        return

    provider = find_provider(snapshot, provider_id)
    if provider is None:
        emit_provider_error(
            state,
            registry_path,
            "provider.not_found",
            f"no Provider has ID {provider_id!r}",
            exit_code=1,
        )
    emit_provider_record(state, provider)


@provider_app.command("set", help="Replace one complete Provider record.")
def set_provider_command(
    context: typer.Context,
    provider_id: Annotated[
        ProviderId,
        typer.Argument(
            parser=parse_provider_id,
            help="Stable Provider ID.",
        ),
    ],
    status: Annotated[
        ProviderStatus,
        typer.Argument(
            parser=parse_provider_status,
            help="The complete record status.",
        ),
    ],
    reason: Annotated[
        InactiveReason | None,
        typer.Option(
            parser=parse_inactive_reason,
            help="Required for inactive: deferred, ineligible, or blocked.",
        ),
    ] = None,
    explanation: Annotated[
        str | None,
        typer.Option(help="Required for inactive Provider records."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(help="Display name; required when adding a new Provider."),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option(
            help="General public HTTPS website; required when adding a new Provider."
        ),
    ] = None,
) -> None:
    state = cli_state(context)
    registry_path = provider_registry_path(state.workspace)

    registry = open_provider_registry_or_exit(state, registry_path)
    existing = find_provider(registry.snapshot(), provider_id)
    if existing is None:
        emit_provider_error(
            state,
            registry_path,
            "provider.not_found",
            f"no Provider has ID {provider_id!r}",
            exit_code=1,
        )

    record_name = name if name is not None else existing.name
    record_url = url if url is not None else existing.url
    if status == "active":
        if reason is not None or explanation is not None:
            emit_provider_error(
                state,
                registry_path,
                "provider.invalid_input",
                "active Providers cannot include --reason or --explanation",
                exit_code=2,
            )
        try:
            record = ActiveProvider(
                id=provider_id,
                name=record_name,
                url=record_url,
                status="active",
            )
        except ValidationError as error:
            emit_provider_error(
                state,
                registry_path,
                "provider.record_invalid",
                "Provider record is not a valid publication-safe active record",
                exit_code=2,
            )
            raise AssertionError("unreachable") from error
    else:
        if reason is None or explanation is None:
            emit_provider_error(
                state,
                registry_path,
                "provider.inactive_details_required",
                "inactive Providers require --reason and --explanation",
                exit_code=2,
            )
        try:
            record = InactiveProvider(
                id=provider_id,
                name=record_name,
                url=record_url,
                status="inactive",
                reason=reason,
                explanation=explanation,
            )
        except ValidationError as error:
            emit_provider_error(
                state,
                registry_path,
                "provider.record_invalid",
                "Provider record is not a valid publication-safe inactive record",
                exit_code=2,
            )
            raise AssertionError("unreachable") from error

    try:
        updated_snapshot = registry.put(record)
    except ProviderRecordInvalid as error:
        emit_provider_error(
            state,
            registry_path,
            "provider.record_invalid",
            str(error),
            exit_code=2,
        )
    except RegistryInvalid as error:
        emit_provider_error(
            state,
            registry_path,
            "provider.registry_write_failed",
            str(error),
            exit_code=1,
        )
    updated = next(
        candidate
        for candidate in updated_snapshot.providers
        if candidate.id == provider_id
    )
    emit_provider_record_change(state, updated)


def cli_state(context: typer.Context) -> CliState:
    state = context.find_root().obj["state"]
    if not isinstance(state, CliState):
        raise RuntimeError("CLI state was not initialized")
    return state


def provider_registry_path(workspace: Path) -> Path:
    return workspace / "config" / "provider-registry.jsonl"


def find_provider(
    snapshot: ProviderRegistrySnapshot,
    provider_id: ProviderId | None,
) -> ActiveProvider | InactiveProvider | None:
    if provider_id is None:
        return None
    return next(
        (candidate for candidate in snapshot.providers if candidate.id == provider_id),
        None,
    )


def open_provider_registry_or_exit(state: CliState, path: Path) -> ProviderRegistry:
    try:
        return ProviderRegistry.open(path)
    except RegistryInvalid as error:
        emit_provider_error(
            state,
            path,
            "provider.registry_invalid",
            str(error),
            exit_code=1,
        )
    raise AssertionError("unreachable")


def emit_provider_snapshot(
    state: CliState,
    snapshot: ProviderRegistrySnapshot,
) -> None:
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "kind": "provider-registry",
                    "records": [
                        provider.model_dump(mode="json")
                        for provider in snapshot.providers
                    ],
                    "catalogueDatasetChanged": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    lines = ["ID           STATUS    NAME         WEBSITE"]
    for provider in snapshot.providers:
        lines.append(
            f"{provider.id:<12} {provider.status:<9} {provider.name:<12} {provider.url}"
        )
        if isinstance(provider, InactiveProvider):
            lines.append(f"  reason: {provider.reason}")
            lines.append(f"  explanation: {provider.explanation}")
    typer.echo("\n".join(lines))


def emit_provider_record(
    state: CliState,
    provider: ActiveProvider | InactiveProvider,
) -> None:
    if state.json_output:
        emit_provider_json(provider)
        return
    typer.echo(f"ID: {provider.id}")
    typer.echo(f"Status: {provider.status}")
    typer.echo(f"Name: {provider.name}")
    typer.echo(f"Website: {provider.url}")
    if isinstance(provider, InactiveProvider):
        typer.echo(f"Reason: {provider.reason}")
        typer.echo(f"Explanation: {provider.explanation}")


def emit_provider_record_change(
    state: CliState,
    provider: ActiveProvider | InactiveProvider,
) -> None:
    if state.json_output:
        emit_provider_json(provider)
        return
    suffix = f" ({provider.reason})" if isinstance(provider, InactiveProvider) else ""
    typer.echo(f"Provider {provider.id} is now {provider.status}{suffix}.")
    typer.echo("Active Catalogue Dataset was not changed.")


def emit_provider_json(provider: ActiveProvider | InactiveProvider) -> None:
    typer.echo(
        json.dumps(
            {
                "kind": "provider",
                "record": provider.model_dump(mode="json"),
                "catalogueDatasetChanged": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def emit_provider_error(
    state: CliState,
    path: Path,
    code: str,
    message: str,
    *,
    exit_code: int,
) -> NoReturn:
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": {"code": code, "message": message},
                    "safeState": {
                        "providerRegistry": str(path),
                        "unchanged": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
    else:
        typer.echo(f"error [{code}]: {message}", err=True)
        typer.echo(
            f"safe state: Provider Registry at {path} is unchanged",
            err=True,
        )
    raise typer.Exit(code=exit_code)


site_app = typer.Typer(
    help="Build, inspect, and serve the workspace-bound Catalogue Site.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(site_app, name="site")


@site_app.command("build", help="Build the Site from the workspace's active Dataset.")
def site_build_command(context: typer.Context) -> None:
    state = cli_state(context)
    site = CatalogueSite(state.workspace)
    try:
        site.build()
    except SiteBuildError as error:
        typer.echo(f"error: {error}", err=True)
        typer.echo(
            f"safe state: completed Site at {error.safe_artifact or site.site_path} is unchanged",
            err=True,
        )
        raise typer.Exit(code=1) from error
    except (OSError, ValueError) as error:
        typer.echo(f"error: cannot build Site: {error}", err=True)
        raise typer.Exit(code=1) from error


@catalogue_app.command(
    "refresh",
    help="Refresh the complete covered-provider catalogue.",
)
def refresh_command(context: typer.Context) -> None:
    state = cli_state(context)
    if not state.workspace.exists() or not state.workspace.is_dir():
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            CatalogueRefreshError.invalid_input(
                "catalogue.workspace_invalid",
                "Catalogue Refresh requires an existing workspace directory.",
            ).failure,
        )
    try:
        ProviderRegistry.open(provider_registry_path(state.workspace))
        catalogue = Catalogue(
            state.workspace,
            adapters=production_provider_adapters(),
        )
        report = catalogue.refresh()
    except CatalogueRefreshError as error:
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            error.failure,
        )
    except RegistryInvalid as error:
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            CatalogueRefreshError.invalid_input(
                "catalogue.registry_invalid",
                f"The Provider Registry is invalid: {error}",
            ).failure,
        )
    except ValueError as error:
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            CatalogueRefreshError.invalid_input(
                "catalogue.refresh_precondition",
                str(error),
            ).failure,
        )
    except KeyboardInterrupt:
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            CatalogueRefreshError.interrupted().failure,
        )
    except Exception:
        emit_catalogue_error(
            state,
            state.workspace / "var" / "catalogue-dataset.json",
            CatalogueRefreshError.unexpected_defect().failure,
        )
    emit_refresh_report(state, report)


def catalogue_refresh_exit_code(category: RefreshFailureCategory) -> int:
    """Map refresh failure categories to the documented CLI statuses."""
    exit_codes: dict[RefreshFailureCategory, int] = {
        "operational": 1,
        "invalid-input": 2,
        "unexpected-defect": 3,
        "interruption": 130,
    }
    return exit_codes[category]


def emit_refresh_report(state: CliState, report: CatalogueRefreshReport) -> None:
    serialized = report.model_dump(mode="json", by_alias=True)
    if state.json_output:
        typer.echo(
            json.dumps(
                serialized,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    typer.echo(
        "\n".join(
            [
                "Catalogue Refresh",
                f"Generated at: {report.generated_at}",
                f"Providers: {', '.join(report.provider_ids)}",
                f"Catalogue Offers: {report.catalogue_offer_count}",
                f"Quarantined Candidates: {report.quarantined_candidate_count}",
                "Active Catalogue Dataset replaced atomically.",
            ]
        )
    )


@app.command("history-check", help="Check Git history for generated artifacts.")
def history_check_command(
    repository: Annotated[
        Path,
        typer.Option(help="Git checkout to inspect."),
    ] = Path("."),
) -> None:
    try:
        validate_repository_history(repository)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print("Repository history check passed.")


@app.command("legal-check", help="Check the consumer-credit release gate.")
def legal_check_command(
    repository: Annotated[
        Path,
        typer.Option(help="Git checkout to inspect."),
    ] = Path("."),
    legal_record: Annotated[
        Path,
        typer.Option(help="Legal release record JSON."),
    ] = DEFAULT_LEGAL_RECORD,
) -> None:
    try:
        legal_path = (
            legal_record
            if legal_record.is_absolute()
            else repository.resolve() / legal_record
        )
        legal_status = validate_legal_release(legal_path, repository)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(legal_status)


@site_app.command("serve", help="Serve the completed workspace Site.")
def site_serve_command(
    context: typer.Context,
    port: Annotated[
        int,
        typer.Option(min=1, max=65535, help="TCP port to serve."),
    ] = 4173,
) -> None:
    try:
        CatalogueSite(cli_state(context).workspace).serve(port)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot serve incomplete static artifact: {error}") from error


@site_app.command("inspect", help="Inspect the completed workspace Site.")
def site_inspect_command(context: typer.Context) -> None:
    state = cli_state(context)
    site = CatalogueSite(state.workspace)
    try:
        dataset = site.open()
    except (OSError, ValueError) as error:
        raise SystemExit(
            f"Cannot inspect incomplete static artifact: {error}"
        ) from error
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "kind": "catalogue-site",
                    "site": str(site.site_path),
                    "generatedAt": dataset.generated_at,
                    "catalogueOfferCount": len(dataset.offers),
                    "quarantinedCandidateCount": len(dataset.quarantined_candidates),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    typer.echo(f"Catalogue Site: {site.site_path}")
    typer.echo(f"Generated at: {dataset.generated_at}")
    typer.echo(f"Catalogue Offers: {len(dataset.offers)}")
    typer.echo(f"Quarantined Candidates: {len(dataset.quarantined_candidates)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
