# PROTOTYPE — Catalogue Dataset serialization contract

> Throwaway Wayfinder prototype for **Design the catalogue's public serialization contract**. This is a discussion artifact, not production documentation or an implementation specification.

## Question

Can one strict, publication-safe `CatalogueDataset` shape serve all three roles without growing a second model: the complete durable result of a Catalogue Refresh, the unchanged input packaged by `CatalogueSite`, and the browser's runtime-validated data contract?

The prototype makes the proposed answer concrete enough to attack with real cases. It is split across:

- [Contract shape](./01-contract-shape.md) — the proposed Pydantic v2 models, nesting, and cross-record invariants.
- [Pressure-test dataset](./02-pressure-test-dataset.md) — one illustrative generation containing two admitted Offers, an inactive provider, and a Quarantined Candidate.
- [Python-to-TypeScript seam](./03-python-to-typescript-seam.md) — schema generation, packaging, runtime validation, inferred types, and versioning.

To review all three files locally:

```sh
open docs/prototypes/catalogue-dataset-contract/README.md
```

## Upstream constraints retained

The following decisions already made by the rewrite map remain fixed in this prototype:

- `CatalogueDataset` is the only named catalogue model and only durable catalogue artifact.
- The browser consumes the Dataset unchanged; there is no publication model, presentation model, serializer, or projection workflow.
- Provider Registry records are wholly publication-safe and are copied into each Dataset generation.
- A Catalogue Offer keeps normalized facts but no per-fact evidence or source wording. Its canonical offer URL remains the place to verify current terms.
- A Quarantined Candidate is compact and is the only Dataset record that retains short supporting evidence.
- Retrieval metadata, full documents, hashes, parser versions, retry history, and diagnostics are transient and absent from the Dataset.

## Proposed answer at a glance

The top level has five fields only:

```text
CatalogueDataset
├── schemaVersion
├── generatedAt
├── providers
├── offers
└── quarantinedCandidates
```

`providers` is the dated copy of Provider Registry records. `offers` contains normalized source facts plus two validated flat totals calculated from each Base Cash-flow Stream. `quarantinedCandidates` contains identity, provider, canonical source, admission reasons, and the evidence for those reasons. Provider participation and counts are derived from these arrays; designated source scope remains in Provider Adapter code and source audits.

There is no backend Comparison model. The frontend selects Offers by identity from the parsed Dataset and renders their facts, `totalDkk`, and `totalDkkPerMonth` side by side; selection and presentation state do not enter the Dataset.

## Accepted in live review

