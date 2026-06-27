"""Generate the data catalog JSONL file from Pydantic schemas, parquet stats,
and Hamilton DAG lineage.

Usage:
    uv run python scripts/generate_catalog.py              # from project root
    dotenvx run -- uv run python scripts/generate_catalog.py
"""

import gzip
import json
import sys
from datetime import UTC, datetime
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    PIPELINE_VERSION = _pkg_version("egg-n-bacon-housing")
except Exception:
    PIPELINE_VERSION = "unknown"


# ---------------------------------------------------------------------------
# Model discovery via catalog_dataset_id class attribute
# ---------------------------------------------------------------------------

# Runtime inputs that are injected, not produced by DAG nodes
_RUNTIME_INPUTS: set[str] = {
    "bronze_dir",
    "silver_dir",
    "gold_dir",
    "writer",
    "geocoder",
    "min_coordinate_coverage",
    "median_household_income",
    "affordability_thresholds",
}

# Layer directory names
LAYER_DIRS: dict[str, str] = {
    "bronze": "01_bronze",
    "silver": "02_silver",
    "gold": "03_gold",
    "platinum": "04_platinum",
}


# ===================================================================
# 1. Pydantic schema introspection
# ===================================================================


def _format_annotation(annotation: Any) -> str:
    """Stringify a type annotation, stripping module prefixes."""
    if annotation is None:
        return "any"
    raw = str(annotation)
    # Remove <class '...'> wrappers
    raw = raw.replace("<class '", "").replace("'>", "")
    # Remove common module prefixes for readability
    for prefix in ("builtins.", "datetime.", "typing."):
        raw = raw.replace(prefix, "")
    return raw


def _is_nullable(field: Any) -> bool:
    """Determine if a Pydantic field is nullable (| None or default=None)."""
    ann_str = _format_annotation(field.annotation)
    if "None" in ann_str or "NoneType" in ann_str:
        return True
    if field.default is None:
        return True
    return False


def _extract_constraints(field: Any) -> dict[str, float]:
    """Extract numeric constraints (gt, ge, lt, le) from a Field in Annotated."""
    constraints: dict[str, float] = {}
    metadata = getattr(field, "metadata", [])
    for item in metadata:
        if hasattr(item, "gt") and item.gt is not None:
            constraints["gt"] = item.gt
        if hasattr(item, "ge") and item.ge is not None:
            constraints["ge"] = item.ge
        if hasattr(item, "lt") and item.lt is not None:
            constraints["lt"] = item.lt
        if hasattr(item, "le") and item.le is not None:
            constraints["le"] = item.le
    return constraints


def _format_default(field: Any) -> str:
    """Return a human-readable default value string."""
    from pydantic.fields import FieldInfo

    if field.is_required():
        return "required"
    if field.default is not None and not isinstance(field.default, FieldInfo):
        return str(field.default)
    return "None"


def _discover_catalog_models() -> list[type]:
    """Recursively find all Pydantic models tagged with ``catalog_dataset_id``.

    Imports the schema modules first so their classes are registered on
    ``BaseModel.__subclasses__()`` before traversal.
    """
    from pydantic import BaseModel

    # Ensure schema modules are imported so their classes are discoverable
    from egg_n_bacon_housing.schemas import clean_models, feature_models  # noqa: F401

    discovered: list[type[BaseModel]] = []

    def _walk(cls: type) -> None:
        if hasattr(cls, "catalog_dataset_id"):
            discovered.append(cls)
        for sub in cls.__subclasses__():
            _walk(sub)

    _walk(BaseModel)
    return discovered


def collect_schema_info() -> dict[str, dict]:
    """Extract field metadata from all Pydantic models tagged with
    ``catalog_dataset_id``.

    Returns dict keyed by dataset name, each with model name, docstring, and per-field info.
    """
    models = _discover_catalog_models()

    result: dict[str, dict] = {}
    for model_cls in models:
        dataset_name = model_cls.catalog_dataset_id

        fields: dict[str, dict] = {}
        for field_name, field_info in model_cls.model_fields.items():
            fields[field_name] = {
                "type": _format_annotation(field_info.annotation),
                "nullable": _is_nullable(field_info),
                "constraints": _extract_constraints(field_info),
                "default": _format_default(field_info),
            }

        result[dataset_name] = {
            "model": model_cls.__name__,
            "doc": (model_cls.__doc__ or "").strip(),
            "fields": fields,
        }

    return result


# ===================================================================
# 2. Parquet file scanning
# ===================================================================


