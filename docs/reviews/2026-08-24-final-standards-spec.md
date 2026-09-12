# Issue #87 — final Standards + Spec review evidence

Review date: 2026-08-24; owner amendment: 2026-08-25; correction: 2026-08-28
Candidate baseline: `5a2ed41697e94006df5387e6a2ebbd0742bd5ffe` (accepted #86)
Scope: the clean-room replacement in this checkout
Review axes: `CODING_STANDARDS.MD` and the complete #67 body

This is the durable evidence for the one central GPT-5.6 Sol review and its
single correction pass. It is not a reviewer subthread, does not close #87,
and does not claim that repository cutover or deployment has happened.

## Review disposition

The correction pass fixes the authoritative-boundary, generator, historical
evidence, viewport, rollback, CLI-scope, and amended chart findings. The
2026-08-25 owner amendment recorded on #67 and #87 replaces the unavailable
prior chart dependency requirement with TanStack Charts. The shared cash-flow
seam now uses the official `@tanstack/charts@0.16.0` package through
`@tanstack/charts/react`; the locked dependency, typecheck, module, build, and
1440 × 900 / 390 × 844 browser checks are recorded below. The live owner gate is
the accepted record in [#86's acceptance record](../acceptance/2026-08-24-live-owner-acceptance.md);
the post-20 November 2026 legal gate and the repository merge/cutover actions
remain conditional gates owned by the release orchestrator.

The chart amendment is implemented at the existing shared seam without a
second runtime or a new public data authority. TanStack owns the SVG visual
surface, scales, marks, focus, and native tooltip; the existing HTML table and
accessible event list remain the exact-value semantic source. This record does
not claim repository cutover or deployment; #87 remains open for the
orchestrator's read-only verification and issue closure.

| Finding | Why it was in scope | Disposition and durable proof |
| --- | --- | --- |
| Backend `ComparisonModel` and `calculate_catalogue_offer_comparison` remained public | #67 deliberately excludes a backend Comparison/readiness model; comparison is a Catalogue Site concern | Removed `car_picker/comparison.py`, its tests, and package exports. `tests/test_clean_room_cutover.py` guards the absent public surface. The frontend `comparison-page.tsx` remains the accepted browser page. |
| A provider-withdrawal operating procedure remained in the replacement | #67 deliberately excludes a special withdrawal workflow; inactive `blocked` is the complete Registry state | Removed `docs/operations/provider-withdrawal.md` and the old Python workflow was already absent. The owner guide documents only ordinary complete Registry replacement and refresh. The clean-room test guards the removed path. |
| `CatalogueSite` exposed `dataset_path` and `output_path` overrides | #67 binds Site artifacts to workspace conventions and keeps filesystem substitutions private | `CatalogueSite` now accepts only `workspace` and always binds `var/catalogue-dataset.json` and `var/site`. Fixture tests use temporary conventional workspaces; the clean-room test guards the public signature. |
| A second source-access ledger was introduced beside the Provider Registry | #67 names the Registry as the sole identity and participation authority; source decisions belong in audits and ADRs | Removed the ledger module, its JSON file, package exports, CLI checks, roster type, tests, fixtures, and stale acceptance references. Active/inactive Registry state and the two static adapters remain the only participation path. |
| Publication contract generation had an optional-schema hook and facade forwarding layer | #67 requires one Site-owned Python schema authority | `generate_catalogue_contract_sources()` is now one direct implementation with no schema injection. It is not exported from the package facade; the frontend build script imports the narrow Site module seam. |
| The shared cash-flow visual had to use the amended approved chart package | The 2026-08-25 owner amendment replaces the unavailable prior chart dependency while preserving the #67 shared DKK/chronology/accessibility contract | `frontend/src/catalogue-cash-flow.tsx` uses `defineChart`/`barY` with `@tanstack/charts@0.16.0` and `@tanstack/charts/react`; the semantic table/list, deterministic legend, unavailable note, native tooltip, keyboard focus, and responsive browser assertions remain in place. |
| Historical acceptance records were not explicitly bounded | Clean-room construction allows evidence to cross, not historical implementation/configuration or obsolete behavior | All four July records now state their historical-only disposition; the clean-room test verifies their explicit entries in this record and the absence of the removed surfaces. |
| Rollback evidence checked tag existence but not prior-main identity | #67 rule 71 requires the prior main revision | `pre-cutover-issue-85` now resolves exactly to `main` at `79deb767ece2aaa6ffe33d512fa5e0b1521471bb`; the owner guide and correction test verify equality. |

## Standards axis

| Standard | Evidence | Disposition |
| --- | --- | --- |
| Deep modules with narrow interfaces | `ProviderRegistry`, `Catalogue`, and `CatalogueSite` are the owner-facing public modules. `ProviderAdapter` is the only source-specific lower seam. | Pass. The removed backend comparison module was an accidental shallow/extra authority. |
| Distinct abstraction levels and inward dependencies | CLI composition imports the package facade; Catalogue owns refresh/admission; adapters own source mechanics; Site owns contract generation/build/serve; frontend consumers use the Dataset module. | Pass. `tests/test_clean_room_cutover.py` checks the public import seams. |
| Boundary validation and explicit domain states | Pydantic strict models validate Registry, Candidate, Dataset, Site, and CLI report boundaries. Zod validates the generated browser contract. `UnavailableState` is explicit rather than nullable ambiguity. | Pass. Contract, refresh-failure, Site, and browser contract tests cover invalid boundaries. |
| No unchecked escape hatch without a boundary reason | Dynamic JSON is confined to source ingress, JSON persistence, and CLI/report boundaries; strict models take over before publication. No new `Any`/cast boundary was introduced by this review. | Pass. Existing casts are at untrusted or fixture boundaries and are covered by `ty`. |
| Python public package interfaces | `car_picker.__init__` exports the domain types and lifecycle operations; callers do not need private implementation modules. | Pass. The removed comparison exports and Site path overrides are no longer public. |
| React single source of truth | Dataset is loaded once through TanStack Query, selection and durable page filters live in validated hash URLs, and page values derive from Dataset state. | Pass. `frontend/e2e/offer-selection.spec.ts`, `catalogue-search.spec.ts`, and Dataset module tests cover the observable state. |
| Effects and memoization carry a burden of proof | Effects remain limited to URL canonicalization and layout synchronization. The chart definition uses one `useMemo` because TanStack treats definition identity as its update boundary; no new effect was added. | Pass. The memoization captures the complete chart definition inputs, and focused/full browser coverage exercises updates and focus. |
| Accessible, behavioral/presentational separation | Route adapters own routing/search/lookup; page and shared display modules receive domain data and callbacks. TanStack owns the visual SVG/focus/tooltip surface while the HTML table and event list carry exact values and unavailable states. | Pass. Browser tests exercise the named SVG, DKK axis, legend, native tooltip, keyboard focus, semantic tables, and contained comparison scroll. |

## #67 Spec axis — user-story trace

The numbers below are the 73 numbered User Stories in #67. Each row records
the implementation seam or acceptance evidence that proves the requirement;
the row is not a new product requirement.

| #67 | Requirement traced | Evidence / disposition |
| ---: | --- | --- |
| 1 | Clean-room construction | `tests/test_clean_room_cutover.py`; superseded backend surfaces removed. Pass. |
| 2 | Normative domain glossary | `CONTEXT.md`; public names use Catalogue/Provider/Offer vocabulary. Pass. |
| 3 | Registry as Provider authority | `provider_registry.py`, Dataset provider copy, Registry tests. Pass. |
| 4 | Stable explicit Provider ID | Strict Registry `id`; source audits and renamed-display-name refresh test. Pass. |
| 5 | Publication-safe Provider fields | Strict active/inactive Registry union rejects extra/private fields. Pass. |
| 6 | Complete active/inactive record | `ProviderRegistry.put` and `provider set`; atomic Registry tests. Pass. |
| 7 | Inactive reason and explanation | `InactiveProvider` requires the three reasons and explanation. Pass. |
| 8 | Atomic Provider changes | JSONL replacement and byte-preserving failure tests. Pass. |
| 9 | Blocking does not mutate the dated Dataset | CLI Registry mutation reports and tests preserve Dataset/Site bytes. Pass. |
| 10 | Static Adapter for each active Provider | Static `production_provider_adapters` plus pre-network coverage validation. Pass. |
| 11 | Exhaustive bounded source enumeration | Fleasing and Terminalen Adapter fixture suites enumerate and reject structural gaps. Pass. |
| 12 | Fleasing and Terminalen initial scope | Version-controlled Registry, source audits, and production composition tests. Pass. |
| 13 | All active Providers in Registry order | `Catalogue.refresh` and ordered fixture workflow test. Pass. |
| 14 | Candidates remain transient | Admission consumes Candidates; Dataset serialization tests exclude admission/source metadata. Pass. |
| 15 | Provider-independent admission | `Catalogue._admit_candidate` evaluates the shared Candidate contract. Pass. |
| 16 | Candidate-level quarantine | Compact `QuarantinedCandidate` and structured reason tests. Pass. |
| 17 | Provider failures reject the whole refresh | Retrieval/enumeration/structural failure tests. Pass. |
| 18 | Failed refresh preserves bytes | `test_catalogue_refresh_fail_closed.py` and live acceptance rehearsal. Pass. |
| 19 | Exactly one active Dataset | Workspace convention and one `var/catalogue-dataset.json` lifecycle. Pass. |
| 20 | One Dataset generation timestamp | Refresh assigns one timestamp after collection and report tests assert it. Pass. |
| 21 | Strict, versioned Dataset | Pydantic `catalogue-dataset/v1`, extra-forbid and invalid-shape tests. Pass. |
| 22 | Whole-Dataset identity/reference graph | Dataset model validates Provider, Offer, Candidate, identity, and order invariants. Pass. |
| 23 | Atomic advertised configuration | Offer Identity contains provider/source/configuration components; source Adapter tests preserve distinct configurations. Pass. |
| 24 | Offer embeds its own Vehicle Specification | `CatalogueOffer.vehicle_specification`; contract and browser facts tests. Pass. |
| 25 | Supported drivetrain scope only | Adapter boundary accepts gasoline, diesel, or battery-electric and quarantines unsupported values. Pass. |
| 26 | Explicit unavailable fact states | `known`, `not_stated`, `unclear`, `conflicting`, `not_applicable` contract and UI tests. Pass. |
| 27 | Audited images and fallback | Adapter image auditing plus image fallback/security and browser tests. Pass. |
| 28 | One normal-completion cash-flow occurrence each | Strict chronological `BaseCashFlowEvent` stream and cash-flow display tests. Pass. |
| 29 | Explicit receipt reduces total | Signed total tests and shared cash-flow display retain receipt events. Pass. |
| 30 | Unavailable amount makes totals unavailable | Contract recomputation and browser unavailable-fact tests. Pass. |
| 31 | Advertised and Calculated Totals stay distinct | Separate Dataset fields, fixture facts, CLI/detail/comparison presentation. Pass. |
| 32 | Conditional costs excluded from headline totals | Public Offer contract has no conditional-cost calculator or exposure total; source mapping emits only base events. Pass. |
| 33 | Compact quarantine evidence only | Dataset contract rejects full Candidate payloads; refresh tests assert admission facts/source metadata are absent. Pass. |
| 34 | CLI Registry inspection | `provider inspect` human/JSON reports and Registry tests. Pass. |
| 35 | CLI complete Provider set | `provider set` validates and atomically replaces one record. Pass. |
| 36 | One complete Catalogue refresh command | `catalogue refresh`; tests reject provider/source/force switches and legacy commands. Pass. |
| 37 | Inspect Dataset/exact Offer/Candidate | `catalogue inspect` and stable report contracts. Pass. |
| 38 | Site build separate from refresh | CLI composition test proves refresh does not build a Site. Pass. |
| 39 | Serve validates before binding | Static artifact tests and `CatalogueSite.serve`. Pass. |
| 40 | Human default and stable JSON | CLI report models, stream tests, and acceptance command evidence. Pass. |
| 41 | Exit statuses and diagnostic codes | `CatalogueRefreshFailure`, CLI error mapping, and failure tests. Pass. |
| 42 | Workspace conventions, no artifact path flags | CLI help tests and workspace-bound `CatalogueSite` signature guard. Pass. |
| 43 | Explanation-first bounded Landing Page | `landing-page.tsx`, shell tests, and live owner journey. Pass. |
| 44 | Factual image-forward Catalogue cards | `catalogue-offer-card.tsx`, image fallback, and Catalogue Overview browser tests. Pass. |
| 45 | Search/filter/sort in shareable URL state | `catalogue-search.ts`, overview e2e, reload/history tests. Pass. |
| 46 | Honest bounded empty state | Overview e2e asserts no-match wording does not claim whole-market absence. Pass. |
| 47 | Complete Offer detail | `offer-detail-page.tsx` and detail browser journey cover vehicle, contract, service, cash flow, and source. Pass. |
| 48 | Explicit unavailable detail facts | Fact presentation and detail e2e assert state-specific unavailable text. Pass. |
| 49 | Canonical Provider source action | Detail/comparison source links use `canonicalOfferUrl`; browser source navigation test. Pass. |
| 50 | Ordered selection of at most five Offers | Selection module and e2e tests cover add/remove/order/limit. Pass. |
| 51 | Selection URL canonicalization | Selection parser/reconciliation and malformed/duplicate/stale/excess URL e2e. Pass. |
| 52 | Dense aligned neutral comparison | `comparison-page.tsx`, matrix e2e, pinned labels, and no ranking language. Pass. |
| 53 | One shared chronological DKK chart | `catalogue-cash-flow.tsx` uses `@tanstack/charts@0.16.0` through `@tanstack/charts/react`; one-to-five Offer e2e covers the shared SVG, DKK axis, deterministic legend, tooltips, unavailable note, semantic tables, and responsive layouts. Pass. |
| 54 | Mobile comparison scroll containment | Comparison region CSS/e2e verifies internal scroll and no document overflow. Pass. |
| 55 | Dated Provider Overview and counts | `provider-overview.tsx`, Dataset-derived counts, route and mobile e2e. Pass. |
| 56 | Persistent scope/date shell context | `application-shell.tsx` Context Band and shell e2e. Pass. |
| 57 | Selection preserved while page state is local | Semantic navigation helpers and route/reload/history e2e. Pass. |
| 58 | Keyboard/assistive operation | Real-browser keyboard/focus/accessibility assertions at both viewports. Pass. |
| 59 | Mobile retains material facts | Detail, comparison, shell, provider, and Catalogue mobile e2e at 390 × 844. Pass. |
| 60 | Fail closed before page rendering | Dataset loader/query tests and unavailable/invalid startup journeys. Pass. |
| 61 | Python schema generates TypeScript contract | One direct Site-owned generator, generated declaration/schema, cross-language fixtures. Pass. |
| 62 | Narrow consumer interfaces | Package exports, Dataset module, route adapters, and clean-room import tests. Pass. |
| 63 | Dependencies point inward | CLI → owner modules → adapters; Site → Dataset contract; frontend → generated Dataset. Pass. |
| 64 | Generated outputs/Sites untracked and reproducible | `.gitignore`, generated-boundary tests, route reproducibility, history check. Pass. |
| 65 | Minimized reviewed fixtures | Provider fixture suites and source-audit provenance. Pass. |
| 66 | Fresh-checkout locked verification | README, owner guide, locked matrix, and the fresh-checkout proof recorded below, including the pinned TanStack package and frontend lockfile. Pass. |
| 67 | Live Fleasing/Terminalen admission roles | Accepted #86 record: 17 Fleasing and 2 Terminalen Offers, including the required financial/flex and operational roles. Pass. |
| 68 | Independent source/arithmetic spot checks | Accepted #86 record contains source curl checks and independent DKK recomputations. Pass. |
| 69 | Dated desktop/mobile owner acceptance | Accepted #86 owner record truthfully retains its 1280 × 720 observation; the correction replay records the required 1440 × 900 and 390 × 844 browser evidence without fabricating a second owner sign-off. Automated evidence passes; required human 1440 judgment remains pending. |
| 70 | Consumer-credit change-horizon gate | `legal-check`, committed legal record, and owner guide require official revalidation on/after 2026-11-20. Pending by design before the horizon; not a current failure. |
| 71 | Pre-rewrite rollback tag | `pre-cutover-issue-85` equals prior `main` `79deb767ece2aaa6ffe33d512fa5e0b1521471bb`; guide and test verify the exact target. Pass. |
| 72 | One reviewed repository replacement, no dual runtime | Current tree has one replacement path; merge/branch removal and post-merge rerun remain orchestrator-owned cutover actions. No implementation finding in this thread. |
| 73 | Final Standards + Spec review | This record, the owner amendment, the single correction pass, and locked verification are complete with no remaining actionable implementation finding. Orchestrator-owned cutover, legal revalidation, read-only verification, and issue closure remain outside this thread. Pass for this implementation gate. |

## #67 deliberate omissions and boundary checks

These are deliberate non-parity decisions, not missing work. The active
implementation and publication contract contain none of the following:

| Omission | Boundary proof |
| --- | --- |
| Runtime backend, database, accounts, analytics, ranking, recommendation, scoring, personalization, or market-coverage claim | Static Site lifecycle only; no server-side data path; shell copy says bounded catalogue. |
| Historical Datasets, refresh history, incremental/provider-only refresh, mixed-age publication, retained Candidates, source archives, or admitted-Offer evidence | `CatalogueDataset` has only one generation and current records; refresh replaces one file; Site verification rejects internal metadata. |
| Second presentation/publication model, frontend-owned schema, backend Comparison/readiness model, or Provider-total reconciliation | The removed `car_picker/comparison.py`; one generated Dataset schema; no `projection.json`; strict Site artifact contains only approved files. |
| Catalogue Coverage record, Registration-tax Treatment, Exposure Scenarios, or conditional-cost calculator | These names exist only in reviewed source-boundary parsing/research where needed to avoid inventing public facts; they are excluded from `CatalogueOffer` and browser contract. No public model or persisted field exists. |
| Unsupported drivetrains, third-party enrichment, undesignated sources, authentication bypass, bot evasion, or identity rotation | Fleasing/Terminalen source audits and Adapter origin/path checks; no third-party collection path. |
| Invented payments, receipts, refundability, residual values, probabilities, or future legal requirements | Strict Fact states, signed cash-flow calculation, and pending legal record. |
| Special withdrawal workflow, fallback branch, compatibility adapter, runtime switch, legacy Dataset, legacy Site, or dual implementation | Withdrawal document and backend module removed; clean-room test guards absence; only `pre-cutover-issue-85` is the documented rollback anchor. |
| Old CLI shape, source override, force flag, pipeline-stage command, Candidate command, implicit refresh/build, or catch-all release validation | CLI help/negative tests. `history-check` and `legal-check` remain separate repository gates required by #67/#86, `site inspect` remains the narrow inspection operation under the `site` noun, and contract generation remains an internal Site build step; none is a catch-all release command. |

## Historical acceptance disposition

The four July acceptance records are intentionally retained as historical
evidence, not as active product authorities or hidden requirements. They record
blocked or unsigned intermediate candidates and are useful for proving why the
clean-room replacement rejected partial refreshes, preserved unknowns, and
kept source/arithmetic decisions explicit. Each record now carries its own
historical-only notice:

| Record | Retained evidence | Explicitly superseded material |
| --- | --- | --- |
| `docs/acceptance/2026-07-28-fixed-real-offer.md` | Failed complete-refresh preservation and non-approval | 1280 × 720 fixture observation and provider-aggregate diagnostic as acceptance requirements |
| `docs/acceptance/2026-07-29-fixed-real-offer-retry.md` | Zero-admission/quarantine outcome and fail-closed admission reasoning | Prior source-control wording, provider-aggregate terminology, and 1280 × 720 task boundary |
| `docs/acceptance/2026-07-29-fixed-real-offer-vat-decision.md` | ADR-0002 VAT decision and factual Advertised-versus-Calculated distinction | Intermediate aggregate-reconciliation warning, provider-control wording, and withdrawal expectations as separate authorities |
| `docs/acceptance/2026-07-29-fixed-real-offer.md` | Failed-refresh preservation and procedural defect history | Withdrawal-isolation regression, coverage wording, provider-aggregate diagnostic, and 1280 × 720 fixture observation |

The accepted #86 record is also retained as the dated live owner gate. Its
1280 × 720 human observation is not relabeled; the #87 record adds exact
1440 × 900 and 390 × 844 automated browser replay evidence. No historical
Dataset, source document, provider-control ledger, withdrawal workflow, or
coverage authority crossed into the active implementation.

## Accepted live gate and conditional gates

The non-automated live gate is not recreated or replaced here. Its source,
arithmetic, failure-preservation, browser, defect-disposition, environment,
and owner-signoff evidence is [the dated #86 acceptance record](../acceptance/2026-08-24-live-owner-acceptance.md).
That record is explicitly pre-transition: `legal-check` reports the
2026-11-20 horizon and the committed legal record keeps `revalidation: null`.

The following actions are intentionally outside this issue-thread commit and
must be performed by the release orchestrator after the central review:

- land the reviewed replacement as the one repository cutover;
- rerun deterministic checks on the merged revision;
- remove the rewrite branch while retaining the named rollback tag; and
- revalidate current official consumer-credit law/guidance if the release date
  is on or after 2026-11-20.

## Locked verification matrix

The commands are separate by seam; there is intentionally no catch-all release
command. Results below are the results required for the final commit.

| Command | Required evidence |
| --- | --- |
| `uv sync --locked --dev` | Locked Python environment resolves without lock changes. |
| `uv run --locked ruff format --check .` | Python formatting passes. |
| `uv run --locked ruff check .` | Python lint passes. |
| `uv run --locked ty check car_picker tests` | Python types pass. |
| `uv run --locked pytest` | Full Python suite passes. |
| `uv run --locked pytest tests/test_collection.py tests/test_fleasing_adapter.py tests/test_terminalen_adapter.py tests/test_production_composition.py` | Adapter/composition seam passes. |
| `uv run --locked pytest tests/test_catalogue_refresh_contracts.py tests/test_catalogue_contract.py` | Dataset/admission contract seam passes. |
| `uv run --locked pytest tests/test_clean_room_cutover.py tests/test_cutover_corrections.py` | Clean-room, CLI boundary, historical-evidence, and exact rollback-target evidence passes. |
| `cd frontend && pnpm install --frozen-lockfile` | Locked frontend dependencies are installed. |
| `cd frontend && pnpm generate-contract && pnpm generate-routes` | Generated contract/routes are reproducible and ignored. |
| `cd frontend && pnpm typecheck` | Frontend generated declarations and TypeScript pass. |
| `cd frontend && pnpm test:module` | Dataset module browser seam passes. |
| `cd frontend && pnpm exec playwright install chromium` | Locked browser is available. |
| `cd frontend && pnpm test:e2e` | Completed static Site journeys pass at 1440 × 900 and 390 × 844. |
| `uv run --locked car-picker --workspace . site build` | Site builds from the conventional active Dataset. |
| `uv run --locked car-picker --workspace . site inspect` | Completed Site validates and reports its Dataset. |
| `uv run --locked car-picker history-check --repository .` | No generated Dataset/Site entered Git history. |
| `uv run --locked car-picker legal-check --repository .` | Pre-transition legal status is reported, not falsely passed. |
| `git diff --check` and `git status --short` | No whitespace errors and no tracked/generated worktree residue. |

The final handoff must append the actual command outputs/counts to this matrix
or to the commit handoff. Generated `var/`, frontend contract/route outputs,
build output, and caches remain ignored and are not review evidence.

## Recorded verification result for the corrected tree

These results were obtained after the TanStack correction changes and before
the final commit:

| Command | Recorded result |
| --- | --- |
| `uv sync --locked --dev` | `Resolved 21 packages in 7ms`; `Checked 20 packages in 1ms`; exit 0. |
| `uv run --locked ruff format --check .` | `106 files already formatted`; exit 0. |
| `uv run --locked ruff check .` | `All checks passed!`; exit 0. |
| `uv run --locked ty check car_picker tests` | `All checks passed!`; exit 0. |
| `uv run --locked pytest` | `165 passed in 215.54s (0:03:35)`. |
| Adapter/composition focus suite | `68 passed in 0.98s`. |
| Dataset/admission contract focus suite | `29 passed in 5.02s`. |
| Clean-room/CLI/rollback focus suite | `13 passed in 6.57s`. |
| `cd frontend && pnpm install --frozen-lockfile` | `Already up to date`; `Done in 683ms using pnpm v11.9.0`; exit 0. |
| `cd frontend && pnpm generate-contract && pnpm generate-routes` | Both generators completed; exit 0. |
| `cd frontend && pnpm typecheck` | Contract/routes regenerated and `tsc -b` completed; exit 0. |
| `cd frontend && pnpm test:module` | `4 passed (17.0s)`. |
| `cd frontend && pnpm exec playwright install chromium` | Locked Chromium available; exit 0. |
| `cd frontend && pnpm build` | `2,151 modules transformed`; Vite build completed in `4.94s`; exit 0. The existing chunk-size advisory is non-failing. |
| `cd frontend && pnpm test:e2e` | `60 passed (52.0s)`; desktop projects include 1440 × 900 and mobile projects include 390 × 844. |
| `uv run --locked car-picker --workspace . site build` | Completed successfully; exit 0. |
| `uv run --locked car-picker --workspace . site inspect` | Completed Site generated `2026-07-31T10:00:00Z`; `Catalogue Offers: 1`; `Quarantined Candidates: 0`; exit 0. |
| `uv run --locked car-picker history-check --repository .` | `Repository history check passed.`; exit 0. |
| `uv run --locked car-picker legal-check --repository .` | `Legal gate: change horizon 2026-11-20; post-transition revalidation is pending.`; exit 0, intentionally pending before the horizon. |
| `pnpm list --depth=0 @tanstack/charts` | `@tanstack/charts@0.16.0`; exit 0. |

## Fresh-checkout verification

The following proof ran from a new clone at
`/tmp/car-picker-issue87-final.bolppm` of implementation snapshot
`abd3283c01b678bb3d096d388470cac34169a67e`; ignored artifacts from this
worktree were not copied. The final handoff is an evidence-only amend of that
snapshot: no source, dependency, generated, or test changes occurred after the
proof. Working directories are explicit so the evidence can be replayed from
a fresh checkout:

| Working directory | Command | Recorded result |
| --- | --- | --- |
| `/tmp/car-picker-issue87-final.bolppm` | `git rev-parse HEAD` | `abd3283c01b678bb3d096d388470cac34169a67e`. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv sync --locked --dev` | Created `.venv`, resolved the locked 21-package environment, and installed 20 packages; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked ruff format --check .` | `106 files already formatted`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked ruff check .` | `All checks passed!`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked ty check car_picker tests` | `All checks passed!`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked pytest` | `165 passed in 216.19s (0:03:36)`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm install --frozen-lockfile` | `Already up to date`; `Done in 690ms using pnpm v11.9.0`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm generate-contract && pnpm generate-routes` | Both generators completed; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm typecheck` | Contract/routes regenerated and `tsc -b` completed; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm test:module` | `4 passed (16.2s)`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm exec playwright install chromium` | Locked Chromium available; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm build` | `2,151 modules transformed`; Vite build completed in `4.79s`; exit 0. The existing chunk-size advisory is non-failing. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm test:e2e` | `60 passed (50.7s)`; desktop projects include 1440 × 900 and mobile projects include 390 × 844. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked car-picker --workspace . site build` | Completed successfully; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked car-picker --workspace . site inspect` | `Catalogue Offers: 1`; `Quarantined Candidates: 0`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked car-picker history-check --repository .` | `Repository history check passed.`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `uv run --locked car-picker legal-check --repository .` | `Legal gate: change horizon 2026-11-20; post-transition revalidation is pending.`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm/frontend` | `pnpm list --depth=0 @tanstack/charts` | `@tanstack/charts@0.16.0`; exit 0. |
| `/tmp/car-picker-issue87-final.bolppm` | `git rev-parse pre-cutover-issue-85^{commit}` and `git rev-parse refs/remotes/origin/main^{commit}` | Both resolved to `79deb767ece2aaa6ffe33d512fa5e0b1521471bb`. |
| `/tmp/car-picker-issue87-final.bolppm` | `git status --short` | Empty. `git ls-files` showed only `frontend/src/generated/.gitignore`; generated files remained untracked/ignored. |

## Amended chart dependency evidence

The owner amendment recorded on #67 and #87 on 2026-08-25 replaces the prior
unavailable chart dependency decision with TanStack Charts. The frontend pins
the official `@tanstack/charts@0.16.0` package, and the shared seam imports
`Chart` from `@tanstack/charts/react` plus the documented chart definition,
scale, mark, and tooltip modules. The lockfile resolves that exact version.
The visual chart owns only the SVG presentation; the existing HTML tables and
accessible event lists remain the semantic source of truth for exact and
unavailable values.

```text
Working directory: <checkout>/frontend
Command: pnpm install --frozen-lockfile && pnpm list --depth=0 @tanstack/charts
Result: locked install succeeded; @tanstack/charts@0.16.0; exit 0
```

The focused and full browser checks prove the shared SVG, chronological DKK
axis, deterministic offer legend, native keyboard tooltip/focus surface,
unavailable note, semantic tables, and contained desktop/mobile comparison.
This amendment removes the dependency blocker; cutover and issue closure remain
orchestrator-owned actions.
