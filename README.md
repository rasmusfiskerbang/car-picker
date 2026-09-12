# Car picker

Owner-operated, evidence-backed comparison of Danish private passenger-car
leasing offers.

Use the [owner operating guide](docs/operations/owner-guide.md) as the
canonical source for Provider Registry operations, source-access boundaries,
refresh and inspection, diagnostics, Site builds/serving, recovery, rollback,
the direct verification matrix, and the conditional consumer-credit release
gate.

The implementation evidence for the final #87 Standards + Spec gate is in
[the dated review record](docs/reviews/2026-08-24-final-standards-spec.md).

## Development setup

Install the development tools and Git hooks:

```console
uv sync --locked --dev
uv run --locked prek install
```

Run the direct checks individually so each failure identifies its owner seam:

```console
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check car_picker tests
uv run --locked pytest
uv run --locked pytest tests/test_collection.py tests/test_fleasing_adapter.py tests/test_terminalen_adapter.py tests/test_production_composition.py
uv run --locked pytest tests/test_catalogue_refresh_contracts.py
uv run --locked pytest tests/test_clean_room_cutover.py tests/test_cutover_corrections.py
```

The production browser application lives under `frontend/`. Install its locked
dependencies and Chromium once, then run the frontend checks:

```console
cd frontend
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
pnpm generate-contract
pnpm generate-routes
pnpm typecheck
pnpm test:module
pnpm test:e2e
```

Build a completed Site from the public command:

```console
cd ..
uv run --locked car-picker --workspace . site build
```

Generated contracts, route outputs, Datasets, Sites, and caches are ignored
local artifacts. Remove them and confirm `git status --short` is clean before a
commit. There is intentionally no catch-all validation command.
