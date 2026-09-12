# Owner operating guide

This is the canonical operating guide for the owner-only private-leasing
comparison. Run commands from the repository root with Python 3.14 or newer.
The Provider Registry is authoritative for active coverage. Catalogue Datasets,
route outputs, and Sites are reproducible local artifacts and must never be
committed.

## Locked verification matrix

There is no catch-all validation command. Each direct command owns one seam and
must use the committed dependency locks:

```sh
uv sync --locked --dev
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check car_picker tests
uv run --locked pytest
uv run --locked pytest tests/test_collection.py tests/test_fleasing_adapter.py tests/test_terminalen_adapter.py tests/test_production_composition.py
uv run --locked pytest tests/test_catalogue_refresh_contracts.py tests/test_catalogue_contract.py
uv run --locked pytest tests/test_clean_room_cutover.py tests/test_cutover_corrections.py
cd frontend
pnpm install --frozen-lockfile
pnpm generate-contract
pnpm generate-routes
pnpm typecheck
pnpm test:module
pnpm exec playwright install chromium
pnpm test:e2e
cd ..
uv run --locked car-picker --workspace . site build
uv run --locked car-picker --workspace . site inspect
uv run --locked car-picker history-check --repository .
uv run --locked car-picker legal-check --repository .
```

The Python formatting, Ruff lint, `ty` typing, Python tests, Provider Adapter
tests, contract tests, clean-room architecture/import/style tests, frontend
contract and route generators, frontend type/module tests, production Site
build, and Playwright commands are intentionally separate. `pnpm install
--frozen-lockfile` and `uv sync --locked` are required in a fresh checkout;
`uv run --locked` refuses to alter the Python lock during checks.

The contract generator writes ignored files under `frontend/src/generated/`.
The route generator reads the tracked `frontend/src/route-manifest.json` and
writes the ignored `frontend/src/generated/route-output.ts`. Site build and
Playwright write ignored `var/`, `frontend/dist/`, and test-result artifacts.
Remove generated files and caches before committing and confirm
`git status --short` is empty.

For a clean-room proof, clone the final commit into a new directory without
copying `var/`, `frontend/src/generated/`, `frontend/dist/`, or caches, then
run the same locked setup and direct checks. The committed inputs are the
Provider Registry, source audits and ADRs, legal record, reviewed fixtures,
application code, and route manifest.

`history-check` and `legal-check` are separate repository-maintenance gates,
not a catch-all release command. `site inspect` is the narrow inspection
operation under the `site` noun and is retained because the accepted #86 live
gate records the completed artifact through that operation. The contract
generator is an internal Site-owned build step used by `pnpm generate-contract`;
it is not a package-facade or owner-CLI API.

## Provider Registry operations

Inspect the complete ordered Registry:

```sh
uv run --locked car-picker provider inspect
uv run --locked car-picker --json provider inspect
```

Replace one complete record atomically. An inactive record requires an explicit
reason and explanation; changing the Registry does not mutate the active
Catalogue Dataset or Site:

```sh
uv run --locked car-picker provider set terminalen inactive \
  --reason blocked \
  --explanation "Owner paused retrieval pending source review."
git diff -- config/provider-registry.jsonl
```

Reactivate a record by replacing it with the complete public record:

```sh
uv run --locked car-picker provider set terminalen active
```

Commit Registry changes before a refresh. Do not add a provider-specific CLI
switch, source URL, adapter selector, force flag, or second control file.
Before live retrieval, review the [Fleasing](../source-audits/fleasing.md) and
[Terminalen](../source-audits/terminalen.md) audits under
[ADR-0001](../adr/0001-public-provider-access.md). A source audit that is not
currently allowed blocks contact with that active provider; the Registry's
active/inactive state remains the sole participation control.

## Refresh and inspection

Refresh is one complete all-active-provider operation. It uses the statically
composed Provider Adapters, assigns one generation timestamp, admits only
strict public Offers, quarantines incomplete Candidates, and atomically
replaces `var/catalogue-dataset.json`:

```sh
uv run --locked car-picker --workspace . catalogue refresh
uv run --locked car-picker --workspace . catalogue inspect
uv run --locked car-picker --workspace . --json catalogue inspect
uv run --locked car-picker --workspace . catalogue inspect 'terminalen:offer:identity'
```

The refresh contacts only the designated first-party source paths documented
in the audits. It retains normalized facts and necessary transient evidence in
memory; it does not retain full fetched pages or prior Datasets. A provider,
enumeration, or structural failure leaves the previous active Dataset
byte-for-byte unchanged.

## Site build and serve

The Site commands are grouped under the workspace-bound `site` noun. They
always read and write the conventional workspace artifacts:

```sh
uv run --locked car-picker --workspace . site build
uv run --locked car-picker --workspace . site inspect
uv run --locked car-picker --workspace . site serve --port 4173
```

Build packages the exact active Dataset bytes, generates the Pydantic contract
and frontend route output, compiles the frontend, writes the integrity
manifest, and verifies the completed artifact before atomic replacement. A
failed build leaves the prior completed Site active. `site serve` validates the
Site before binding and serves no runtime backend.

## Diagnostics and recovery

Use inspection output and structured refresh/Site errors as the diagnostics
surface; they never alter generated artifacts:

```sh
uv run --locked car-picker --workspace . --json catalogue inspect
uv run --locked car-picker --workspace . --json site inspect
```

- If refresh fails, inspect its error and confirm the active Dataset is
  unchanged. Repair the source audit, Registry, or adapter boundary, then
  rerun the complete refresh. Never hand-edit the Dataset.
- If Site build fails, keep serving the last completed Site. Repair the input
  or frontend contract/build failure, rerun `site build`, then run `site inspect`
  before serving. Never hand-edit Site files.
- If generated output or a Site was accidentally committed, stop release and
  run `history-check`; current ignored files alone are not a history repair.

## Blocking post-cutover rollback

The repository keeps the named tag `pre-cutover-issue-85` at the prior `main`
revision `79deb767ece2aaa6ffe33d512fa5e0b1521471bb`. It is the only rollback
anchor for a blocking post-cutover recovery; do not choose an arbitrary
reviewed commit:

```sh
git fetch --tags
git rev-parse pre-cutover-issue-85^{commit}
git rev-parse main^{commit}
git log --oneline pre-cutover-issue-85..HEAD
git revert --no-edit pre-cutover-issue-85..HEAD
uv sync --locked --dev
uv run --locked car-picker history-check --repository .
```

Preserve the incident, reason, rollback commit, and operational result in the
dated acceptance record. The rollback is a normal revert, so it does not erase
the audit trail.

## Conditional consumer-credit revalidation

The consumer-credit gate is mandatory for any cutover or release on or after
20 November 2026. Run it separately from the history check:

```sh
uv run --locked car-picker legal-check --repository .
```

Before the horizon, the committed
`config/consumer-credit-legal-review.json` deliberately has
`"revalidation": null`. On or after the horizon, `legal-check` fails until the
record contains a completed, dated review against then-current official law and
official guidance, explicit classification and disclosure conclusions,
implementation impact, and dated owner sign-off. The record and any required
code changes must be committed together. See
[consumer-credit-revalidation.md](consumer-credit-revalidation.md).

Before release, also complete the dated
[fixed real-offer acceptance procedure](fixed-real-offer-acceptance.md),
including reviewed fixtures, source audits, and recorded operational facts or
non-approval. Those records remain normative evidence; generated Dataset and
Site outputs do not become repository inputs.