def collect_parquet_stats(pipeline_dir: Path) -> dict[str, dict]:
    """Scan parquet files for row counts, column stats, and sample values.

    Returns dict keyed by dataset name (parquet stem), each containing file
    metadata and per-column statistics.
    """
    import pyarrow.parquet as pq

    result: dict[str, dict] = {}

    for layer, dir_name in LAYER_DIRS.items():
        layer_path = pipeline_dir / dir_name
        if not layer_path.exists():
            continue

        # Main parquet files
        for pq_file in sorted(layer_path.glob("*.parquet")):
            dataset_name = pq_file.stem
            _accumulate_parquet_stats(result, dataset_name, layer, pq_file, pq)

        # External sub-directory (bronze/external — macro parquets)
        external_path = layer_path / "external"
        if external_path.is_dir():
            for pq_file in sorted(external_path.glob("*.parquet")):
                dataset_name = f"external__{pq_file.stem}"
                _accumulate_parquet_stats(result, dataset_name, layer, pq_file, pq)

    return result


def _accumulate_parquet_stats(
    result: dict,
    dataset_name: str,
    layer: str,
    pq_file: Path,
    pq: Any,
) -> None:
    """Helper: read one parquet file into the result dict."""
    try:
        pf = pq.read_metadata(pq_file)
        schema = pq.read_schema(pq_file)

        columns: dict[str, dict] = {}
        for i in range(pf.num_columns):
            field = schema.field(i)
            col_name = field.name
            col_data: dict[str, Any] = {
                "parquet_type": str(field.type),
            }
            # Null count from row-group statistics
            null_count = 0
            for rg_idx in range(pf.num_row_groups):
                rg = pf.row_group(rg_idx)
                col_meta = rg.column(i)
                if col_meta.statistics and col_meta.statistics.null_count is not None:
                    null_count += col_meta.statistics.null_count
            col_data["null_count"] = null_count
            col_data["null_pct"] = (
                round(null_count / pf.num_rows * 100, 2) if pf.num_rows > 0 else None
            )
            columns[col_name] = col_data

        # Read 5 rows for sample values
        try:
            import pandas as pd

            sample_df = pd.read_parquet(pq_file, nrows=5)
            for col_name in columns:
                if col_name in sample_df.columns:
                    non_null = sample_df[col_name].dropna()
                    if len(non_null) > 0:
                        val = non_null.iloc[0]
                        if isinstance(val, pd.Timestamp | datetime):
                            val = val.isoformat()
                        columns[col_name]["sample_value"] = str(val)
                    else:
                        columns[col_name]["sample_value"] = None
        except Exception:
            pass  # Sample values are best-effort

        result[dataset_name] = {
            "layer": layer,
            "file": pq_file.name,
            "row_count": pf.num_rows,
            "column_count": pf.num_columns,
            "file_size_bytes": pq_file.stat().st_size,
            "columns": columns,
            "status": "available",
        }
    except Exception as exc:
        result[dataset_name] = {
            "layer": layer,
            "file": pq_file.name,
            "status": "error",
            "error": str(exc),
        }


# ===================================================================
# 3. Hamilton DAG lineage extraction
# ===================================================================


def collect_lineage() -> dict[str, dict]:
    """Extract upstream/downstream lineage for every DAG node.

    Builds the Hamilton driver without executing the pipeline.
    Runtime inputs (bronze_dir, writer, geocoder, etc.) are filtered out.
    """
    from hamilton import driver  # type: ignore[import-untyped]

    from egg_n_bacon_housing.pipeline import _STAGE_MODULES

    dr = (
        driver.Builder()
        .with_modules(*_STAGE_MODULES)
        .with_config({"data_path": str(ROOT / "data")})
        .build()
    )

    all_vars = [v.name for v in dr.list_available_variables()]
    lineage: dict[str, dict] = {}

    for var_name in all_vars:
        if var_name in _RUNTIME_INPUTS:
            continue
        upstream = [n.name for n in dr.what_is_upstream_of(var_name)]
        downstream = [n.name for n in dr.what_is_downstream_of(var_name)]
        # Filter runtime inputs from upstream/downstream
        upstream = [u for u in upstream if u not in _RUNTIME_INPUTS]
        downstream = [d for d in downstream if d not in _RUNTIME_INPUTS]
        lineage[var_name] = {
            "upstream": upstream,
            "downstream": downstream,
        }

    return lineage


# ===================================================================
# 4. Merge & write
# ===================================================================


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# Known gold-tier dataset names without a parquet file to anchor them.
_GOLD_DATASET_NAMES = frozenset(
    {
        "location_dim",
        "rental_yield",
        "transactions_enriched",
        "planning_area_360",
        "town_360",
        "block_profile",
    }
)

# Known platinum-tier dataset names.
_PLATINUM_DATASET_NAMES = frozenset(
    {
        "unified_dataset",
        "pa_monthly_metrics",
        "appreciation_hotspots",
    }
)


