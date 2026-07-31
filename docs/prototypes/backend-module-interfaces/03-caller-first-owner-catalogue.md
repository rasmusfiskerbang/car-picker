# Design 3: Caller-first Owner Catalogue

## Intent

Optimize for the owner CLI and workflow tests. One workspace-scoped behavioral
module fixes canonical paths and exposes only the complete operations the owner
performs.

## Interface

```python
class OwnerCatalogue:
    @classmethod
    def open(
        cls,
        root: Path,
        *,
        provider_adapters: Mapping[ProviderId, ProviderAdapter] | None = None,
    ) -> Self: ...

    def refresh(self) -> RefreshReport: ...

    def inspect(
        self,
        offer: OfferIdentity | None = None,
    ) -> InspectionReport: ...

    def publish(self) -> PublicationReport: ...

    def verify_completed_site(self) -> SiteVerification: ...

    def serve_completed_site(self, address: ServeAddress) -> None: ...
```

The root fixes canonical locations for the version-controlled Provider Registry,
active Catalogue Dataset, and completed site. Common callers cannot accidentally
combine artifacts from unrelated workspaces.

The optional Provider Adapter mapping is a construction seam for tests. Production
callers use the statically composed defaults.

## Caller example

```python
owner = OwnerCatalogue.open(Path("."))

refresh = owner.refresh()
inspection = owner.inspect()
publication = owner.publish()
verification = owner.verify_completed_site()
owner.serve_completed_site(ServeAddress(host="0.0.0.0", port=4173))
```

The CLI contains only argument parsing, rendering, and exit-code translation:

```python
@catalogue_app.command("refresh")
def refresh() -> None:
    render(OwnerCatalogue.open(Path(".")).refresh())


@catalogue_app.command("inspect")
def inspect(offer: OfferIdentity | None = None) -> None:
    render(OwnerCatalogue.open(Path(".")).inspect(offer))


@site_app.command("build")
def build() -> None:
    render(OwnerCatalogue.open(Path(".")).publish())
```

Workflow tests use the same behaviors with fixture Provider Adapters.

## Invariants and ordering

- `open()` validates the Provider Registry and Provider Adapter coverage without
  contacting providers.
- The Provider Registry alone determines stable provider identity and active or
  inactive state.
- Provider Adapters own Designated Offer Source mechanics but confer no authority
  to activate a provider.
- `refresh()` retrieves every active provider, admits transient Catalogue
  Candidates, constructs one Catalogue Dataset, validates it, and atomically
  replaces the active generation.
- Failed refreshes leave the prior Catalogue Dataset byte-for-byte unchanged.
- `inspect()` derives comparison values, readiness, and aggregate reconciliation
  from the active dataset without persisting them.
- `publish()` derives `CataloguePublication`, builds and verifies a staged site,
  and atomically replaces the completed site.
- `verify_completed_site()` checks both artifact integrity and agreement with the
  active Catalogue Dataset generation.
- A successful refresh makes an older completed site explicitly stale.
- Validation runs at the operation owning the risk; no catch-all validation
  behavior exists.

## Error interface

```python
class WorkspaceInvalid(Exception): ...
class ProviderAdapterMissing(Exception): ...
class NoActiveCatalogue(Exception): ...
class RefreshRejected(Exception): ...
class OfferNotFound(Exception): ...
class PublicationRejected(Exception): ...
class CompletedSiteInvalid(Exception): ...
class CompletedSiteStale(Exception): ...
```

`RefreshRejected` records the provider ID and failing stage but does not retain
full provider documents. `PublicationRejected` records the failing stage and
leaves the previous completed site intact.

## Hidden implementation

- Canonical workspace layout and safe path handling.
- Provider Registry parsing and discriminated-union validation.
- Active-provider selection and Provider Adapter coverage.
- Retry policy and all-provider refresh orchestration.
- Catalogue Admission and compact Quarantined Candidate creation.
- Catalogue Dataset validation and atomic replacement.
- Offer lookup, derived comparison values, readiness, and reconciliation.
- `CataloguePublication` derivation and schema generation.
- Frontend compilation, staged verification, atomic replacement, and current-
  generation checks.
- Error translation into owner-level operation errors.

These concerns may be organized into private domain modules. They do not become
public `CatalogueStore`, `ProjectionBuilder`, or `ArtifactVerifier` interfaces.

## Dependencies and seams

```python
class ProviderAdapter(Protocol):
    provider_id: ProviderId

    def collect(self) -> Sequence[CatalogueCandidate]: ...
```

- Provider websites are **true external** and justify production and fixture
  Provider Adapters.
- HTTP is a private seam inside each Provider Adapter.
- Domain validation, Catalogue Admission, offer behavior, and serialization are
  **in-process**.
- Filesystem, temporary directories, Git checkout, and the frontend toolchain are
  **local-substitutable** and tested through temporary workspaces.
- No storage or calculation ports appear in the external interface.

## Trade-offs

### Strengths

- The common workflow is concise and difficult to misuse.
- Canonical paths and ordering disappear from callers.
- CLI and workflow tests share one narrow interface.
- Transaction rules have strong locality.

### Weaknesses

- `OwnerCatalogue` owns provider state and completed-site behavior even though its
  name says Catalogue.
- It encourages a god module whose interface may grow with every owner operation.
- Provider Registry operations do not fit naturally.
- The CLI may group operations by domain noun while delegating every group to one
  ambiguously named facade.
- Reusing one capability independently requires reaching into private modules or
  expanding the facade.

## Verdict

This design has the best default caller experience, but its name and ownership do
not remain coherent as Provider Registry and site behavior grow. It provides the
workflow simplicity to preserve in a more honestly named module structure.
