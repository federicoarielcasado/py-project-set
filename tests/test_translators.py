"""Tests de integración para los traductores AutoCAD y LibreCAD.

Sprint 2: verifica que los traductores generan archivos DXF/DWT válidos
con todas las capas, tipos de línea, estilos de texto y cotas del perfil IRAM.
"""
from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest

from cadnorm.core.loader import load_builtin_profile
from cadnorm.translators.autocad import AutoCADTranslator
from cadnorm.translators.librecad import LibreCADTranslator


# ---------------------------------------------------------------------------
# Fixtures de sesión (carga y generación una sola vez por suite)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def iram_profile():
    """Perfil IRAM cargado como NormProfile validado."""
    return load_builtin_profile("iram_general")


@pytest.fixture(scope="session")
def autocad_result(iram_profile, tmp_path_factory):
    """Genera el .dwt una vez y lo reutiliza en todos los tests AutoCAD."""
    out = tmp_path_factory.mktemp("autocad") / "iram_test.dwt"
    translator = AutoCADTranslator()
    return translator.generate(iram_profile, out)


@pytest.fixture(scope="session")
def autocad_doc(autocad_result):
    """Documento ezdxf del .dwt generado."""
    assert autocad_result.success, f"Generación AutoCAD fallida:\n{autocad_result}"
    return ezdxf.readfile(str(autocad_result.output_path))


@pytest.fixture(scope="session")
def librecad_result(iram_profile, tmp_path_factory):
    """Genera el .dxf una vez y lo reutiliza en todos los tests LibreCAD."""
    out = tmp_path_factory.mktemp("librecad") / "iram_test.dxf"
    translator = LibreCADTranslator()
    return translator.generate(iram_profile, out)


@pytest.fixture(scope="session")
def librecad_doc(librecad_result):
    """Documento ezdxf del .dxf generado."""
    assert librecad_result.success, f"Generación LibreCAD fallida:\n{librecad_result}"
    return ezdxf.readfile(str(librecad_result.output_path))


# ---------------------------------------------------------------------------
# Tests: interfaz del Translator
# ---------------------------------------------------------------------------

class TestTranslatorInterface:
    """Verifica que los traductores implementan correctamente la interfaz."""

    def test_autocad_software_name(self):
        assert AutoCADTranslator().software_name == "autocad"

    def test_autocad_output_extension(self):
        assert AutoCADTranslator().output_extension == ".dwt"

    def test_librecad_software_name(self):
        assert LibreCADTranslator().software_name == "librecad"

    def test_librecad_output_extension(self):
        assert LibreCADTranslator().output_extension == ".dxf"


# ---------------------------------------------------------------------------
# Tests: AutoCAD — resultado de generación
# ---------------------------------------------------------------------------

class TestAutoCADResult:
    """Verifica el GenerationResult del traductor AutoCAD."""

    def test_generation_success(self, autocad_result):
        assert autocad_result.success

    def test_output_file_exists(self, autocad_result):
        assert autocad_result.output_path is not None
        assert autocad_result.output_path.exists()

    def test_output_file_not_empty(self, autocad_result):
        assert autocad_result.output_path.stat().st_size > 0

    def test_no_errors(self, autocad_result):
        assert not autocad_result.errors, f"Errores inesperados: {autocad_result.errors}"

    def test_stats_layers_ge_8(self, autocad_result):
        assert autocad_result.stats.get("layers", 0) >= 8

    def test_stats_text_styles_ge_5(self, autocad_result):
        assert autocad_result.stats.get("text_styles", 0) >= 5

    def test_stats_dim_styles_ge_1(self, autocad_result):
        assert autocad_result.stats.get("dim_styles", 0) >= 1


# ---------------------------------------------------------------------------
# Tests: AutoCAD — contenido del DXF generado
# ---------------------------------------------------------------------------

