from __future__ import annotations

from pathlib import Path

from car_picker import CatalogueDataset, CatalogueSite


def build_site(dataset_path: Path, site_path: Path) -> None:
    """Exercise the public workspace Site seam with a fixture workspace."""
    workspace = site_path.parent.parent
    active_path = workspace / "var/catalogue-dataset.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_bytes(dataset_path.read_bytes())
    CatalogueSite(workspace).build()


def write_workspace_dataset(workspace: Path, dataset_path: Path) -> Path:
    active_path = workspace / "var/catalogue-dataset.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_bytes(dataset_path.read_bytes())
    return active_path


def open_site(site_path: Path) -> CatalogueDataset:
    return CatalogueSite(site_path.parent.parent).open()
