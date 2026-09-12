from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from car_picker import CatalogueSite
from car_picker.__main__ import app


REPOSITORY_ROOT = Path(__file__).parents[1]


def test_clean_room_removes_superseded_production_surfaces() -> None:
    package_files = {
        path.name for path in (REPOSITORY_ROOT / "car_picker").glob("*.py")
    }
    assert "catalogue_model.py" not in package_files
    assert "comparison.py" not in package_files
    assert "presentation_model.py" not in package_files
    assert "provider_withdrawal.py" not in package_files
    assert "provider" + "_access.py" not in package_files

    assert not (REPOSITORY_ROOT / "docs/operations/provider-withdrawal.md").exists()
    assert not (REPOSITORY_ROOT / "config" / ("provider" + "-access.json")).exists()

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPOSITORY_ROOT / "car_picker").glob("*.py")
    )
    assert "catalogue_model" not in source
    assert "CatalogueOfferComparison" not in source
    assert "refresh_all_providers" not in source
    assert "refresh_catalogue" not in source
    assert "complete_catalogue_dataset" not in source
    assert "projection.json" not in source


def test_historical_acceptance_records_have_explicit_clean_room_disposition() -> None:
    review = (
        REPOSITORY_ROOT / "docs/reviews/2026-08-24-final-standards-spec.md"
    ).read_text(encoding="utf-8")
    records = (
        "docs/acceptance/2026-07-28-fixed-real-offer.md",
        "docs/acceptance/2026-07-29-fixed-real-offer-retry.md",
        "docs/acceptance/2026-07-29-fixed-real-offer-vat-decision.md",
        "docs/acceptance/2026-07-29-fixed-real-offer.md",
    )
    for record in records:
        assert (REPOSITORY_ROOT / record).is_file()
        assert f"`{record}`" in review
    assert "intentionally retained as historical" in review
    assert "historical-only notice" in review


def test_backend_public_interface_has_no_comparison_model_or_withdrawal_workflow() -> (
    None
):
    import car_picker

    assert not hasattr(car_picker, "CatalogueOfferComparison")
    assert not hasattr(car_picker, "calculate_catalogue_offer_comparison")
    assert not hasattr(car_picker, "generate_catalogue_contract_sources")


def test_catalogue_refresh_rejects_runtime_provider_and_source_switches() -> None:
    runner = CliRunner()

    for arguments in (
        ["--provider", "fleasing"],
        ["--adapter", "terminalen"],
        ["--source", "https://example.test/"],
        ["--force"],
    ):
        result = runner.invoke(app, ["catalogue", "refresh", *arguments])

        assert result.exit_code != 0
        assert (
            "no such option" in result.output.lower()
            or "no such command" in result.output.lower()
        )


def test_generated_contracts_and_routes_are_untracked_boundaries() -> None:
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            "frontend/src/generated/catalogue-dataset.ts",
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
            "frontend/src/generated/catalogue-dataset.ts",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.returncode != 0

    route_output = REPOSITORY_ROOT / "frontend/src/generated/route-output.ts"
    generated = subprocess.run(
        ["pnpm", "generate-routes"],
        cwd=REPOSITORY_ROOT / "frontend",
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    assert route_output.exists()
    assert "/catalogue" in route_output.read_text(encoding="utf-8")
    route_ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            str(route_output.relative_to(REPOSITORY_ROOT)),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    assert route_ignored.returncode == 0
    route_tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            str(route_output.relative_to(REPOSITORY_ROOT)),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert route_tracked.returncode != 0


def test_catalogue_site_is_the_public_site_seam() -> None:
    assert CatalogueSite.__name__ == "CatalogueSite"
    runner = CliRunner()
    result = runner.invoke(app, ["site", "build", "--help"])
    assert result.exit_code == 0, result.output
    assert "--dataset" not in result.output
    assert "--output" not in result.output


def test_catalogue_site_is_bound_to_workspace_artifacts() -> None:
    assert set(inspect.signature(CatalogueSite).parameters) == {"workspace"}


def test_python_modules_use_public_package_seams_for_internal_imports() -> None:
    facades = {"__main__.py", "publication.py"}
    for path in (REPOSITORY_ROOT / "car_picker").glob("*.py"):
        if path.name not in facades:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            assert not node.module.startswith("car_picker.")

    main_source = (REPOSITORY_ROOT / "car_picker/__main__.py").read_text(
        encoding="utf-8"
    )
    assert "from car_picker import (" in main_source
