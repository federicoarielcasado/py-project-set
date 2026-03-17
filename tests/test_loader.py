"""Tests del módulo loader — Sprint 1.

Cubre:
  - Carga exitosa del perfil IRAM incluido en el paquete
  - Validación contra schema.json
  - Errores tipificados: archivo inexistente, JSON inválido,
    schema inválido, validación Pydantic fallida
"""
import json
import tempfile
from pathlib import Path

import pytest

from cadnorm.core.loader import (
    ProfileParseError,
    SchemaValidationError,
    load_builtin_profile,
    load_profile,
    load_schema,
)
from cadnorm.core.models import NormProfile


class TestLoadBuiltinProfile:
    def test_loads_iram_successfully(self):
        profile = load_builtin_profile("iram_general")
        assert isinstance(profile, NormProfile)
        assert profile.name == "IRAM"

    def test_iram_has_correct_units(self):
        profile = load_builtin_profile("iram_general")
        assert profile.units.system == "metric"
        assert profile.units.linear_unit == "mm"

    def test_iram_layers_count(self):
        profile = load_builtin_profile("iram_general")
        assert len(profile.layers) == 12

    def test_iram_linetypes_count(self):
        profile = load_builtin_profile("iram_general")
        assert len(profile.linetypes) == 5

    def test_iram_text_styles_count(self):
        profile = load_builtin_profile("iram_general")
        # IRAM 4503 Tabla I: 7 alturas normalizadas (2.5, 3.5, 5, 7, 10, 14 mm + STD variable)
        assert len(profile.text_styles) == 7

    def test_iram_paper_sizes_count(self):
        profile = load_builtin_profile("iram_general")
        assert len(profile.paper_sizes) == 6

    def test_iram_scales_count(self):
        profile = load_builtin_profile("iram_general")
        # IRAM 4505 Tabla I: 1 natural + 14 reducción + 3 ampliación = 18
        assert len(profile.drawing_scales) == 18

    def test_iram_title_block_required_fields(self):
        profile = load_builtin_profile("iram_general")
        required_ids = {"title", "drawing_no", "scale", "date", "drawn_by", "revision", "sheet"}
        field_ids = {f.id for f in profile.title_block.fields}
        assert required_ids <= field_ids

    def test_iram_default_text_style_is_iram_std(self):
        profile = load_builtin_profile("iram_general")
        assert profile.default_text_style().name == "IRAM_STD"

    def test_iram_default_dim_style_is_iram_standard(self):
        profile = load_builtin_profile("iram_general")
        assert profile.default_dim_style().name == "IRAM_STANDARD"

    def test_nonexistent_norm_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="INEXISTENTE"):
            load_builtin_profile("INEXISTENTE")


class TestLoadProfileFromPath:
    def test_load_from_absolute_path(self):
        from cadnorm.core.loader import STANDARDS_DIR
        path = STANDARDS_DIR / "iram_general.json"
        profile = load_profile(path)
        assert isinstance(profile, NormProfile)

    def test_load_without_schema_validation(self):
        from cadnorm.core.loader import STANDARDS_DIR
        path = STANDARDS_DIR / "iram_general.json"
        profile = load_profile(path, validate_schema=False)
        assert profile.name == "IRAM"

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_profile(Path("/ruta/que/no/existe.json"))

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            f.write("{ esto no es json válido")
            tmp_path = Path(f.name)
        try:
            with pytest.raises(json.JSONDecodeError):
                load_profile(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_schema_violation_raises_schema_error(self):
        """Un JSON válido pero que viola el schema debe lanzar SchemaValidationError."""
        bad_data = {"metadata": {"standard_name": "X"}}  # incompleto
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(bad_data, f)
            tmp_path = Path(f.name)
        try:
            with pytest.raises(SchemaValidationError):
                load_profile(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_pydantic_error_raises_parse_error(self, iram_profile):
        """JSON que pasa schema pero tiene valor Pydantic inválido debe lanzar ProfileParseError."""
        bad_data = dict(iram_profile)
        bad_data["units"] = dict(iram_profile["units"])
        bad_data["units"]["system"] = "SISTEMA_INVALIDO"

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(bad_data, f, ensure_ascii=False)
            tmp_path = Path(f.name)
        try:
            with pytest.raises(ProfileParseError):
                load_profile(tmp_path, validate_schema=False)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestLoadSchema:
    def test_returns_dict(self):
        schema = load_schema()
        assert isinstance(schema, dict)

    def test_has_top_level_sections(self):
        schema = load_schema()
        sections = set(schema.get("properties", {}).keys())
        assert "layers" in sections
        assert "metadata" in sections

    def test_schema_error_has_path_info(self):
        """SchemaValidationError debe exponer el path del archivo."""
        bad_data = {"incomplete": True}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(bad_data, f)
            tmp_path = Path(f.name)
        try:
            with pytest.raises(SchemaValidationError) as exc_info:
                load_profile(tmp_path)
            assert exc_info.value.path == tmp_path
        finally:
            tmp_path.unlink(missing_ok=True)
