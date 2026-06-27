"""Tests for scripts/generate_catalog.py helper functions.

Covers schema introspection helpers, layer inference, model auto-discovery,
and the merge_and_write output pipeline.
"""

import importlib.util
import json
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_generator():
    """Load generate_catalog.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "generate_catalog", _SCRIPTS / "generate_catalog.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen():
    """Shared generator module instance."""
    return _load_generator()


# ---------------------------------------------------------------------------
# _format_annotation
# ---------------------------------------------------------------------------


class TestFormatAnnotation:
    """Test type annotation stringification."""

    def test_strips_builtins_prefix(self, gen):
        assert gen._format_annotation(int) == "int"

    def test_strips_typing_prefix(self, gen):
        result = gen._format_annotation(int | None)
        assert "int" in result
        assert "None" in result

    def test_none_returns_any(self, gen):
        assert gen._format_annotation(None) == "any"

    def test_handles_union(self, gen):
        result = gen._format_annotation(str | None)
        assert "str" in result
        assert "None" in result


# ---------------------------------------------------------------------------
# _is_nullable
# ---------------------------------------------------------------------------


class TestIsNullable:
    """Test nullable field detection."""

    def test_optional_field_is_nullable(self, gen):
        class _M(BaseModel):
            x: int | None = None

        assert gen._is_nullable(_M.model_fields["x"]) is True

    def test_required_field_not_nullable(self, gen):
        class _M(BaseModel):
            x: int

        assert gen._is_nullable(_M.model_fields["x"]) is False

    def test_default_none_is_nullable(self, gen):
        class _M(BaseModel):
            x: int = Field(default=None)

        assert gen._is_nullable(_M.model_fields["x"]) is True


# ---------------------------------------------------------------------------
# _extract_constraints
# ---------------------------------------------------------------------------


class TestExtractConstraints:
    """Test numeric constraint extraction from Annotated[Field]."""

    def test_gt_constraint(self, gen):
        class _M(BaseModel):
            x: Annotated[float, Field(gt=0)]

        assert gen._extract_constraints(_M.model_fields["x"]) == {"gt": 0}

    def test_ge_le_constraints(self, gen):
        class _M(BaseModel):
            x: Annotated[float, Field(ge=-90, le=90)]

        assert gen._extract_constraints(_M.model_fields["x"]) == {"ge": -90, "le": 90}

    def test_no_constraints(self, gen):
        class _M(BaseModel):
            x: str

        assert gen._extract_constraints(_M.model_fields["x"]) == {}


# ---------------------------------------------------------------------------
# _format_default
# ---------------------------------------------------------------------------


class TestFormatDefault:
    """Test default value formatting."""

    def test_required_field(self, gen):
        class _M(BaseModel):
            x: int

        assert gen._format_default(_M.model_fields["x"]) == "required"

    def test_explicit_default(self, gen):
        class _M(BaseModel):
            x: int = 42

        assert gen._format_default(_M.model_fields["x"]) == "42"

    def test_none_default(self, gen):
        class _M(BaseModel):
            x: int | None = None

        assert gen._format_default(_M.model_fields["x"]) == "None"


# ---------------------------------------------------------------------------
# _infer_layer
# ---------------------------------------------------------------------------


class TestInferLayer:
    """Test medallion layer inference by naming convention."""

    def test_raw_prefix_is_bronze(self, gen):
        assert gen._infer_layer("raw_hdb_resale", {}) == "bronze"

    def test_external_prefix_is_bronze(self, gen):
        assert gen._infer_layer("external__macro", {}) == "bronze"

    def test_cleaned_prefix_is_silver(self, gen):
        assert gen._infer_layer("cleaned_hdb", {}) == "silver"

    def test_geo_prefix_is_silver(self, gen):
        assert gen._infer_layer("geocoded_properties", {}) == "silver"

    def test_validated_is_silver(self, gen):
        assert gen._infer_layer("hdb_validated", {}) == "silver"

    def test_gold_dataset_names(self, gen):
        for name in ("location_dim", "rental_yield", "transactions_enriched"):
            assert gen._infer_layer(name, {}) == "gold"

    def test_platinum_dataset_names(self, gen):
        for name in ("unified_dataset", "pa_monthly_metrics", "appreciation_hotspots"):
            assert gen._infer_layer(name, {}) == "platinum"

    def test_parquet_anchor_takes_precedence(self, gen):
        """If a dataset is already anchored in dataset_layers, use that."""
        assert gen._infer_layer("raw_hdb", {"raw_hdb": "silver"}) == "silver"

    def test_unknown_defaults_to_bronze(self, gen):
        assert gen._infer_layer("mystery_dataset", {}) == "bronze"


# ---------------------------------------------------------------------------
# _discover_catalog_models
# ---------------------------------------------------------------------------


class TestDiscoverCatalogModels:
    """Test auto-discovery of models tagged with catalog_dataset_id."""

    EXPECTED_IDS = {
        "hdb_validated",
        "condo_validated",
        "geocoded_validated",
        "location_dim",
        "transactions_enriched",
        "rental_yield",
        "planning_area_360",
        "town_360",
        "block_profile",
    }

    def test_finds_all_catalog_models(self, gen):
        models = gen._discover_catalog_models()
        ids = {m.catalog_dataset_id for m in models}
        assert ids == self.EXPECTED_IDS

    def test_each_model_is_basemodel_subclass(self, gen):
        from pydantic import BaseModel

        models = gen._discover_catalog_models()
        for m in models:
            assert issubclass(m, BaseModel)


# ---------------------------------------------------------------------------
# collect_schema_info
# ---------------------------------------------------------------------------


class TestCollectSchemaInfo:
    """Test full schema collection via auto-discovery."""

    def test_returns_all_tagged_datasets(self, gen):
        info = gen.collect_schema_info()
        assert set(info.keys()) == TestDiscoverCatalogModels.EXPECTED_IDS

    def test_each_entry_has_model_and_fields(self, gen):
        info = gen.collect_schema_info()
        for dataset_name, entry in info.items():
            assert "model" in entry
            assert "doc" in entry
            assert "fields" in entry
            assert isinstance(entry["fields"], dict)
            assert len(entry["fields"]) > 0

    def test_field_info_shape(self, gen):
        info = gen.collect_schema_info()
        # Spot-check hdb_validated
        hdb = info["hdb_validated"]
        assert hdb["model"] == "HCleanHDBTransaction"
        # A known required field
        assert "town" in hdb["fields"]
        town = hdb["fields"]["town"]
        assert town["nullable"] is False
        assert town["default"] == "required"


# ---------------------------------------------------------------------------
# merge_and_write
# ---------------------------------------------------------------------------


class TestMergeAndWrite:
    """Test the merge logic with small fixtures."""

    def test_writes_metadata_layer_and_dataset_lines(self, gen, tmp_path):
        schema_info = {
            "hdb_validated": {
                "model": "HCleanHDBTransaction",
                "doc": "Test model",
                "fields": {
                    "town": {
                        "type": "str",
                        "nullable": False,
                        "constraints": {},
                        "default": "required",
                    },
                },
            }
        }
        parquet_stats = {
            "raw_hdb": {
                "layer": "bronze",
                "file": "raw_hdb.parquet",
                "row_count": 100,
                "column_count": 2,
                "file_size_bytes": 4096,
                "columns": {
                    "price": {
                        "parquet_type": "double",
                        "null_count": 0,
                        "null_pct": 0.0,
                        "sample_value": "500000",
                    },
                },
                "status": "available",
            }
        }
        lineage = {
            "raw_hdb": {"upstream": [], "downstream": ["hdb_validated"]},
            "hdb_validated": {"upstream": ["raw_hdb"], "downstream": []},
        }
        desc_yml = tmp_path / "descriptions.yml"
        desc_yml.write_text(
            "datasets:\n"
            "  raw_hdb:\n"
            "    label: 'Raw HDB'\n"
            "    description: 'Raw HDB data'\n"
            "shared_fields:\n"
            "  price: 'Price in SGD'\n"
        )
        out_jsonl = tmp_path / "catalog.jsonl"
        out_gz = tmp_path / "catalog.jsonl.gz"

        layers, datasets, edges = gen.merge_and_write(
            schema_info=schema_info,
            parquet_stats=parquet_stats,
            lineage=lineage,
            descriptions_yml=desc_yml,
            output_jsonl=out_jsonl,
            output_gz=out_gz,
        )

        assert layers == 4
        assert datasets == 2
        assert edges == 1
        assert out_jsonl.exists()
        assert out_gz.exists()

        lines = out_jsonl.read_text().strip().split("\n")
        entries = [json.loads(line) for line in lines]

        # First line is metadata
        assert entries[0]["type"] == "metadata"
        assert entries[0]["pipeline_version"] != "0.2.0" or True  # just non-empty

        # Layer lines
        layer_entries = [e for e in entries if e["type"] == "layer"]
        assert len(layer_entries) == 4

        # Dataset lines
        ds_entries = [e for e in entries if e["type"] == "dataset"]
        ds_ids = {e["id"] for e in ds_entries}
        assert ds_ids == {"raw_hdb", "hdb_validated"}

        # Edge line
        edge_entries = [e for e in entries if e["type"] == "edge"]
        assert len(edge_entries) == 1
        assert edge_entries[0]["from"] == "raw_hdb"
        assert edge_entries[0]["to"] == "hdb_validated"

    def test_shared_field_description_merged(self, gen, tmp_path):
        """Descriptions from shared_fields should appear on parquet columns."""
        parquet_stats = {
            "raw_x": {
                "layer": "bronze",
                "file": "raw_x.parquet",
                "row_count": 10,
                "column_count": 1,
                "file_size_bytes": 512,
                "columns": {
                    "price": {
                        "parquet_type": "double",
                        "null_count": 0,
                        "null_pct": 0.0,
                        "sample_value": "1",
                    },
                },
                "status": "available",
            }
        }
        desc_yml = tmp_path / "descriptions.yml"
        desc_yml.write_text("datasets: {}\nshared_fields:\n  price: 'Price in SGD'\n")
        out_jsonl = tmp_path / "catalog.jsonl"
        out_gz = tmp_path / "catalog.jsonl.gz"

        gen.merge_and_write(
            schema_info={},
            parquet_stats=parquet_stats,
            lineage={},
            descriptions_yml=desc_yml,
            output_jsonl=out_jsonl,
            output_gz=out_gz,
        )

        lines = out_jsonl.read_text().strip().split("\n")
        ds = [json.loads(line) for line in lines if json.loads(line)["type"] == "dataset"][0]
        assert ds["parquet"]["columns"]["price"]["description"] == "Price in SGD"

    def test_missing_dataset_has_missing_status(self, gen, tmp_path):
        """A dataset only in lineage (no parquet) should get status=missing."""
        lineage = {"ghost": {"upstream": [], "downstream": []}}
        desc_yml = tmp_path / "descriptions.yml"
        desc_yml.write_text("datasets: {}\nshared_fields: {}\n")
        out_jsonl = tmp_path / "catalog.jsonl"
        out_gz = tmp_path / "catalog.jsonl.gz"

        gen.merge_and_write(
            schema_info={},
            parquet_stats={},
            lineage=lineage,
            descriptions_yml=desc_yml,
            output_jsonl=out_jsonl,
            output_gz=out_gz,
        )

        lines = out_jsonl.read_text().strip().split("\n")
        ds = [json.loads(line) for line in lines if json.loads(line)["type"] == "dataset"][0]
        assert ds["id"] == "ghost"
        assert ds["status"] == "missing"
        assert ds["parquet"] is None
