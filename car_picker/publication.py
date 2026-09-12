"""Build, open, verify, and serve the static Catalogue Site."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import uuid
from collections.abc import Mapping
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import BaseServer
from typing import Any

from pydantic import JsonValue

from car_picker import CatalogueDataset, catalogue_dataset_json_schema


_CATALOGUE_DATASET_FILENAME = "catalogue-dataset.json"
_CATALOGUE_DATASET_SCHEMA_FILENAME = "catalogue-dataset-schema.json"
_SITE_INTEGRITY_FILENAME = "catalogue-site-integrity.json"
_SITE_INTEGRITY_SCHEMA_VERSION = "catalogue-site-integrity/v1"
_CATALOGUE_DATASET_SCHEMA_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "frontend/src/generated/catalogue-dataset-schema.json"
)
_CATALOGUE_DATASET_SCHEMA_MODULE = (
    Path(__file__).resolve().parents[1]
    / "frontend/src/generated/catalogue-dataset-schema.ts"
)
_CATALOGUE_STATIC_ARTIFACT_FILENAMES = {
    "app.js",
    "index.html",
    _CATALOGUE_DATASET_FILENAME,
    _CATALOGUE_DATASET_SCHEMA_FILENAME,
    _SITE_INTEGRITY_FILENAME,
    "styles.css",
}
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_ROOT = _REPOSITORY_ROOT / "frontend"
_FORBIDDEN_ARTIFACT_KEYS = {
    "contentSha256",
    "hash",
    "parserMetadata",
    "parserVersion",
    "quarantineReasons",
    "sourceMetadata",
}


class SiteBuildError(ValueError):
    """A Site build failed before replacing the active artifact."""

    def __init__(
        self,
        message: str,
        *,
        output_path: Path,
        safe_artifact: Path | None,
    ) -> None:
        super().__init__(message)
        self.output_path = output_path
        self.safe_artifact = safe_artifact


class CatalogueSite:
    """The workspace-bound public lifecycle for one completed Catalogue Site."""

    def __init__(
        self,
        workspace: Path,
    ) -> None:
        self.workspace = workspace.resolve()
        self.dataset_path = self.workspace / "var/catalogue-dataset.json"
        self.site_path = self.workspace / "var/site"

    def build(self) -> None:
        """Build the active workspace Dataset into its ignored Site artifact."""
        _build_site(self.dataset_path, self.site_path)

    def open(self) -> CatalogueDataset:
        """Open and validate the completed workspace Site."""
        return _open_site(self.site_path)

    def serve(self, port: int = 4173) -> None:
        """Validate and serve the completed workspace Site."""
        _serve_site(self.site_path, port)


def _build_site(dataset_path: Path, output_path: Path) -> None:
    """Validate and atomically publish one exact Catalogue Dataset."""
    output_path = output_path.absolute()
    safe_artifact = _find_safe_artifact(output_path)
    dataset_bytes, raw_dataset = _read_json_with_bytes(
        dataset_path, "canonical catalogue dataset"
    )
    CatalogueDataset.model_validate(raw_dataset)
    schema = catalogue_dataset_json_schema()

    try:
        _write_site_atomically(output_path, dataset_bytes, schema)
    except SiteBuildError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise SiteBuildError(
            f"Catalogue Site build failed: {error}",
            output_path=output_path,
            safe_artifact=safe_artifact,
        ) from error
    return None


def _open_site(site_path: Path) -> CatalogueDataset:
    """Open and validate the Site's own completed Dataset and schema."""
    return _read_verified_site(site_path)[0]


def _serve_site(site_path: Path, port: int = 4173) -> None:
    """Validate a completed Site before binding its HTTP server."""
    _read_verified_site(site_path)
    if not 1 <= port <= 65535:
        raise ValueError("--port must be between 1 and 65535")

    site_path = site_path.absolute()

    class StaticSiteHandler(SimpleHTTPRequestHandler):
        def __init__(
            self,
            request: socket.socket,
            client_address: tuple[str, int],
            server: BaseServer,
        ) -> None:
            super().__init__(request, client_address, server, directory=str(site_path))

    with ThreadingHTTPServer(("0.0.0.0", port), StaticSiteHandler) as server:
        print(
            f"Serving completed static artifact on http://0.0.0.0:{port}/",
            flush=True,
        )
        server.serve_forever()


def _read_json_with_bytes(
    path: Path,
    name: str,
) -> tuple[bytes, Mapping[str, Any]]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Cannot read {name} at {path}: {error}") from error
    return raw, _object_value(value, name)


