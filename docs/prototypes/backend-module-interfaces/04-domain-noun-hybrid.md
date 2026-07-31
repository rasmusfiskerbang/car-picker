# Design 4: Domain-noun hybrid with one Catalogue Dataset

## Intent

Combine the caller-first workflow with domain-oriented ownership. Expose three
owner-facing behavioral modules—`ProviderRegistry`, `Catalogue`, and
`CatalogueSite`—and one Pydantic catalogue model, `CatalogueDataset`.

The Catalogue Dataset is both the durable active generation and the exact data
contract consumed by the static frontend. There is no `CataloguePublication`,
presentation model, projection workflow, or catalogue serializer.

This is the current recommendation.

## Interface

### Provider Registry

```python
class ProviderRegistry:
    @classmethod
    def open(cls, path: Path) -> Self: ...

    def snapshot(self) -> ProviderRegistrySnapshot: ...

    def put(
        self,
        record: ActiveProvider | InactiveProvider,
    ) -> ProviderRegistrySnapshot: ...
```

`ProviderRegistrySnapshot`, `ActiveProvider`, and `InactiveProvider` are Pydantic
data models. `ProviderRegistry` is a regular behavioral class that hides JSONL,
validation, stable ordering, and atomic replacement.

### Catalogue

```python
class Catalogue:
    @classmethod
    def open(
        cls,
        workspace: CatalogueWorkspace,
        *,
        provider_adapters: Mapping[ProviderId, ProviderAdapter] | None = None,
    ) -> Self: ...

    def refresh(self) -> RefreshReport: ...

    def current(self) -> CatalogueDataset: ...

    def inspect(
        self,
        offer: OfferIdentity | None = None,
    ) -> InspectionReport: ...
```

`CatalogueWorkspace` fixes the Provider Registry and active Catalogue Dataset
locations as one validated input. Callers cannot pass active provider IDs, source
URLs, candidate stores, or an output dataset separately.

`CatalogueDataset`, `CatalogueOffer`, `QuarantinedCandidate`, `RefreshReport`, and
`InspectionReport` are Pydantic data models. They do not retrieve providers,
write files, or build sites.

The Catalogue Dataset is deliberately browser-complete. At a high level it holds:

- the generation timestamp and schema version;
- a publication-safe snapshot of the Provider Registry at that generation;
- Catalogue Coverage;
- Catalogue Offers with normalized source facts and validated materialized
  comparison values, operation readiness, and aggregate reconciliation; and
- compact, publication-safe Quarantined Candidates.