def _infer_layer(name: str, dataset_layers: dict[str, str]) -> str:
    """Infer the medallion layer for a dataset by naming convention.

    ``dataset_layers`` maps dataset names already anchored to a layer via
    their parquet file location; it is checked first.
    """
    if name in dataset_layers:
        return dataset_layers[name]
    if name.startswith("raw_") or name.startswith("external__"):
        return "bronze"
    if name.startswith("cleaned_") or name.startswith("geo"):
        return "silver"
    if "validated" in name:
        return "silver"
    if name in _GOLD_DATASET_NAMES:
        return "gold"
    if name in _PLATINUM_DATASET_NAMES:
        return "platinum"
    return "bronze"


def merge_and_write(
    schema_info: dict[str, dict],
    parquet_stats: dict[str, dict],
    lineage: dict[str, dict],
    descriptions_yml: Path,
    output_jsonl: Path,
    output_gz: Path,
) -> tuple[int, int, int]:
    """Merge all sources and write JSONL + gzipped output.

    Returns (layer_count, dataset_count, edge_count).
    """
    # Load descriptions YAML
    with open(descriptions_yml) as fh:
        desc_data = yaml.safe_load(fh) or {}

    dataset_descs: dict[str, dict] = desc_data.get("datasets", {})
    shared_fields: dict[str, str] = desc_data.get("shared_fields", {})

    # Build the full dataset catalog
    all_dataset_names: set[str] = set()
    all_dataset_names.update(schema_info.keys())
    all_dataset_names.update(parquet_stats.keys())
    all_dataset_names.update(lineage.keys())
    # Also include any referenced in descriptions.yml
    all_dataset_names.update(dataset_descs.keys())

    # Determine layer for each dataset
    dataset_layers: dict[str, str] = {}
    for name, stats in parquet_stats.items():
        if name not in dataset_layers and "layer" in stats:
            dataset_layers[name] = stats["layer"]

    # Layers we know about
    known_layers = ["bronze", "silver", "gold", "platinum"]
    layer_labels = {
        "bronze": "Bronze (Raw)",
        "silver": "Silver (Cleaned)",
        "gold": "Gold (Features)",
        "platinum": "Platinum (Unified)",
    }
    layer_descriptions = {
        "bronze": "Immutable raw data from APIs, CSVs, and GeoJSON files",
        "silver": "Validated, cleaned data with schema enforcement",
        "gold": "Feature-enriched data with spatial and macro features",
        "platinum": "Predictions, unified exports, and aggregate metrics",
    }

    # Assign layers: inferred from parquet location, then by naming convention
    for name in list(all_dataset_names):
        if name not in dataset_layers:
            dataset_layers[name] = _infer_layer(name, dataset_layers)

    # Build output lines
    lines: list[str] = []

    # Metadata line
    lines.append(
        json.dumps(
            {
                "type": "metadata",
                "generated_at": datetime.now(UTC).isoformat(),
                "pipeline_version": PIPELINE_VERSION,
                "generator": "scripts/generate_catalog.py",
            }
        )
    )

    # Layer summary lines
    layer_datasets: dict[str, list[str]] = {layer: [] for layer in known_layers}
    for name in sorted(all_dataset_names):
        layer = dataset_layers.get(name, "bronze")
        if layer in layer_datasets:
            layer_datasets[layer].append(name)

    for layer in known_layers:
        ds_list = layer_datasets[layer]
        total_rows = sum(parquet_stats.get(ds, {}).get("row_count", 0) or 0 for ds in ds_list)
        total_size = sum(parquet_stats.get(ds, {}).get("file_size_bytes", 0) or 0 for ds in ds_list)
        lines.append(
            json.dumps(
                {
                    "type": "layer",
                    "id": layer,
                    "label": layer_labels[layer],
                    "description": layer_descriptions[layer],
                    "dataset_count": len(ds_list),
                    "total_rows": total_rows,
                    "total_size_bytes": total_size,
                }
            )
        )

    # Dataset lines
    dataset_count = 0
    for name in sorted(all_dataset_names):
        dataset_count += 1
        layer = dataset_layers.get(name, "bronze")
        ds_desc = dataset_descs.get(name, {})
        pq_info = parquet_stats.get(name)

        # Build the dataset entry
        entry: dict[str, Any] = {
            "type": "dataset",
            "id": name,
            "layer": layer,
            "label": ds_desc.get("label", name.replace("_", " ").title()),
            "description": ds_desc.get("description", ""),
            "source": ds_desc.get("source"),
        }

        if pq_info:
            entry["status"] = pq_info.get("status", "available")
            entry["parquet"] = {
                "file": pq_info.get("file", ""),
                "row_count": pq_info.get("row_count", 0),
                "column_count": pq_info.get("column_count", 0),
                "file_size_bytes": pq_info.get("file_size_bytes", 0),
                "columns": {},
            }
            # Merge column descriptions from shared_fields + dataset-specific YAML
            specific_fields: dict[str, str] = ds_desc.get("fields", {})
            for col_name, col_stats in pq_info.get("columns", {}).items():
                entry["parquet"]["columns"][col_name] = col_stats  # type: ignore[index]
                # description priority: specific > shared
                desc = specific_fields.get(col_name) or shared_fields.get(col_name)
                if desc:
                    entry["parquet"]["columns"][col_name]["description"] = desc  # type: ignore[index]
        else:
            entry["status"] = "missing"
            entry["parquet"] = None

        # Schema info (from Pydantic)
        si = schema_info.get(name)
        if si:
            entry["schema"] = {
                "model": si["model"],
                "doc": si.get("doc", ""),
                "fields": {},
            }
            specific_fields = ds_desc.get("fields", {})
            for field_name, field_info in si["fields"].items():
                entry["schema"]["fields"][field_name] = dict(field_info)  # type: ignore[index]
                desc = specific_fields.get(field_name) or shared_fields.get(field_name)
                if desc:
                    entry["schema"]["fields"][field_name]["description"] = desc  # type: ignore[index]
        else:
            entry["schema"] = None

        # Lineage
        le = lineage.get(name, {})
        entry["lineage"] = {
            "upstream": le.get("upstream", []),
            "downstream": le.get("downstream", []),
        }

        lines.append(json.dumps(entry))

    # Edge lines (denormalized for graph rendering)
    edge_count = 0
    seen_edges: set[tuple[str, str]] = set()
    for name in sorted(all_dataset_names):
        le = lineage.get(name, {})
        for downstream_name in sorted(le.get("downstream", [])):
            edge = (name, downstream_name)
            if edge not in seen_edges:
                seen_edges.add(edge)
                lines.append(
                    json.dumps(
                        {
                            "type": "edge",
                            "from": name,
                            "to": downstream_name,
                        }
                    )
                )
                edge_count += 1

    # Write JSONL
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.write_text("\n".join(lines) + "\n")

    # Write gzipped
    output_gz.parent.mkdir(parents=True, exist_ok=True)
    compressed = gzip.compress(("\n".join(lines) + "\n").encode("utf-8"))
    output_gz.write_bytes(compressed)

    return len(known_layers), dataset_count, edge_count


