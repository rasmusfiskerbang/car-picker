from __future__ import annotations

import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CUTOVER_RECORD = REPOSITORY_ROOT / "docs/acceptance/2026-08-28-repository-cutover.md"
ROLLBACK_TAG = "pre-cutover-issue-85"
PRIOR_MAIN_REVISION = "79deb767ece2aaa6ffe33d512fa5e0b1521471bb"
REVIEWED_CANDIDATE = "4b58b8bcd3d347e0304f21a8970f27686abe8d1a"


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_repository_cutover_record_pins_the_verified_rollback_contract() -> None:
    assert CUTOVER_RECORD.is_file()
    record = CUTOVER_RECORD.read_text(encoding="utf-8")

    assert f"Reviewed candidate source: `{REVIEWED_CANDIDATE}`" in record
    assert f"Rollback tag: `{ROLLBACK_TAG}`" in record
    assert f"Rollback target: `{PRIOR_MAIN_REVISION}`" in record
    assert "Blocking post-cutover failures revert to the tagged revision" in record
    assert "Accepted nonblocking defects are fixed forward" in record
    assert "orchestrator/issue-85" in record
    assert "orchestrator/issue-87" in record
    assert "fresh-checkout" in record.lower()
    assert "uv run --locked pytest" in record
    assert "pnpm test:e2e" in record

    assert git("cat-file", "-t", ROLLBACK_TAG) == "tag"
    assert git("rev-parse", f"{ROLLBACK_TAG}^{{commit}}") == PRIOR_MAIN_REVISION