def _write_site_atomically(
    output_path: Path,
    dataset: Mapping[str, Any] | bytes,
    schema: Mapping[str, Any],
) -> None:
    """Stage and verify one Site before atomically replacing the prior one."""
    output_path = output_path.absolute()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_bytes = (
        dataset
        if isinstance(dataset, bytes)
        else json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    schema_bytes = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    with tempfile.TemporaryDirectory(
        prefix=".car-picker-site-", dir=output_path.parent
    ) as staging_root:
        staging_path = Path(staging_root) / "site"
        staging_path.mkdir()
        (staging_path / _CATALOGUE_DATASET_FILENAME).write_bytes(dataset_bytes)
        (staging_path / _CATALOGUE_DATASET_SCHEMA_FILENAME).write_bytes(schema_bytes)
        _build_frontend(staging_path)
        _add_asset_integrity(staging_path)
        _verify_static_artifact(staging_path, schema)
        _replace_directory(staging_path, output_path)


def _build_frontend(staging_path: Path) -> None:
    """Generate the contract once, then run compile-only production build."""
    environment = _frontend_environment(staging_path)
    _run_frontend_command(["pnpm", "generate-contract"], environment)
    _run_frontend_command(["pnpm", "generate-routes"], environment)
    _run_frontend_command(["pnpm", "build"], environment)


def _add_asset_integrity(site_path: Path) -> None:
    files = {}
    for filename in sorted(
        _CATALOGUE_STATIC_ARTIFACT_FILENAMES - {_SITE_INTEGRITY_FILENAME}
    ):
        content = (site_path / filename).read_bytes()
        files[filename] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        }
    manifest = {
        "files": files,
        "schemaVersion": _SITE_INTEGRITY_SCHEMA_VERSION,
    }
    (site_path / _SITE_INTEGRITY_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _frontend_environment(staging_path: Path) -> dict[str, str]:
    environment = dict(os.environ)
    # The workspace command owns the Python used for contract generation; an
    # ambient override would make Site builds differ from frontend checks.
    environment.pop("CAR_PICKER_PYTHON", None)
    environment["CAR_PICKER_SITE_OUTPUT"] = str(staging_path)
    if shutil.which("node", path=environment.get("PATH")) is None:
        codex_node_directory = Path(
            "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin"
        )
        if (codex_node_directory / "node").is_file():
            environment["PATH"] = (
                f"{codex_node_directory}{os.pathsep}{environment.get('PATH', '')}"
            )
    return environment


def _run_frontend_command(command: list[str], environment: Mapping[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=_FRONTEND_ROOT,
        env=dict(environment),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(
            output
            for output in (result.stdout.strip(), result.stderr.strip())
            if output
        )
        if not detail:
            detail = f"exit status {result.returncode}"
        raise ValueError(f"frontend command {' '.join(command)} failed: {detail}")


def generate_catalogue_contract_sources() -> dict[str, Any]:
    """Generate the frontend contract directly from the Catalogue schema."""
    pinned_schema = catalogue_dataset_json_schema()
    serialized_schema = json.dumps(pinned_schema, ensure_ascii=False, indent=2)
    _CATALOGUE_DATASET_SCHEMA_SOURCE.write_text(
        f"{serialized_schema}\n", encoding="utf-8"
    )
    _CATALOGUE_DATASET_SCHEMA_MODULE.write_text(
        "/* Generated from the Pydantic serialization schema. Do not edit. */\n"
        "export const catalogueDatasetJsonSchema = "
        f"{serialized_schema} as const;\n\n"
        "export default catalogueDatasetJsonSchema;\n",
        encoding="utf-8",
    )
    return pinned_schema


def _verify_static_artifact(
    site_path: Path,
    schema: Mapping[str, Any] | None = None,
) -> None:
    """Reject an incomplete or corrupt static Site artifact."""
    _read_verified_site(site_path, schema)


def _read_verified_site(
    site_path: Path,
    schema: Mapping[str, Any] | None = None,
) -> tuple[CatalogueDataset, Mapping[str, Any]]:
    if not site_path.is_dir():
        raise ValueError("static artifact must be a directory")
    entries = tuple(site_path.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in entries):
        raise ValueError("static artifact must contain only approved regular files")
    files = {path.name for path in entries}
    if files != _CATALOGUE_STATIC_ARTIFACT_FILENAMES:
        raise ValueError("static artifact contains unexpected or missing files")
    _verify_asset_integrity(site_path)

    _, raw_dataset = _read_json_with_bytes(
        site_path / _CATALOGUE_DATASET_FILENAME,
        "packaged Catalogue Dataset",
    )
    dataset = CatalogueDataset.model_validate(raw_dataset)
    _, packaged_schema = _read_json_with_bytes(
        site_path / _CATALOGUE_DATASET_SCHEMA_FILENAME,
        "packaged Catalogue Dataset schema",
    )
    expected_schema = (
        dict(schema) if schema is not None else catalogue_dataset_json_schema()
    )
    if packaged_schema != expected_schema:
        raise ValueError(
            "static artifact must export the Pydantic Dataset serialization schema"
        )
    if _contains_forbidden_artifact_key(raw_dataset):
        raise ValueError("static artifact Dataset contains internal metadata")

    index = (site_path / "index.html").read_text(encoding="utf-8")
    required_index_markers = ('type="module"', 'src="./app.js"', 'href="./styles.css"')
    if any(marker not in index for marker in required_index_markers):
        raise ValueError("static artifact browser application is incomplete")
    return dataset, packaged_schema


def _verify_asset_integrity(site_path: Path) -> None:
    _, raw_manifest = _read_json_with_bytes(
        site_path / _SITE_INTEGRITY_FILENAME,
        "static artifact integrity manifest",
    )
    if set(raw_manifest) != {"files", "schemaVersion"}:
        raise ValueError("static artifact integrity manifest has an invalid shape")
    if raw_manifest["schemaVersion"] != _SITE_INTEGRITY_SCHEMA_VERSION:
        raise ValueError(
            "static artifact integrity manifest has an unsupported version"
        )
    files = raw_manifest["files"]
    if not isinstance(files, Mapping):
        raise ValueError("static artifact integrity manifest files must be an object")
    expected_files = _CATALOGUE_STATIC_ARTIFACT_FILENAMES - {_SITE_INTEGRITY_FILENAME}
    if set(files) != expected_files:
        raise ValueError("static artifact integrity manifest has an invalid file list")

    for filename in sorted(expected_files):
        entry = files[filename]
        if not isinstance(entry, Mapping) or set(entry) != {"sha256", "size"}:
            raise ValueError(
                f"static artifact integrity manifest has an invalid entry for {filename}"
            )
        digest = entry["sha256"]
        size = entry["size"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            raise ValueError(
                f"static artifact integrity manifest has an invalid entry for {filename}"
            )
        content = (site_path / filename).read_bytes()
        if size != len(content) or digest != hashlib.sha256(content).hexdigest():
            raise ValueError(f"static artifact integrity mismatch for {filename}")


def _find_safe_artifact(output_path: Path) -> Path | None:
    if not output_path.exists() and not output_path.is_symlink():
        return None
    try:
        _open_site(output_path)
    except OSError, UnicodeError, ValueError:
        return None
    return output_path


def _contains_forbidden_artifact_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in _FORBIDDEN_ARTIFACT_KEYS or _contains_forbidden_artifact_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_artifact_key(item) for item in value)
    return False


def _replace_directory(staging_path: Path, output_path: Path) -> None:
    """Publish an immutable artifact through one atomic pointer replacement."""
    if output_path.exists() and not output_path.is_symlink():
        raise ValueError(
            "existing static artifact predates atomic publication; "
            "move it aside before rebuilding"
        )
    identifier = uuid.uuid4().hex
    artifact_path = output_path.with_name(f".{output_path.name}.artifact-{identifier}")
    next_link = output_path.with_name(f".{output_path.name}.next-{identifier}")
    previous_artifact = output_path.resolve() if output_path.is_symlink() else None
    os.replace(staging_path, artifact_path)
    try:
        next_link.symlink_to(artifact_path.name, target_is_directory=True)
        os.replace(next_link, output_path)
    except BaseException:
        if next_link.is_symlink():
            next_link.unlink()
        if artifact_path.exists():
            shutil.rmtree(artifact_path)
        raise
    if (
        previous_artifact is not None
        and previous_artifact.parent == output_path.parent
        and previous_artifact.name.startswith(f".{output_path.name}.artifact-")
    ):
        shutil.rmtree(previous_artifact)


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, JsonValue]],
) -> dict[str, JsonValue]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate JSON object keys are not permitted")
    return value


def _object_value(value: JsonValue, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


__all__ = [
    "CatalogueSite",
    "SiteBuildError",
]
