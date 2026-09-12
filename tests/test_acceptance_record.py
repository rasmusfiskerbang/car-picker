from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_RECORD = (
    REPOSITORY_ROOT / "docs/acceptance/2026-08-24-live-owner-acceptance.md"
)


def test_live_owner_acceptance_record_contains_the_gate_evidence() -> None:
    record = ACCEPTANCE_RECORD.read_text(encoding="utf-8")

    assert re.search(r"Application commit: `[0-9a-f]{40}`", record)
    for required_field in (
        "Dataset generation: `2026-08-24T07:16:31Z`",
        "Provider counts: Fleasing 17; Terminalen 2",
        "Catalogue Offers: 19",
        "Quarantined Candidates: 138",
        "Owner-recorded desktop viewport: 1280 × 720 (historical owner evidence)",
        "Correction replay desktop viewport: 1440 × 900",
        "Mobile viewport: 390 × 844",
        "2026-11-20",
        "Owner name: Rasmus Fisker Bang",
        "Signed on: 2026-08-24",
        "Decision: approved",
        "fleasing:442795427:private-8f745634e8cf",
        "terminalen:HY_IONIQ5_NE_DK_IONIQ5_MY27:private-e25cc77f6e4b",
        "fleasing-html-v7",
        "uv run --locked car-picker --workspace . --json catalogue refresh",
        "uv run --locked car-picker --workspace . site build",
        "uv run --locked car-picker --workspace . site serve --port 4173",
        "15 passed, 2 subtests passed",
        "164 passed",
        "29 passed, 3 subtests passed",
    ):
        assert required_field in record

    for frontend_command in (
        "cd frontend && pnpm install --frozen-lockfile",
        "cd frontend && pnpm generate-contract",
        "cd frontend && pnpm generate-routes",
        "cd frontend && pnpm typecheck",
        "cd frontend && pnpm test:module",
        "cd frontend && pnpm build",
        "cd frontend && pnpm exec playwright install chromium",
        "cd frontend && pnpm test:e2e",
    ):
        assert f"`{frontend_command}`" in record

    assert "59 passed" in record
    assert "desktop projects use 1440 × 900" in record
    assert "post-transition revalidation is pending" in record