class TestAutoCADContent:
    """Verifica el contenido del DXF generado para AutoCAD."""

    def test_file_opens_with_ezdxf(self, autocad_doc):
        assert autocad_doc is not None

    def test_dxf_version_r2010(self, autocad_doc):
        assert autocad_doc.dxfversion == "AC1024", (
            f"Se esperaba R2010 (AC1024), se obtuvo {autocad_doc.dxfversion}"
        )

    def test_units_are_metric(self, autocad_doc):
        assert autocad_doc.header["$MEASUREMENT"] == 1   # 1 = métrico
        assert autocad_doc.header["$INSUNITS"] == 4      # 4 = mm

    def test_linear_format_is_decimal(self, autocad_doc):
        assert autocad_doc.header["$LUNITS"] == 2        # 2 = decimal

    # --- Capas ---

    def test_critical_layers_exist(self, autocad_doc):
        layer_names = {la.dxf.name for la in autocad_doc.layers}
        required = {"VP-VISIBLE", "OC-OCULTA", "EJ-EJE", "CO-COTA",
                    "HT-HACHURA", "MA-MARCO", "RT-ROTULO", "AN-ANOTACION"}
        missing = required - layer_names
        assert not missing, f"Capas IRAM faltantes: {missing}"

    def test_layer_0_exists(self, autocad_doc):
        layer_names = {la.dxf.name for la in autocad_doc.layers}
        assert "0" in layer_names

    def test_visible_layer_color(self, autocad_doc):
        layer = autocad_doc.layers.get("VP-VISIBLE")
        assert layer is not None
        assert layer.color == 7

    def test_hidden_layer_color(self, autocad_doc):
        layer = autocad_doc.layers.get("OC-OCULTA")
        assert layer is not None
        assert layer.color == 2   # amarillo IRAM

    def test_axis_layer_color(self, autocad_doc):
        layer = autocad_doc.layers.get("EJ-EJE")
        assert layer is not None
        assert layer.color == 1   # rojo IRAM

    def test_reference_layer_does_not_plot(self, autocad_doc):
        layer = autocad_doc.layers.get("REF-REFERENCIA")
        assert layer is not None
        # En ezdxf, dxf.plot: 0=no imprimir, 1=imprimir (DXF grupo 290)
        assert layer.dxf.plot == 0

    # --- Tipos de línea ---

    def test_custom_linetypes_exist(self, autocad_doc):
        lt_names = {lt.dxf.name for lt in autocad_doc.linetypes}
        # Al menos CENTER, DASHED y CUTTING_PLANE deben estar presentes
        for required in ("CENTER", "DASHED", "CUTTING_PLANE"):
            assert required in lt_names, f"Tipo de línea '{required}' faltante"

    def test_cutting_plane_linetype(self, autocad_doc):
        lt_names = {lt.dxf.name for lt in autocad_doc.linetypes}
        assert "CUTTING_PLANE" in lt_names

    # --- Estilos de texto ---

    def test_iram_text_styles_exist(self, autocad_doc):
        style_names = {s.dxf.name for s in autocad_doc.styles}
        required = {"IRAM_STD", "IRAM_H25", "IRAM_H35", "IRAM_H50",
                    "IRAM_H70", "IRAM_H100", "IRAM_H140"}
        missing = required - style_names
        assert not missing, f"Estilos de texto faltantes: {missing}"

    def test_default_text_style_height_is_variable(self, autocad_doc):
        """IRAM_STD debe tener height=0 (variable según contexto)."""
        style = autocad_doc.styles.get("IRAM_STD")
        assert style is not None
        assert style.dxf.height == 0.0

    def test_h25_style_height(self, autocad_doc):
        style = autocad_doc.styles.get("IRAM_H25")
        assert style is not None
        assert style.dxf.height == pytest.approx(2.5)

    # --- Estilos de cota ---

    def test_iram_standard_dimstyle_exists(self, autocad_doc):
        dimstyle_names = {ds.dxf.name for ds in autocad_doc.dimstyles}
        assert "IRAM_STANDARD" in dimstyle_names

    def test_dimstyle_scale(self, autocad_doc):
        ds = autocad_doc.dimstyles.get("IRAM_STANDARD")
        assert ds.dxf.dimscale == pytest.approx(1.0)

    def test_dimstyle_text_height(self, autocad_doc):
        ds = autocad_doc.dimstyles.get("IRAM_STANDARD")
        assert ds.dxf.dimtxt == pytest.approx(2.5)

    def test_dimstyle_decimal_places_zero(self, autocad_doc):
        """IRAM 4513: cotas en mm sin decimales."""
        ds = autocad_doc.dimstyles.get("IRAM_STANDARD")
        assert ds.dxf.dimdec == 0


