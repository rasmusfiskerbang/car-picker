# Backend module interface prototypes

These throwaway design documents compare four external interface shapes for the
clean-room rewrite. They answer the question in
[Design the core backend module interfaces](https://github.com/rasmusfiskerbang/car-picker/issues/51):
which small set of deep behavioral modules should own provider state, Catalogue
refresh and offer behavior, publication, and Catalogue Site operations?

The first three designs preserve these constraints:

- The Provider Registry is the sole provider authority.
- One successful all-provider Catalogue refresh atomically replaces the complete
  active Catalogue Dataset.
- Catalogue Candidates and refresh diagnostics are transient.
- Comparison values and operation readiness are derived rather than persisted.
- `CataloguePublication` is the sole generated browser-facing serialization
  contract; the Catalogue Dataset remains the durable authority.
- The CLI and behavioral tests call the same external interfaces.
- Provider websites are true-external dependencies behind real Provider Adapter
  seams; local storage and pure calculations do not become public ports.
- Pydantic models hold data and regular classes own behavior.

## Designs

1. [Command-oriented backend](./01-command-oriented-backend.md) — one generic
   method receiving complete owner intents.
2. [Explicit capability suite](./02-explicit-capability-suite.md) — independently
   composable modules for each capability.
3. [Caller-first Owner Catalogue](./03-caller-first-owner-catalogue.md) — one
   workspace-scoped facade for the common owner workflow.
4. [Domain-noun hybrid](./04-domain-noun-hybrid.md) — three owner-facing domain
   nouns and one Catalogue Dataset used directly by the browser. This is the
   current recommendation.

Design 4 incorporates the human review of the alternatives. It deliberately
reopens two starting constraints: comparison results become validated materialized
values in the Catalogue Dataset, and the separate publication contract disappears.

These are discussion artifacts, not implementation specifications. Nothing here
is intended to cross automatically into the clean-room rewrite.
