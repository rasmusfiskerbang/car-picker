from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from car_picker import (
    CandidateAdmissionFacts,
    CandidateEvidence,
    CatalogueSite,
    KnownCandidateFact,
    UnavailableCandidateFact,
)
from car_picker.__main__ import app


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRIOR_MAIN_REVISION = "79deb767ece2aaa6ffe33d512fa5e0b1521471bb"


def test_public_site_and_candidate_fact_seams_are_narrow_and_finite() -> None:
    assert CatalogueSite.__name__ == "CatalogueSite"
    assert KnownCandidateFact(
        state="known",
        value=True,
        evidence=CandidateEvidence.model_validate(
            {"sourceUrl": "https://example.test/source", "wording": "yes"}
        ),
    )
    unavailable = UnavailableCandidateFact(
        state="not_stated",
        evidence=CandidateEvidence.model_validate(
            {
                "sourceUrl": "https://example.test/source",
                "wording": "not stated",
            }
        ),
    )
    assert not hasattr(unavailable, "value")

    invalid = {
        "privateConsumerEligibility": {
            "state": "known",
            "evidence": {"sourceUrl": "https://example.test/source", "wording": "yes"},
        },
        "privateConsumerAmountAdmissibility": unavailable.model_dump(by_alias=True),
        "passengerCarScope": unavailable.model_dump(by_alias=True),
        "currentAvailability": unavailable.model_dump(by_alias=True),
        "supportedLeasingForm": unavailable.model_dump(by_alias=True),
    }
    with pytest.raises(ValidationError):
        CandidateAdmissionFacts.model_validate(invalid)


def test_site_commands_are_workspace_bound_and_grouped() -> None:
    runner = CliRunner()

    for arguments in (("site", "build", "--help"), ("site", "serve", "--help")):
        result = runner.invoke(app, list(arguments))
        assert result.exit_code == 0, result.output
        assert "--dataset" not in result.output
        assert "--output" not in result.output
        assert "--site" not in result.output

    for command in ("build-site", "serve-site", "release-check", "diagnose-aggregates"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code != 0


def test_public_facades_do_not_reach_into_private_car_picker_modules() -> None:
    facade_names = {"__main__.py", "publication.py"}
    for path in (REPOSITORY_ROOT / "car_picker").glob("*.py"):
        if path.name not in facade_names:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        private_imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("car_picker.")
        ]
        assert private_imports == [], (path.name, private_imports)

    main_source = (REPOSITORY_ROOT / "car_picker/__main__.py").read_text(
        encoding="utf-8"
    )
    assert "from car_picker import (" in main_source


def test_route_output_is_generated_reproducibly_and_ignored() -> None:
    output = REPOSITORY_ROOT / "frontend/src/generated/route-output.ts"
    original = output.read_bytes() if output.exists() else None
    try:
        for _ in range(2):
            result = subprocess.run(
                ["pnpm", "generate-routes"],
                cwd=REPOSITORY_ROOT / "frontend",
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            current = output.read_bytes()
            if _ == 0:
                first = current
            else:
                assert current == first

        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "--quiet",
                str(output.relative_to(REPOSITORY_ROOT)),
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        assert ignored.returncode == 0
        tracked = subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                str(output.relative_to(REPOSITORY_ROOT)),
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert tracked.returncode != 0
        assert "/catalogue" in output.read_text(encoding="utf-8")
    finally:
        if original is None:
            output.unlink(missing_ok=True)
        else:
            output.write_bytes(original)


def test_rollback_instructions_pin_the_prior_main_revision() -> None:
    guide = (REPOSITORY_ROOT / "docs/operations/owner-guide.md").read_text(
        encoding="utf-8"
    )
    assert "pre-cutover-issue-85" in guide
    tag = subprocess.run(
        ["git", "rev-parse", "--verify", "pre-cutover-issue-85^{commit}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tag.returncode == 0, tag.stderr
    assert tag.stdout.strip() == PRIOR_MAIN_REVISION

    for main_ref in ("refs/heads/main", "refs/remotes/origin/main"):
        main = subprocess.run(
            ["git", "rev-parse", f"{main_ref}^{{commit}}"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if main.returncode == 0:
            assert main.stdout.strip() == tag.stdout.strip()
            break
