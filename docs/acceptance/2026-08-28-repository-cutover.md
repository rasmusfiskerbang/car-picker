# Repository cutover evidence — 2026-08-28

This record is the #88 cutover handoff for the clean-room replacement in
#67. It records the repository boundary and rollback contract; deployment and
issue closure remain outside this change.

## Cutover inputs

- Base revision: `79deb767ece2aaa6ffe33d512fa5e0b1521471bb` (`main` before the
  replacement).
- Reviewed candidate source: `4b58b8bcd3d347e0304f21a8970f27686abe8d1a`
  (`orchestrator/issue-87`, accepted after the owner-approved TanStack Charts
  amendment).
- Cutover revision: the single cohesive commit containing this record and the
  reviewed replacement tree; the orchestrator handoff reports its SHA.

The candidate is landed as one repository replacement. The obsolete Dataset,
Site, presentation, comparison, provider-control, withdrawal, and parallel
test surfaces are deleted from the landed tree. The active implementation has
no fallback branch, compatibility adapter, runtime implementation switch,
legacy Dataset, legacy Site, or dual production path. Missing-image handling
is a factual presentation fallback and is not a second catalogue authority.

## Rollback contract

- Rollback tag: `pre-cutover-issue-85`.
- Rollback target: `79deb767ece2aaa6ffe33d512fa5e0b1521471bb`.
- The tag is annotated, and its peeled commit is the pre-cutover `main`
  revision.
- Blocking post-cutover failures revert to the tagged revision with a normal
  revert of the landed range, preserving the incident and audit trail.
- Accepted nonblocking defects are fixed forward on the replacement revision.

The operator verifies the target before recovery:

```sh
git fetch --tags
git cat-file -t pre-cutover-issue-85
git rev-parse pre-cutover-issue-85^{commit}
git rev-parse main^{commit}
git revert --no-edit pre-cutover-issue-85..HEAD
```

The rollback tag is the only repository rollback anchor for this cutover; an
arbitrary intermediate review or implementation commit is not substituted.

## Verification evidence

The final merged candidate is checked from a fresh-checkout using the locked,
direct commands in `README.md` and `docs/operations/owner-guide.md`. The
verification matrix is intentionally separate by owner seam and has no
catch-all release command.

Status: passed on the merged candidate tree from a fresh checkout. The
observed direct results are:

| Check | Result |
| --- | --- |
| `uv sync --locked --dev` | Pass; locked environment resolved 21 packages and installed 20. |
| `uv run --locked ruff format --check .` | Pass; 108 files already formatted. |
| `uv run --locked ruff check .` | Pass. |
| `uv run --locked ty check car_picker tests` | Pass. |
| `uv run --locked pytest -q` | Pass; 166 tests and 28 subtests in 211.53 seconds. |
| Provider Adapter/focused workflow tests | Pass; 68 tests and 7 subtests. |
| Dataset contract/refresh tests | Pass; 29 tests and 8 subtests. |
| Clean-room, correction, and repository-cutover tests | Pass; 14 tests. |
| `pnpm install --frozen-lockfile` | Pass in the fresh frontend checkout. |
| Contract and route generation | Pass; generated outputs are ignored. |
| `pnpm typecheck` | Pass. |
| `pnpm test:module` | Pass; 4 tests. |
| `pnpm build` | Pass; 2,151 modules transformed. The bundler emitted only its existing advisory about a chunk over 500 kB. |
| `pnpm exec playwright install chromium` | Pass. |
| `pnpm test:e2e` | Pass; 60 tests at the configured desktop/mobile viewports. |
| Workspace-bound `site build` and `site inspect` | Pass; one fixture Catalogue Offer, zero Quarantined Candidates, generation `2026-07-31T10:00:00Z`. |
| `history-check` | Pass. |
| `legal-check` | Pass; pre-horizon gate reports post-transition revalidation pending for `2026-11-20`. |

The fresh checkout was detached at the cutover commit and began without
tracked generated contracts, route output, active Datasets, Sites, or caches.
All generated files produced by the checks were ignored, and the checkout was
clean apart from those ignored artifacts.

## Browser QA

The completed Site was served from the workspace and inspected in a real
browser. The landing, Catalogue Overview, Provider Overview, and Offer
Comparison routes rendered; selecting the Offer propagated through the hash
URL into comparison; the chart exposed DKK axis labels, chronological events,
and explicit unavailable-value text; and the mobile filter dialog opened and
closed accessibly. At the observed 1440 × 900 and 390 × 844 viewports,
document and body scroll widths matched the viewport width. Browser console
errors were empty.

The relevant direct commands include:

```sh
uv run --locked pytest
uv run --locked pytest tests/test_clean_room_cutover.py tests/test_cutover_corrections.py
cd frontend && pnpm test:e2e
```

The final verification also confirms that generated contracts, route output,
active Datasets, Sites, and caches are ignored and absent from the commit.

## Branch retirement

After the checks passed, the superseded rewrite/candidate branches
`orchestrator/issue-85` and `orchestrator/issue-87` were retired. The annotated
rollback tag remains preserved after that cleanup.
