"""Validate the committed data catalog for internal consistency.

Runs in CI without pipeline parquet files (those are gitignored). Catches:

- Malformed JSONL lines in ``catalog.jsonl``
- Missing or duplicate metadata / layer entries
- Lineage edges referencing unknown dataset IDs
- ``descriptions.yml`` entries for datasets not present in the catalog
- ``descriptions.yml`` field descriptions for columns that do not exist

For full drift detection (forgotten regeneration after schema/component
changes), run ``uv run python scripts/generate_catalog.py`` locally with
pipeline data present and commit the updated ``catalog.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO_ROOT / "data" / "catalog" / "catalog.jsonl"
DEFAULT_DESCRIPTIONS = REPO_ROOT / "data" / "catalog" / "descriptions.yml"

REQUIRED_LAYERS = {"bronze", "silver", "gold", "platinum"}
VALID_ENTRY_TYPES = {"metadata", "layer", "dataset", "edge"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Path to catalog.jsonl")
    parser.add_argument(
        "--descriptions",
        default=str(DEFAULT_DESCRIPTIONS),
        help="Path to descriptions.yml",
    )
    return parser.parse_args()


def _load_catalog(path: Path) -> tuple[list[dict], list[str]]:
    """Return (entries, errors). Each entry is the parsed JSON dict."""
    entries: list[dict] = []
    errors: list[str] = []
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(f"catalog.jsonl:{lineno}: invalid JSON ({exc})")
            continue
        if not isinstance(entry, dict):
            errors.append(f"catalog.jsonl:{lineno}: entry is not an object")
            continue
        entries.append(entry)
    return entries, errors


def _load_descriptions(path: Path) -> tuple[dict, list[str]]:
    """Return (desc_data, errors)."""
    errors: list[str] = []
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        return {}, [f"descriptions.yml: invalid YAML ({exc})"]
    if not isinstance(data, dict):
        return {}, ["descriptions.yml: top-level must be a mapping"]
    return data, errors


def validate() -> int:
    args = parse_args()
    catalog_path = Path(args.catalog)
    desc_path = Path(args.descriptions)
    errors: list[str] = []

    if not catalog_path.exists():
        print(f"✗ catalog.jsonl not found: {catalog_path}")
        print("  Run `uv run python scripts/generate_catalog.py` and commit the output.")
        return 1
    if not desc_path.exists():
        print(f"✗ descriptions.yml not found: {desc_path}")
        return 1

    entries, load_errors = _load_catalog(catalog_path)
    errors.extend(load_errors)

    # Partition entries by type.
    metadata: list[dict] = []
    layers: dict[str, dict] = {}
    datasets: dict[str, dict] = {}
    edges: list[dict] = []

    for entry in entries:
        etype = entry.get("type")
        if etype not in VALID_ENTRY_TYPES:
            errors.append(f"catalog entry has invalid type {etype!r}: {entry.get('id', '?')}")
            continue
        if etype == "metadata":
            metadata.append(entry)
        elif etype == "layer":
            lid = entry.get("id")
            if not lid:
                errors.append("layer entry missing 'id'")
                continue
            if lid in layers:
                errors.append(f"layer {lid!r} declared more than once")
                continue
            layers[lid] = entry
        elif etype == "dataset":
            did = entry.get("id")
            if not did:
                errors.append("dataset entry missing 'id'")
                continue
            if did in datasets:
                errors.append(f"dataset {did!r} declared more than once")
                continue
            datasets[did] = entry
        elif etype == "edge":
            edges.append(entry)

    # Metadata: exactly one.
    if len(metadata) == 0:
        errors.append("no metadata entry in catalog")
    elif len(metadata) > 1:
        errors.append(f"expected 1 metadata entry, found {len(metadata)}")

    # Layers: all required layers present.
    missing_layers = REQUIRED_LAYERS - set(layers)
    if missing_layers:
        errors.append(f"missing required layers: {sorted(missing_layers)}")
    for lid, layer in layers.items():
        for field in ("label", "description", "dataset_count"):
            if not layer.get(field):
                errors.append(f"layer {lid!r} missing field {field!r}")

    # Edges: every endpoint must reference a known dataset.
    for idx, edge in enumerate(edges):
        for endpoint in ("from", "to"):
            ref = edge.get(endpoint)
            if not ref:
                errors.append(f"edge[{idx}] missing '{endpoint}'")
            elif ref not in datasets:
                errors.append(f"edge[{idx}].{endpoint} references unknown dataset {ref!r}")

    # Cross-check descriptions.yml.
    desc_data, desc_errors = _load_descriptions(desc_path)
    errors.extend(desc_errors)

    if desc_data:
        shared_fields = set(desc_data.get("shared_fields", {}) or {})
        desc_datasets = desc_data.get("datasets", {}) or {}

        # Every described dataset must exist in the catalog.
        for ds_id in desc_datasets:
            if ds_id not in datasets:
                errors.append(f"descriptions.yml: dataset {ds_id!r} not present in catalog")

        # Every described field must exist as a column OR be a shared field.
        # (We cannot fully verify shared_fields coverage here — some are
        # intentionally defined ahead of new datasets.)
        for ds_id, ds_desc in desc_datasets.items():
            ds_entry = datasets.get(ds_id)
            if ds_entry is None or not isinstance(ds_desc, dict):
                continue
            parquet = ds_entry.get("parquet") or {}
            real_cols = set((parquet.get("columns") or {}).keys())
            schema = ds_entry.get("schema") or {}
            real_cols |= set((schema.get("fields") or {}).keys())

            # If the dataset has no columns (parquet missing / not yet
            # materialised), there is nothing to validate field descriptions
            # against — skip rather than flag every described column.
            if not real_cols:
                continue

            specific_fields = ds_desc.get("fields", {}) or {}
            for field_name in specific_fields:
                # A field description is valid if the column exists in this
                # dataset OR the field is defined in shared_fields (the
                # generator falls back to shared_fields).
                if field_name in real_cols or field_name in shared_fields:
                    continue
                errors.append(
                    f"descriptions.yml: dataset {ds_id!r} describes column "
                    f"{field_name!r} which does not exist (not in parquet, "
                    f"schema, or shared_fields)"
                )

    if errors:
        print(f"✗ Catalog validation failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"✓ Catalog valid: {len(layers)} layers, {len(datasets)} datasets, {len(edges)} edges.")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