# ---------------------------------------------------------------------------
# Tests: LibreCAD — resultado de generación
# ---------------------------------------------------------------------------

class TestLibreCADResult:
    """Verifica el GenerationResult del traductor LibreCAD."""

    def test_generation_success(self, librecad_result):
        assert librecad_result.success

    def test_output_file_exists(self, librecad_result):
        assert librecad_result.output_path is not None
        assert librecad_result.output_path.exists()

    def test_output_file_not_empty(self, librecad_result):
        assert librecad_result.output_path.stat().st_size > 0

    def test_no_errors(self, librecad_result):
        assert not librecad_result.errors, f"Errores inesperados: {librecad_result.errors}"

    def test_dim_styles_stat_is_zero(self, librecad_result):
        """LibreCAD no exporta DimStyles."""
        assert librecad_result.stats.get("dim_styles", 0) == 0

    def test_stats_layers_ge_8(self, librecad_result):
        assert librecad_result.stats.get("layers", 0) >= 8


# ---------------------------------------------------------------------------
# Tests: LibreCAD — contenido del DXF generado
# ---------------------------------------------------------------------------

class TestLibreCADContent:
    """Verifica el contenido del DXF generado para LibreCAD."""

    def test_file_opens_with_ezdxf(self, librecad_doc):
        assert librecad_doc is not None

    def test_dxf_version_r2004(self, librecad_doc):
        assert librecad_doc.dxfversion == "AC1018", (
            f"Se esperaba R2004 (AC1018), se obtuvo {librecad_doc.dxfversion}"
        )

    def test_units_are_metric(self, librecad_doc):
        assert librecad_doc.header["$MEASUREMENT"] == 1
        assert librecad_doc.header["$INSUNITS"] == 4

    def test_critical_layers_exist(self, librecad_doc):
        layer_names = {la.dxf.name for la in librecad_doc.layers}
        required = {"VP-VISIBLE", "OC-OCULTA", "EJ-EJE", "CO-COTA", "HT-HACHURA"}
        missing = required - layer_names
        assert not missing, f"Capas IRAM faltantes en DXF LibreCAD: {missing}"

    def test_custom_linetypes_exist(self, librecad_doc):
        lt_names = {lt.dxf.name for lt in librecad_doc.linetypes}
        for required in ("CENTER", "DASHED", "CUTTING_PLANE"):
            assert required in lt_names, f"Tipo de línea '{required}' faltante en LibreCAD DXF"

    def test_text_styles_exist(self, librecad_doc):
        style_names = {s.dxf.name for s in librecad_doc.styles}
        required = {"IRAM_STD", "IRAM_H25", "IRAM_H35", "IRAM_H50"}
        missing = required - style_names
        assert not missing, f"Estilos de texto faltantes en LibreCAD DXF: {missing}"


# ---------------------------------------------------------------------------
# Tests: robustez
# ---------------------------------------------------------------------------

class TestTranslatorRobustness:
    """Verifica comportamiento de los traductores ante condiciones especiales."""

    def test_autocad_creates_nested_output_dir(self, iram_profile, tmp_path):
        """El traductor AutoCAD debe crear directorios anidados si no existen."""
        nested = tmp_path / "a" / "b" / "c" / "output.dwt"
        result = AutoCADTranslator().generate(iram_profile, nested)
        assert result.success
        assert nested.exists()

    def test_librecad_creates_nested_output_dir(self, iram_profile, tmp_path):
        """El traductor LibreCAD debe crear directorios anidados si no existen."""
        nested = tmp_path / "x" / "y" / "output.dxf"
        result = LibreCADTranslator().generate(iram_profile, nested)
        assert result.success
        assert nested.exists()

    def test_autocad_result_has_output_path(self, iram_profile, tmp_path):
        out = tmp_path / "check.dwt"
        result = AutoCADTranslator().generate(iram_profile, out)
        assert result.output_path == out

    def test_librecad_result_has_output_path(self, iram_profile, tmp_path):
        out = tmp_path / "check.dxf"
        result = LibreCADTranslator().generate(iram_profile, out)
        assert result.output_path == out
