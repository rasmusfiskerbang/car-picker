# Design 2: Explicit capability suite

## Intent

Maximize flexibility and independent composition. Provider state, Catalogue
refresh, offer behavior, publication, and completed-site operations each receive
their own external behavioral module.

## Interface

```python
class ProviderRegistry:
    @classmethod
    def open(cls, path: Path) -> Self: ...

    def snapshot(self) -> ProviderRegistrySnapshot: ...

    def put(
        self,
        record: ActiveProvider | InactiveProvider,
    ) -> ProviderRegistrySnapshot: ...


class Catalogue:
    def refresh(self) -> RefreshReport: ...

    def current(self) -> CatalogueDataset: ...


class OfferComparison:
    def compare(
        self,
        catalogue: CatalogueDataset,
        selection: OfferSelection,
    ) -> ComparisonReport: ...

    def inspect(
        self,
        catalogue: CatalogueDataset,
        offer: OfferIdentity | None = None,
    ) -> InspectionReport: ...


class Publication:
    def serialize(self, catalogue: CatalogueDataset) -> CataloguePublication: ...

    def build(
        self,
        catalogue: CatalogueDataset,
        destination: Path,
    ) -> CompletedSite: ...


class CompletedSite:
    @classmethod
    def open(cls, path: Path) -> Self: ...

    def verify_against(self, catalogue: CatalogueDataset) -> SiteVerification: ...

    def serve(self, address: ServeAddress) -> None: ...
```

Pydantic models such as `ProviderRegistrySnapshot`, `CatalogueDataset`,
`CatalogueOffer`, `CataloguePublication`, and the report types contain data only.
Regular classes own behavior.

A composition root wires repository paths and statically imported Provider
Adapters. It is configuration, not another behavioral module.

## Caller example

```python
modules = compose_repository(Path("."))

refresh = modules.catalogue.refresh()
catalogue = modules.catalogue.current()

inspection = modules.offer_comparison.inspect(catalogue)
site = modules.publication.build(catalogue, Path("var/site"))
verification = site.verify_against(catalogue)
site.serve(ServeAddress(host="0.0.0.0", port=4173))
```

Tests vary constructor dependencies but call the same interfaces:

```python
modules = compose(
    registry_path=tmp_path / "provider-registry.jsonl",
    dataset_path=tmp_path / "catalogue-dataset.json",
    provider_adapters=fixture_provider_adapters(),
    clock=FixedClock(...),
    frontend_compiler=FixtureFrontendCompiler(...),
)
```

## Invariants and ordering

### Provider Registry

- The registry is the sole provider authority.
- `put()` adds or replaces one current record and atomically rewrites valid JSONL.
- It exposes no delete, transition history, retrieval state, Designated Offer
  Source configuration, withdrawal workflow, or separate eligibility state.

### Catalogue

- `refresh()` snapshots the registry exactly once.
- Every active provider must have one statically composed Provider Adapter.
- Every active provider participates in the attempted refresh.
- The implementation consumes Catalogue Candidates during Catalogue Admission,
  derives Catalogue Coverage, and validates a complete Catalogue Dataset.
- Only a completely successful refresh atomically replaces the active dataset.
- `current()` returns one immutable generation or raises `NoActiveCatalogue`.

### Offer comparison

- All values derive from Catalogue Offer facts and Base Cash-flow Streams.
- Unknown inputs yield unavailable operations with blocking facts, not errors.
- Results never write back into the Catalogue Dataset.

### Publication and completed site

- `serialize()` is the one authoritative path to `CataloguePublication`.
- `build()` accepts one already-loaded Catalogue Dataset generation, preventing a
  mixed-generation build.
- A build validates `CataloguePublication`, compiles in staging, verifies the
  artifact, and atomically replaces the prior completed site.
- `CompletedSite.open()` validates the artifact before returning an instance.
- `verify_against()` detects a structurally valid but stale completed site.

## Error interface

```python
class RegistryInvalid(Exception): ...
class ProviderRecordInvalid(Exception): ...
class MissingProviderAdapter(Exception): ...
class ProviderRefreshFailed(Exception): ...
class NoActiveCatalogue(Exception): ...
class CatalogueInvalid(Exception): ...
class OfferNotFound(Exception): ...
class PublicationFailed(Exception): ...
class InvalidCompletedSite(Exception): ...
class CompletedSiteStale(Exception): ...
```

Malformed inputs fail Pydantic validation at their module interface. Comparison
unavailability remains a domain result rather than entering the error hierarchy.

## Hidden implementation

- JSONL parsing, stable ordering, record validation, and atomic registry writes.
- Registry-to-adapter reconciliation and all-provider orchestration.
- Retry policy, provider source traversal, retrieval, and parsing.
- Catalogue Admission, quarantine compaction, identity uniqueness, Catalogue
  Coverage, generation timing, dataset validation, and atomic replacement.
- Cash-flow reconstruction, readiness, reconciliation, filtering, and comparison.
- Danish public labels, omission rules, schema generation, frontend compilation,
  artifact allow-listing, staging, verification, and atomic site replacement.
- Safe local static serving.

## Dependencies and seams

- Domain calculations and validation are **in-process** and need no adapters.
- Registry, Catalogue Dataset, and completed-site storage are
  **local-substitutable** internal seams exercised through temporary paths.
- Provider websites are **true external** and sit behind `ProviderAdapter`.
- HTTP is a private seam inside each Provider Adapter.
- The frontend compiler is local-substitutable. A production compiler and a
  focused test stand-in may satisfy a private internal interface.
- There are no remote-but-owned dependencies.

The production Provider Adapter set is statically imported. There is no runtime
discovery, plugin directory, configuration-selected class, or dynamic import.

## Trade-offs

### Strengths

- Each module name predicts the behavior it owns.
- Callers can independently reuse refresh, comparison, serialization, and site
  operations.
- Changes have strong locality within their capability.
- Seam placement is explicit and easy to inspect.

### Weaknesses

- The CLI must coordinate several modules and preserve their ordering.
- Callers can accidentally combine a registry, dataset, and site from unrelated
  workspaces or generations unless extra types prevent it.
- The interface exposes types and composition choices the common owner workflow
  does not need.
- `Publication.serialize()` risks becoming an operator-facing projection step,
  contrary to the goal of one hidden publication workflow.
- Some classes may remain shallow unless their implementation absorbs more than
  validation and I/O.

## Verdict

This is the best design for library flexibility and explicit seams, but it makes
the owner CLI carry too much workflow knowledge. It is the upper bound on useful
composition, not the recommended owner-facing surface.
