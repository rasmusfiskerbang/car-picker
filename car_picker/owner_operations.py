from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

from car_picker.catalogue_model import from_legacy_dataset
from car_picker.collection import validate_complete_catalogue_dataset
from car_picker.provider_withdrawal import read_provider_control
from car_picker.publication import (
    project_catalogue,
    read_json,
    validate_presentation_projection,
)


def validate_owner_checkout(
    dataset_path: Path, repository_path: Path, provider_control_path: Path
) -> None:
    """Validate data contracts and the generated-content boundary for an owner checkout."""
    dataset = dict(read_json(dataset_path))
    validate_complete_catalogue_dataset(dataset)
    validate_presentation_projection(project_catalogue(from_legacy_dataset(dataset)))
    read_provider_control(provider_control_path)
    generated_paths = generated_paths_in_history(repository_path)
    if generated_paths:
        joined_paths = ", ".join(generated_paths)
        raise ValueError(
            "Git history contains generated provider content or built artifacts: "
            f"{joined_paths}"
        )


def generated_paths_in_history(repository_path: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repository_path), "rev-list", "--objects", "--all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "not a readable Git repository"
        raise ValueError(f"Cannot inspect Git history at {repository_path}: {detail}")
    paths = (
        line.split(" ", 1)[1] for line in result.stdout.splitlines() if " " in line
    )
    return sorted({path for path in paths if is_generated_path(path)})


def validate_version_controlled_file(repository_path: Path, file_path: Path) -> None:
    repository = repository_path.resolve()
    try:
        relative_path = file_path.resolve().relative_to(repository).as_posix()
    except ValueError as error:
        raise ValueError(
            f"{file_path} must be inside the validated Git checkout"
        ) from error
    committed = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "-e", f"HEAD:{relative_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    unchanged = subprocess.run(
        ["git", "-C", str(repository), "diff", "--quiet", "HEAD", "--", relative_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if committed.returncode != 0 or unchanged.returncode != 0:
        raise ValueError(
            f"{relative_path} must be committed without local changes before release validation"
        )


def is_generated_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and (
        parts[0] == "var" or "site" in parts or parts[-1] == "catalogue-dataset.json"
    )
