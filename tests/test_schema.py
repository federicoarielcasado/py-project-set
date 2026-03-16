"""Tests de validación del schema JSON y del perfil IRAM.

Sprint 0: valida que schema.json es un JSON Schema válido y que
iram_general.json cumple con el schema definido.
"""
import json

import jsonschema
import jsonschema.validators
import pytest

from tests.conftest import STANDARDS_DIR


class TestSchemaValidity:
    """El schema.json debe ser un JSON Schema 2020-12 válido."""

    def test_schema_loads_as_json(self):
        path = STANDARDS_DIR / "schema.json"
        assert path.exists(), "schema.json no encontrado"
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_schema_has_required_meta_fields(self, schema):
        assert "$schema" in schema
        assert "title" in schema
        assert "type" in schema
        assert schema["type"] == "object"

    def test_schema_defines_all_top_level_sections(self, schema):
        expected = {
            "metadata", "units", "layers", "linetypes",
            "text_styles", "dim_styles", "drawing_scales",
            "paper_sizes", "title_block", "hatch_patterns", "plot_config",
        }
        defined = set(schema.get("properties", {}).keys())
        missing = expected - defined
        assert not missing, f"Secciones faltantes en schema: {missing}"

    def test_schema_required_matches_properties(self, schema):
        required = set(schema.get("required", []))
        properties = set(schema.get("properties", {}).keys())
        undefined_required = required - properties
        assert not undefined_required, f"Required sin definición en properties: {undefined_required}"


class TestIRAMProfileAgainstSchema:
    """El perfil iram_general.json debe validar contra schema.json."""

    def test_iram_profile_loads_as_json(self):
        path = STANDARDS_DIR / "iram_general.json"
        assert path.exists(), "iram_general.json no encontrado"
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_iram_profile_validates_against_schema(self, schema, iram_profile):
        """Validación completa del perfil IRAM contra el schema."""
        try:
            jsonschema.validate(instance=iram_profile, schema=schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"iram_general.json no cumple el schema:\n{e.message}\nPath: {list(e.absolute_path)}")

    def test_iram_metadata_fields(self, iram_profile):
        meta = iram_profile.get("metadata", {})
        assert meta.get("standard_name") == "IRAM"
        assert meta.get("country") == "AR"
        assert "autocad" in meta.get("software_targets", [])

    def test_iram_has_minimum_layers(self, iram_profile):
        layers = iram_profile.get("layers", [])
        assert len(layers) >= 8, f"Se esperan al menos 8 capas IRAM, hay {len(layers)}"

    def test_iram_layer_names_are_unique(self, iram_profile):
        names = [l["name"] for l in iram_profile.get("layers", [])]
        assert len(names) == len(set(names)), "Hay capas con nombres duplicados"

    def test_iram_has_normalized_scales(self, iram_profile):
        scales = {s["label"] for s in iram_profile.get("drawing_scales", [])}
        required_scales = {"1:1", "1:10", "1:50", "1:100"}
        missing = required_scales - scales
        assert not missing, f"Escalas IRAM faltantes: {missing}"

    def test_iram_has_all_paper_formats(self, iram_profile):
        sizes = {p["name"] for p in iram_profile.get("paper_sizes", [])}
        required = {"A0", "A1", "A2", "A3", "A4"}
        missing = required - sizes
        assert not missing, f"Formatos de papel faltantes: {missing}"

    def test_iram_title_block_has_required_fields(self, iram_profile):
        fields = {f["id"] for f in iram_profile.get("title_block", {}).get("fields", [])}
        required_fields = {"title", "drawing_no", "scale", "date", "drawn_by", "revision", "sheet"}
        missing = required_fields - fields
        assert not missing, f"Campos de rótulo faltantes: {missing}"

    def test_units_are_metric(self, iram_profile):
        units = iram_profile.get("units", {})
        assert units.get("system") == "metric"
        assert units.get("linear_unit") == "mm"
