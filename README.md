# Car picker

Owner-operated, evidence-backed comparison of Danish private passenger-car
leasing offers.

Use the [owner operating guide](docs/operations/owner-guide.md) as the canonical
source for fixture verification, live refresh, schema and Git-history
validation, static builds, LAN serving, diagnostics, source-access boundaries,
and provider withdrawal.

## Development checks

Install the development tools and Git hooks:

```console
uv sync --dev
uv run prek install
```

Run every commit hook against the complete repository. This is the canonical
local validation command for linting, formatting, and type checking:

```console
uv run prek run --all-files
```

The individual checks can also be run directly:

```console
uv run ruff check .
uv run ruff format --check .
uv run ty check car_picker tests
```

Run the full test suite with:

```console
uv run pytest
```