# ===================================================================
# Main
# ===================================================================


def main() -> None:
    repo_root = ROOT
    pipeline_dir = repo_root / "data" / "pipeline"
    descriptions_yml = repo_root / "data" / "catalog" / "descriptions.yml"
    output_jsonl = repo_root / "data" / "catalog" / "catalog.jsonl"
    output_gz = repo_root / "app" / "public" / "data" / "catalog.jsonl.gz"

    print("=" * 60)
    print("Data Catalog Generator")
    print("=" * 60)

    # 1. Schema introspection
    print("\n[1/4] Extracting Pydantic schemas...")
    try:
        schema_info = collect_schema_info()
        print(f"  ✓ {len(schema_info)} datasets with Pydantic models")
    except Exception as exc:
        print(f"  ✗ Failed: {exc}")
        schema_info = {}

    # 2. Parquet stats
    print("\n[2/4] Scanning parquet files...")
    try:
        parquet_stats = collect_parquet_stats(pipeline_dir)
        available = sum(1 for v in parquet_stats.values() if v.get("status") == "available")
        missing = sum(1 for v in parquet_stats.values() if v.get("status") != "available")
        print(f"  ✓ {available} available, {missing} missing/errors")
    except Exception as exc:
        print(f"  ✗ Failed: {exc}")
        parquet_stats = {}

    # 3. Lineage
    print("\n[3/4] Extracting Hamilton DAG lineage...")
    try:
        lineage = collect_lineage()
        print(f"  ✓ {len(lineage)} nodes with lineage info")
    except Exception as exc:
        print(f"  ✗ Failed: {exc}")
        lineage = {}

    # 4. Merge & write
    print("\n[4/4] Merging and writing output...")
    if not descriptions_yml.exists():
        print(f"  ✗ Descriptions YAML not found: {descriptions_yml}")
        sys.exit(1)

    layers, datasets, edges = merge_and_write(
        schema_info=schema_info,
        parquet_stats=parquet_stats,
        lineage=lineage,
        descriptions_yml=descriptions_yml,
        output_jsonl=output_jsonl,
        output_gz=output_gz,
    )

    print(f"  ✓ {layers} layers, {datasets} datasets, {edges} lineage edges")
    print(f"\n  JSONL:   {output_jsonl}")
    print(f"  Gzipped: {output_gz}")
    print("\nDone.")


if __name__ == "__main__":
    main()