- **Evidence boundary — 2 August 2026:** retain short public first-party excerpts only inside Quarantined Candidate reasons. Admitted Catalogue Offers carry normalized facts and their canonical offer URL, but no per-fact source wording, including on Service Arrangements. `CONTEXT.md` was aligned with this decision.
- **Money representation — 2 August 2026:** use ordinary JSON numbers/Python floats for DKK values. Small floating-point rounding errors are acceptable.
- **Vehicle Specification families — 2 August 2026:** every Offer embeds a discriminated Vehicle Specification. Common attributes are make, model, trim, model year, first-registration year, body style, and odometer reading. Either or both year facts may be available; they are not collapsed into an ambiguous generic year. The only supported kinds are combustion—gasoline or diesel—with fuel efficiency, and battery electric—with battery capacity, WLTP range, maximum charging power, and 10–80% charging time. Other drivetrains are outside scope.
- **EV measurement qualifiers — 2 August 2026:** a known battery-capacity value retains whether it is gross, usable, or unstated; a known maximum-charging-power value retains whether it is AC, DC, or unstated. Values remain available when the qualifier was not stated, but the ambiguity stays visible.
- **No Catalogue Coverage record — 2 August 2026:** the Dataset has no dedicated coverage section. Provider participation and counts are implied by Provider Registry records, Offers, and Quarantined Candidates; source-scope intent is read from Provider Adapter code or source audits when needed.
- **Python-to-TypeScript bridge — 2 August 2026:** keep Pydantic serialization-mode JSON Schema as the sole contract authority; generate a TypeScript schema constant and static type from it; convert the constant once with Zod 4 `fromJSONSchema()`; and connect the broad runtime `ZodType` to the generated type through one isolated, audited cast. Pin the Zod minor line and guard the bridge with schema-feature, runtime-parity, and TypeScript-negative tests. The supporting comparison is [CatalogueDataset Python-to-TypeScript contract toolchain research](../../research/catalogue-dataset-typescript-contract-toolchain.md).
- **Quarantine evidence size — 2 August 2026:** each supporting excerpt is an exact public first-party fragment of at most 500 characters. A reason may cite multiple excerpts when distinct fragments are genuinely necessary; full source documents remain transient.
- **Empty active-provider result — 2 August 2026:** a Provider Adapter may return zero Candidates only after recognizing and exhaustively enumerating a valid empty source. Missing expected structure, failed enumeration, or an ambiguous empty page is a structural failure that rejects the complete refresh. This distinction remains Adapter behavior and adds no Dataset field.
- **No Exposure Scenarios — 2 August 2026:** the v1 Catalogue Offer and product have no structured conditional-cost records, calculators, or presentation. Provider disclosure of an excess-mileage rate, damage charge, early-termination charge, or another conditional amount neither adds a Dataset field nor quarantines an otherwise admissible Offer. Conditional amounts are omitted rather than treated as zero. Exposure Scenarios may return in a later product effort.
- **Pydantic contract notation — 4 August 2026:** express the prototype's authoritative contract shape as illustrative Pydantic v2 models rather than handwritten TypeScript-like types. Prefer readable models over maximal type expressivity; relationships that would make the declarations disproportionately complex may use a broader field shape and remain strict through Pydantic validation. JSON remains the wire example, and TypeScript appears only on the generated browser-consumer side of the seam.
- **Leasing Form normalization — 4 August 2026:** an admitted Offer retains only the normalized `leasingForm` classification. The provider's source label is transient admission input, not a Provider Registry value or retained per-fact wording. The shorter name is sufficient because admission guarantees that every Catalogue Offer has a supported form.
- **No Registration-tax Treatment — 4 August 2026:** remove registration-tax treatment from v1. The product neither calculates nor filters by this contract detail, and advertised payments already enter the Base Cash-flow Stream; retaining it would add an unused Offer fact.
- **No backend Comparison — 4 August 2026:** remove the nested `comparison` record, comparison-specific availability reasons, and provider-total reconciliation. The backend publishes normalized Offers with flat calculated totals; the frontend selects them by identity and owns side-by-side presentation without persisting comparison state or creating a second Dataset model. This revises the earlier backend-interface decision while retaining the Dataset as the unchanged browser contract.
- **Flat Offer totals — 4 August 2026:** every Catalogue Offer retains `advertisedTotalDkk` as a provider-stated Fact and materializes backend-calculated `totalDkk` and `totalDkkPerMonth` directly on the Offer. Payments add and explicit receipts—including refunds—subtract. Both calculated fields are required but `null` when any required cash-flow amount is unavailable. The advertised and calculated totals are independent and are not reconciled.
- **Chronological cash-flow occurrences — 4 August 2026:** the Base Cash-flow Stream contains one event for every actual occurrence, ordered by `occursAtMonth`; it does not contain recurring or one-off schedule rules. Month `0` is the upfront bucket at or before handover, months `1` onward are contract-relative months, and `termMonths` is normal completion. Array order breaks ties within a month. This larger wire representation is accepted because the frontend can chart it directly and backend totals become a signed sum without schedule expansion.

Live review remains open. The decisions above are accepted individually but do not constitute acceptance of the complete prototype.

## Deliberately excluded from the prototype

- Pydantic implementation details beyond the public model shapes and required validators.
- Danish labels, formatting, route state, and page-specific view models; these remain frontend behavior.
- Provider Adapter candidate shapes, refresh reports, diagnostics, and source-document storage.
- Migration machinery for historical datasets. The system retains only one current Dataset and can rebuild it.
- Exact filter composition and responsive presentation, which belong to the four-page application prototype.
- Structured Exposure Scenarios and conditional-cost calculators, which belong to a later product effort.
- Backend Comparison models, comparison-specific readiness, and aggregate reconciliation; frontend selection and side-by-side presentation consume normalized Offers and their flat totals directly.

## Review scenarios

The proposed contract should make each statement obviously true:

- An active provider remains visible even when it contributes zero admitted Offers.
- An inactive provider remains visible in the Provider Registry copy but cannot own an Offer or Quarantined Candidate.
- A missing mileage allowance remains an explicit unavailable Offer fact and does not prevent the frontend from displaying that Offer beside another.
- An unavailable required cash-flow amount makes both flat calculated totals `null` rather than producing a partial total.
- A refundable deposit payment and explicit refund remain separate normalized events and offset each other in the backend-calculated `totalDkk`.
- Every Base Cash-flow Event is an individually timed occurrence, so the frontend can chart the ordered stream without expanding recurrence rules.
- A disclosed excess-mileage rate has no Dataset representation and does not quarantine an otherwise admissible Offer.
- The frontend can select Offers by identity and render their normalized facts and flat totals side by side without a comparison record or projection in the Dataset.
- A Quarantined Candidate can explain failed admission without retaining its full parsed commercial model.
- No handwritten TypeScript Dataset shape can drift from Python, and representative converter differences fail the build-time contract cases.
