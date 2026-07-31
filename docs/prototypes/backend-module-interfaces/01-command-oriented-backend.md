# Design 1: Command-oriented backend

## Intent

Maximize depth at the external seam. The CLI and behavioral tests learn one
behavioral module and one method. Complete owner intents are values passed into
that method; provider state, Catalogue refresh, offer behavior, publication, and
completed-site operations remain private implementation concerns.

## Interface

```python
class CarPickerBackend:
    def __init__(
        self,
        workspace: Workspace,
        provider_adapters: Mapping[ProviderId, ProviderAdapter],
    ) -> None: ...

    def run(self, operation: Operation) -> Outcome: ...


Operation = (
    RefreshCatalogue
    | InspectCatalogue
    | CompleteSite
    | VerifyCompletedSite
    | ServeCompletedSite
)

Outcome = (
    RefreshReport
    | InspectionReport
    | CompletedSite
    | SiteVerification
    | None
)
```

The operations describe owner outcomes rather than workflow steps:

```python
class RefreshCatalogue(BaseModel):
    pass


class InspectCatalogue(BaseModel):
    offer_identity: OfferIdentity | None = None


class CompleteSite(BaseModel):
    destination: Path


class VerifyCompletedSite(BaseModel):
    site: Path


class ServeCompletedSite(BaseModel):
    site: Path
    host: str = "0.0.0.0"
    port: int = 4173
```

An operation never represents an internal step such as `FetchProvider`,
`AdmitCandidate`, `SerializeCatalogue`, or `VerifyStagingDirectory`. Adding such
operations would turn a cosmetically narrow command bus into a shallow module.

## Caller example

The production CLI constructs one backend and translates outcomes to text:

```python
backend = CarPickerBackend(
    workspace=Workspace.open(Path(".")),
    provider_adapters=production_provider_adapters(),
)

report = backend.run(RefreshCatalogue())
backend.run(CompleteSite(destination=Path("var/site")))
verification = backend.run(VerifyCompletedSite(site=Path("var/site")))
```

Behavioral tests call the same seam with fixture-backed Provider Adapters:

```python
backend = CarPickerBackend(
    workspace=Workspace.open(tmp_path),
    provider_adapters={
        ProviderId("fleasing"): FixtureProviderAdapter(...),
        ProviderId("terminalen"): FixtureProviderAdapter(...),
    },
)

report = backend.run(RefreshCatalogue())
inspection = backend.run(InspectCatalogue())

assert report.catalogue_offer_count == 12
assert inspection.offers[0].nominal_base_outlay.value_dkk == 123_456
```

## Invariants and ordering

- `CarPickerBackend` reads and validates the Provider Registry. Callers never
  supply active provider IDs, source URLs, or retrieval state.
- Every active Provider Registry record must have exactly one Provider Adapter.
  Inactive providers are never collected.
- A refresh collects every active provider in Provider Registry order and
  preserves each adapter's Designated Offer Source order.
- Catalogue Candidates cannot escape in an `Outcome` or be persisted.
- The generation time is assigned after every Provider Adapter succeeds.
- The complete Catalogue Dataset is validated before atomic replacement.
- Any retrieval, mapping, admission, validation, or storage failure leaves the
  prior active Catalogue Dataset byte-for-byte unchanged.
- Inspection derives comparison values, operation readiness, and aggregate
  reconciliation from one immutable Catalogue Dataset generation.
- Site completion derives and validates `CataloguePublication`, builds in
  staging, verifies the completed artifact, and only then replaces the prior
  site.
- Site verification rejects an artifact whose `CataloguePublication` generation
  does not match the active Catalogue Dataset.
- Legal and source-access checks run inside the operation owning their risk.
  There is no generic validation operation.

## Error interface

```python
class BackendError(Exception): ...


class RegistryInvalid(BackendError): ...


class ProviderAdapterMissing(BackendError):
    provider_id: ProviderId


class ProviderCollectionFailed(BackendError):
    provider_id: ProviderId
    phase: Literal["retrieve", "enumerate", "map"]


class ActiveCatalogueMissing(BackendError): ...
class ActiveCatalogueInvalid(BackendError): ...


class OfferNotFound(BackendError):
    offer_identity: OfferIdentity


class SiteCompletionFailed(BackendError): ...
class CompletedSiteInvalid(BackendError): ...
```

The CLI translates these errors to messages and exit codes. It does not catch
arbitrary implementation exceptions or repeat validation.

## Hidden implementation

The implementation privately composes domain-oriented modules:

- Provider Registry parsing, validation, record updates, and adapter coverage.
- All-provider retrieval, bounded retries, Catalogue Admission, quarantine
  compaction, Catalogue Coverage, validation, and atomic replacement.
- Offer lookup, comparison calculations, operation readiness, and aggregate
  reconciliation.
- `CataloguePublication` derivation, schema generation, frontend compilation,
  completed-site verification, atomic replacement, and safe local serving.

Deleting `CarPickerBackend` would force each CLI operation and workflow test to
reconstruct this orchestration, so the module earns substantial depth.

## Dependencies and seams

- Catalogue Admission, validation, comparison calculations, reconciliation, and
  serialization are **in-process** dependencies. They remain behind the module.
- Provider Registry JSONL, the Catalogue Dataset, staging directories, and site
  replacement are **local-substitutable**. Tests use temporary filesystems; no
  storage ports are exposed.
- Provider websites are **true external**. `ProviderAdapter.collect()` is a real
  lower seam with production and fixture adapters.
- HTTP transport is a private seam inside each Provider Adapter, with network and
  fixture-response adapters.
- Time and retry scheduling are private internal seams used for deterministic
  tests.

## Trade-offs

### Strengths

- Maximum leverage for the CLI and behavioral tests.
- Almost no caller choreography or invalid ordering.
- Refresh and publication transaction rules have excellent locality.
- Only genuinely variable dependencies remain seams.

### Weaknesses

- `run(Operation) -> Outcome` obscures the domain behind generic dispatch.
- The operation and outcome unions are the real interface size; one method only
  makes that size less visible.
- Return narrowing and discoverability are worse than named methods.
- The design conflicts with the repository preference for domain-oriented
  classes and methods.
- Direct library-style composition is awkward.

## Verdict

This design is deepest at the caller seam but compresses too much meaning into a
generic command bus. It is useful as the lower bound on caller complexity, not
the recommended interface.