[Design the catalogue's public serialization contract](https://github.com/rasmusfiskerbang/car-picker/issues/52)
will decide the exact fields, nesting, versioning, and quarantine representation.

### Provider Adapter and Catalogue Admission

The Provider Adapter seam ends at normalized domain data. An adapter hides its
provider-specific retrieval, enumeration, parsing, and evidence extraction, then
returns evidence-rich Catalogue Candidates:

```python
class ProviderAdapter(Protocol):
    provider_id: ProviderId

    def collect(self) -> tuple[CatalogueCandidate, ...]: ...
```

`Catalogue.refresh()` owns the provider-independent admission workflow:

```text
ProviderAdapter.collect()
        ↓
CatalogueCandidate
  transient, normalized, evidence-rich
        ↓
Catalogue Admission
        ├─ admitted ────→ CatalogueOffer
        └─ rejected ────→ QuarantinedCandidate
                                  ↓
                     materialize derived values
                                  ↓
                         CatalogueDataset
```

A Catalogue Candidate carries the stable Offer Identity and Provider ID,
canonical source, normalized admission and comparison facts, Base Cash-flow
Stream, explicit unavailable fact states, and the evidence needed to decide and
explain admission. It never enters the Catalogue Dataset.

Admission combines the active Provider Registry snapshot with the Candidate's
normalized facts and evidence. An admitted Candidate becomes a Catalogue Offer
without per-fact evidence. A rejected Candidate becomes a compact Quarantined
Candidate containing only identity, provider, canonical source, structured
reasons, and supporting evidence. No separate admission result is persisted.

A provider retrieval, enumeration, or structural mapping failure rejects the
complete refresh. Insufficient or conflicting evidence for one otherwise
identifiable Candidate is a domain outcome and quarantines only that Candidate.

Catalogue Admission may be organized as a private module inside `Catalogue`, but
it is not a public workflow, CLI command, or independently persisted artifact.

### Catalogue Site

```python
class CatalogueSite:
    @classmethod
    def build(
        cls,
        catalogue: CatalogueDataset,
        destination: Path,
    ) -> Self: ...

    @classmethod
    def open(cls, path: Path) -> Self: ...

    def serve(self, address: ServeAddress) -> None: ...
```

`CatalogueSite.build()` serializes the supplied Catalogue Dataset directly using
its Pydantic serialization schema. It does not select, rename, omit, enrich, or
recalculate catalogue fields. It packages that JSON, the schema derived from the
same model, and the frontend into one verified static artifact. `open()` rejects
an incomplete or corrupt artifact; it does not compare the artifact with the
currently active Catalogue Dataset.

## Caller example

```python
registry = ProviderRegistry.open(Path("config/provider-registry.jsonl"))
catalogue = Catalogue.open(CatalogueWorkspace.at(Path(".")))

refresh = catalogue.refresh()
inspection = catalogue.inspect()

snapshot = catalogue.current()
site = CatalogueSite.build(snapshot, Path("var/site"))
site.serve(ServeAddress(host="0.0.0.0", port=4173))
```

The later CLI can group commands by the same nouns:

```text
car-picker provider ...
car-picker catalogue refresh
car-picker catalogue inspect [OFFER]
car-picker site build
car-picker site serve
```

The CLI owns only option parsing, selection of the domain noun, report rendering,
and exit-code translation. Validation remains at the module seam owning each
risk.

## Invariants and ordering

### Provider Registry

- The Provider Registry is the sole provider authority.
- Each provider has one stable provider ID and one current `active` or `inactive`
  record.
- `put()` validates and atomically replaces the complete JSONL representation.
- The registry contains no Designated Offer Source mechanics, retrieval state,
  evidence, credentials, transition history, or special withdrawal workflow.
- A Catalogue Dataset contains a dated snapshot of publication-safe provider
  records. That snapshot describes its generation; it does not become a second
  provider authority.

### Catalogue refresh

- `Catalogue.open()` validates workspace layout, the Provider Registry, and fixed
  Provider Adapter coverage without contacting providers.
- Every active provider must have exactly one Provider Adapter.
- Inactive provider adapters may exist but are never called.
- One refresh collects every active provider in registry order.
- Provider Adapters own their bounded Designated Offer Source scope and preserve
  deterministic source-local ordering.
- Catalogue Candidates exist only inside one refresh.
- Catalogue Admission produces Catalogue Offers or compact Quarantined Candidates.
- The generation time is assigned only after provider collection succeeds.
- Comparison values, operation readiness, and aggregate reconciliation are
  calculated after admission and materialized into the candidate replacement.
- Dataset validation recalculates every materialized result from its normalized
  inputs and rejects any mismatch.
- One complete Catalogue Dataset is validated before atomic replacement.
- Any failure leaves the previous active Catalogue Dataset byte-for-byte intact.
- `RefreshReport` is transient and contains counts and diagnostics, not provider
  documents or a durable run manifest.
- Every retained field is safe to expose to the browser. Private operational
  diagnostics remain transient and cannot enter the Catalogue Dataset.

### Offer behavior

- Base Cash-flow Streams and normalized offer facts remain the semantic inputs to
  comparison behavior.
- Materialized derived values are validated results in the same generation, not
  an independently editable authority or cache with a separate lifecycle.
- Unavailable calculations retain their blocking facts as ordinary domain data.
- `Catalogue.inspect()` reads one immutable generation and may derive transient,
  owner-oriented diagnostics, but it does not create another catalogue model.
- The frontend reads materialized values and does not reimplement financial or
  readiness calculations in TypeScript.

### Catalogue Site

- `CatalogueSite.build()` accepts one immutable Catalogue Dataset generation.
- It writes the same Catalogue Dataset shape and its serialization-mode JSON
  Schema into staging without a catalogue transformation step.
- Danish UI labels and display formatting belong to the frontend; the dataset
  carries stable domain values rather than presentation copy.
- The Catalogue Site is built and verified in staging, then atomically replaces
  its predecessor.
- `CatalogueSite.open()` returns only a structurally valid artifact.
- A Catalogue Site containing an older generation remains a valid, dated
  artifact. The visible generation timestamp communicates its age.
- No public operation compares a built site with the active Catalogue Dataset;
  staleness is not corruption.
- `serve()` validates before binding and exposes static files only.

## Error interface

Errors are owned by the module that can explain and recover from them:

```python
# Provider Registry
class RegistryInvalid(Exception): ...
class ProviderRecordInvalid(Exception): ...

# Catalogue
class CatalogueWorkspaceInvalid(Exception): ...
class ProviderAdapterMissing(Exception): ...
class ProviderCollectionFailed(Exception): ...
class CatalogueReplacementRejected(Exception): ...
class NoActiveCatalogue(Exception): ...
class OfferNotFound(Exception): ...

# Catalogue Site
class SiteCompletionFailed(Exception): ...
class CatalogueSiteInvalid(Exception): ...
class SiteServeFailed(Exception): ...
```

Malformed data and inconsistent materialized results fail Pydantic validation at
the relevant edge. Unknown offer facts and blocked comparisons are valid domain
states rather than errors.

## Hidden implementation

### `ProviderRegistry`

- JSONL parsing and serialization.
- Stable record ordering.
- Discriminated-union validation.
- Duplicate provider-ID rejection.
- Atomic whole-file replacement.

### `Catalogue`

- Registry-to-adapter reconciliation.
- Bounded retry and backoff.
- All-provider orchestration.
- Catalogue Candidate collection and Catalogue Admission.
- Quarantine compaction and Catalogue Coverage derivation.
- Publication-safe Provider Registry snapshotting.
- Offer identity uniqueness.
- Comparison, readiness, and reconciliation materialization.
- Consistency validation for normalized inputs and materialized results.
- Generation timing and atomic dataset replacement.
- Offer lookup and transient owner diagnostics.

### `CatalogueSite`

- Catalogue Dataset serialization and schema generation from the same Pydantic
  model.
- Frontend compilation.
- Artifact manifest and generated-content checks.
- Staging, verification, atomic replacement, and safe serving.

Private implementation may use nested packages and explicit `__all__` exports,
but callers do not reach through the public package interfaces.

## Dependencies and seams

### Real external seam: Provider Adapter

```python
class ProviderAdapter(Protocol):
    provider_id: ProviderId

    def collect(self) -> Sequence[CatalogueCandidate]: ...
```

- `FleasingProviderAdapter` and `TerminalenProviderAdapter` are production
  adapters.
- Fixture Provider Adapters exercise Catalogue behavior through the same seam.
- Each adapter owns its Designated Offer Source URLs and supporting-source rules.
- Provider activation remains exclusively in the Provider Registry.

Each Provider Adapter may contain a private HTTP seam with production network and
fixture-response adapters. It does not leak HTTP into `Catalogue`.

### Internal dependencies

- Catalogue Admission, validation, comparison, readiness, reconciliation, and
  Pydantic serialization are **in-process**. No adapters are introduced.
- Provider Registry JSONL, Catalogue Dataset storage, staging filesystems, and
  Catalogue Site replacement are **local-substitutable**. Behavioral tests use
  temporary workspaces rather than public storage ports.
- Time, retry waiting, frontend compilation, and static serving may use private
  internal seams where deterministic tests or two real adapters justify them.
- There are no remote-but-owned dependencies.

The production Provider Adapter mapping is statically imported and composed in
code. There is no runtime plugin system, adapter class in configuration, dynamic
import, or provider-selected implementation.

## Test surface

- Provider Registry tests call `open()`, `snapshot()`, and `put()` against
  temporary JSONL files.
- Catalogue workflow tests call `refresh()`, `current()`, and `inspect()` with
  fixture Provider Adapters and a temporary workspace.
- Catalogue Dataset tests validate its one storage-and-browser schema, including
  recalculation of every materialized comparison result.
- Provider-specific tests use the lower Provider Adapter seam with minimized
  first-party source fixtures.
- Catalogue Site tests call `build()` and `open()` and prove that the browser
  receives the unchanged Catalogue Dataset shape and incomplete artifacts are
  rejected.
- CLI tests remain useful only for argument parsing, report rendering, and exit
  codes; they do not duplicate deep-module behavior tests.

## Trade-offs

### Strengths

- There is one named catalogue model, one schema, and one serialized shape.
- Python and TypeScript cannot drift through a hand-written transformation.
- The frontend does not duplicate financial or readiness calculations.
- Module names match the domain nouns the owner and CLI use.
- The common workflow remains concise without a generic facade or command bus.
- Data and behavior follow `CODING_STANDARDS.md`.
- Each transaction and error belongs to the module with enough context to own it.
- The Provider Adapter is the only necessary lower public seam.
- The later CLI structure can mirror the module vocabulary.

### Weaknesses

- The Catalogue Dataset is wider because it serves both owner and browser needs.
- Every retained field, including quarantine information, becomes publicly
  accessible even when the frontend does not render it.
- Materialized derived values duplicate normalized inputs inside one artifact;
  strict consistency validation is required to prevent contradiction.
- A provider-state or calculation change becomes visible only through a new
  complete Catalogue refresh.
- Site building requires the caller to take a stable Catalogue Dataset snapshot
  and pass it to `CatalogueSite.build()`.
- `ProviderRegistry.put()` may be shallow until provider-editing behavior grows;
  its main depth is validated atomic JSONL replacement.

## Ticket boundary

This design settles the module-level decisions for
[Design the core backend module interfaces](https://github.com/rasmusfiskerbang/car-picker/issues/51):

- `ProviderRegistry`, `Catalogue`, and `CatalogueSite` are the owner-facing deep
  modules.
- `CatalogueDataset` is the sole durable catalogue artifact and the exact browser
  data contract.
- Derived comparison values and readiness are materialized during refresh and
  validated against their normalized inputs.
- Provider Adapters are the real lower seam.

[Design the catalogue's public serialization contract](https://github.com/rasmusfiskerbang/car-picker/issues/52)
should decide:

- exact Catalogue Dataset fields and nesting;
- schema-version evolution;
- how full Provider Registry records are snapshotted;
- which normalized facts and materialized results each Catalogue Offer contains;
- the compact Quarantined Candidate representation and what evidence is safe to
  expose; and
- how Python's serialization-mode JSON Schema becomes the TypeScript runtime
  validator and inferred types.

CLI command names and whether site build implicitly loads the current generation
belong to
[Prototype the owner CLI interface](https://github.com/rasmusfiskerbang/car-picker/issues/53).
Package and file locations belong to
[Choose the clean-room repository layout](https://github.com/rasmusfiskerbang/car-picker/issues/55).

## Verdict

This design best balances depth, locality, honest naming, and caller simplicity.
The single expanded Catalogue Dataset removes an entire transformation seam and
makes the browser contract identical to the durable, validated generation.
