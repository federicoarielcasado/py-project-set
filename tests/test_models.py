"""Tests de modelos Pydantic v2 — Sprint 1.

Cubre:
  - Construcción correcta de cada modelo con datos válidos
  - Validaciones de rango y reglas de negocio
  - Helpers de NormProfile (default_text_style, layer_by_name, etc.)
"""
import pytest
from pydantic import ValidationError

from cadnorm.core.models import (
    DimStyle,
    DrawingScale,
    HatchPattern,
    Layer,
    Linetype,
    Metadata,
    NormProfile,
    PaperSize,
    PlotConfig,
    TextStyle,
    TitleBlock,
    TitleBlockField,
    Units,
)

# ---------------------------------------------------------------------------
# Datos mínimos válidos por modelo
# ---------------------------------------------------------------------------

VALID_METADATA = {
    "standard_name": "TEST",
    "standard_version": "1.0",
    "effective_date": "2024-01-01",
    "source": "Fuente de prueba",
    "profile_version": "1.0.0",
    "description": "Perfil de prueba",
    "software_targets": ["autocad"],
    "country": "AR",
}

VALID_UNITS = {
    "system": "metric",
    "linear_unit": "mm",
    "linear_precision": 2,
    "angular_unit": "degrees",
    "angular_precision": 0,
    "insertion_scale": "mm",
    "measurement_system": 1,
}

VALID_LINETYPE = {
    "name": "CONTINUOUS",
    "description": "Línea continua",
    "pattern": "",
}

VALID_LAYER = {
    "name": "VP-VISIBLE",
    "color_aci": 7,
    "linetype": "CONTINUOUS",
    "lineweight": 50,
    "plot": True,
    "locked": False,
    "frozen": False,
    "description": "Líneas visibles",
}

VALID_TEXT_STYLE = {
    "name": "IRAM_STD",
    "font": "isocp.shx",
    "height": 0.0,
    "width_factor": 1.0,
    "oblique_angle": 0.0,
    "is_default": True,
}

VALID_DIM_STYLE = {
    "name": "IRAM_STANDARD",
    "dimscale": 1.0,
    "dimtxt": 2.5,
    "dimexo": 1.5,
    "dimexe": 2.0,
    "dimasz": 2.5,
    "dimgap": 1.0,
    "dimdec": 2,
    "dimtih": False,
    "dimtoh": False,
    "dimblk": "",
    "dimclrd": 3,
    "dimclre": 3,
    "dimclrt": 3,
    "dimtxsty": "IRAM_H25",
    "dimlunit": 2,
    "dimadec": 0,
    "is_default": True,
}

VALID_SCALE_NATURAL = {"label": "1:1", "numerator": 1, "denominator": 1, "type": "natural"}
VALID_SCALE_REDUCTION = {"label": "1:50", "numerator": 1, "denominator": 50, "type": "reduction"}
VALID_SCALE_AMPLIFICATION = {"label": "2:1", "numerator": 2, "denominator": 1, "type": "amplification"}

VALID_PAPER = {
    "name": "A4",
    "width_mm": 210.0,
    "height_mm": 297.0,
    "margin_left": 25.0,
    "margin_right": 5.0,
    "margin_top": 5.0,
    "margin_bottom": 5.0,
    "orientation": "portrait",
}

VALID_TITLE_BLOCK_FIELD = {
    "id": "title",
    "label": "Título",
    "required": True,
    "default": "",
    "max_length": 100,
}

VALID_HATCH = {"name": "ANSI31", "description": "Hierro", "angle": 45.0, "scale": 1.0}

VALID_PLOT_CONFIG = {
    "plot_style_type": "ctb",
    "plot_style_file": "monochrome.ctb",
    "plot_area": "layout",
    "scale_to_paper": False,
    "center_plot": True,
    "plot_hidden": False,
    "lineweight_scale": 1.0,
}


# ---------------------------------------------------------------------------
# Tests por modelo
# ---------------------------------------------------------------------------

class TestMetadata:
    def test_valid(self):
        m = Metadata(**VALID_METADATA)
        assert m.standard_name == "TEST"
        assert m.country == "AR"

    def test_missing_required_field(self):
        data = {**VALID_METADATA}
        data.pop("standard_name")
        with pytest.raises(ValidationError):
            Metadata(**data)


class TestUnits:
    def test_valid_metric(self):
        u = Units(**VALID_UNITS)
        assert u.system == "metric"

    def test_invalid_system(self):
        with pytest.raises(ValidationError):
            Units(**{**VALID_UNITS, "system": "japanese"})

    def test_precision_out_of_range(self):
        with pytest.raises(ValidationError):
            Units(**{**VALID_UNITS, "linear_precision": 99})

    def test_measurement_system_out_of_range(self):
        with pytest.raises(ValidationError):
            Units(**{**VALID_UNITS, "measurement_system": 5})


class TestLinetype:
    def test_valid(self):
        lt = Linetype(**VALID_LINETYPE)
        assert lt.name == "CONTINUOUS"

    def test_norm_ref_optional(self):
        lt = Linetype(**VALID_LINETYPE)
        assert lt.norm_ref is None

    def test_norm_ref_set(self):
        lt = Linetype(**{**VALID_LINETYPE, "norm_ref": "IRAM 4504"})
        assert lt.norm_ref == "IRAM 4504"


class TestLayer:
    def test_valid(self):
        la = Layer(**VALID_LAYER)
        assert la.name == "VP-VISIBLE"
        assert la.plot is True

    def test_color_aci_upper_limit(self):
        la = Layer(**{**VALID_LAYER, "color_aci": 256})
        assert la.color_aci == 256

    def test_color_aci_too_high(self):
        with pytest.raises(ValidationError):
            Layer(**{**VALID_LAYER, "color_aci": 300})

    def test_color_aci_bylayer(self):
        la = Layer(**{**VALID_LAYER, "color_aci": -2})
        assert la.color_aci == -2


class TestTextStyle:
    def test_valid(self):
        ts = TextStyle(**VALID_TEXT_STYLE)
        assert ts.is_default is True

    def test_negative_height_invalid(self):
        with pytest.raises(ValidationError):
            TextStyle(**{**VALID_TEXT_STYLE, "height": -1.0})

    def test_zero_width_factor_invalid(self):
        with pytest.raises(ValidationError):
            TextStyle(**{**VALID_TEXT_STYLE, "width_factor": 0.0})

    def test_oblique_angle_limit(self):
        with pytest.raises(ValidationError):
            TextStyle(**{**VALID_TEXT_STYLE, "oblique_angle": 90.0})


class TestDimStyle:
    def test_valid(self):
        ds = DimStyle(**VALID_DIM_STYLE)
        assert ds.name == "IRAM_STANDARD"
        assert ds.is_default is True

    def test_dimscale_zero_invalid(self):
        with pytest.raises(ValidationError):
            DimStyle(**{**VALID_DIM_STYLE, "dimscale": 0.0})

    def test_dimdec_out_of_range(self):
        with pytest.raises(ValidationError):
            DimStyle(**{**VALID_DIM_STYLE, "dimdec": 10})

    def test_dimlunit_out_of_range(self):
        with pytest.raises(ValidationError):
            DimStyle(**{**VALID_DIM_STYLE, "dimlunit": 0})


class TestDrawingScale:
    def test_natural_scale(self):
        s = DrawingScale(**VALID_SCALE_NATURAL)
        assert s.type == "natural"

    def test_reduction_scale(self):
        s = DrawingScale(**VALID_SCALE_REDUCTION)
        assert s.denominator == 50

    def test_amplification_scale(self):
        s = DrawingScale(**VALID_SCALE_AMPLIFICATION)
        assert s.numerator == 2

    def test_natural_type_wrong_ratio(self):
        with pytest.raises(ValidationError, match="natural"):
            DrawingScale(label="1:2", numerator=1, denominator=2, type="natural")

    def test_reduction_type_wrong_ratio(self):
        with pytest.raises(ValidationError, match="reduction"):
            DrawingScale(label="2:1", numerator=2, denominator=1, type="reduction")

    def test_amplification_type_wrong_ratio(self):
        with pytest.raises(ValidationError, match="amplification"):
            DrawingScale(label="1:5", numerator=1, denominator=5, type="amplification")


class TestPaperSize:
    def test_valid_portrait(self):
        p = PaperSize(**VALID_PAPER)
        assert p.name == "A4"
        assert p.orientation == "portrait"

    def test_margins_exceed_width(self):
        with pytest.raises(ValidationError, match="márgenes horizontales"):
            PaperSize(**{**VALID_PAPER, "margin_left": 200, "margin_right": 50})

    def test_margins_exceed_height(self):
        with pytest.raises(ValidationError, match="márgenes verticales"):
            PaperSize(**{**VALID_PAPER, "margin_top": 150, "margin_bottom": 150})

    def test_zero_width_invalid(self):
        with pytest.raises(ValidationError):
            PaperSize(**{**VALID_PAPER, "width_mm": 0.0})


class TestTitleBlock:
    def test_valid(self):
        field = TitleBlockField(**VALID_TITLE_BLOCK_FIELD)
        tb = TitleBlock(fields=[field])
        assert len(tb.fields) == 1

    def test_duplicate_field_ids(self):
        field = TitleBlockField(**VALID_TITLE_BLOCK_FIELD)
        with pytest.raises(ValidationError, match="IDs de campos duplicados"):
            TitleBlock(fields=[field, field])

    def test_max_length_zero_invalid(self):
        with pytest.raises(ValidationError):
            TitleBlockField(**{**VALID_TITLE_BLOCK_FIELD, "max_length": 0})


class TestHatchPattern:
    def test_valid(self):
        h = HatchPattern(**VALID_HATCH)
        assert h.angle == 45.0

    def test_angle_360_invalid(self):
        with pytest.raises(ValidationError):
            HatchPattern(**{**VALID_HATCH, "angle": 360.0})

    def test_scale_zero_invalid(self):
        with pytest.raises(ValidationError):
            HatchPattern(**{**VALID_HATCH, "scale": 0.0})


class TestPlotConfig:
    def test_valid_ctb(self):
        pc = PlotConfig(**VALID_PLOT_CONFIG)
        assert pc.plot_style_type == "ctb"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            PlotConfig(**{**VALID_PLOT_CONFIG, "plot_style_type": "pdf"})

    def test_lineweight_scale_zero_invalid(self):
        with pytest.raises(ValidationError):
            PlotConfig(**{**VALID_PLOT_CONFIG, "lineweight_scale": 0.0})


# ---------------------------------------------------------------------------
# Tests de NormProfile (validadores de nivel raíz)
# ---------------------------------------------------------------------------

def _minimal_profile_data():
    """Devuelve un dict con los datos mínimos para construir un NormProfile."""
    return {
        "metadata": VALID_METADATA,
        "units": VALID_UNITS,
        "linetypes": [VALID_LINETYPE],
        "layers": [VALID_LAYER],
        "text_styles": [VALID_TEXT_STYLE],
        "dim_styles": [VALID_DIM_STYLE],
        "drawing_scales": [VALID_SCALE_NATURAL, VALID_SCALE_REDUCTION],
        "paper_sizes": [VALID_PAPER],
        "title_block": {"fields": [VALID_TITLE_BLOCK_FIELD]},
        "hatch_patterns": [VALID_HATCH],
        "plot_config": VALID_PLOT_CONFIG,
    }


class TestNormProfile:
    def test_build_from_dict(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        assert p.name == "TEST"
        assert p.version == "1.0.0"
        assert len(p.layers) == 1

    def test_repr(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        assert "NormProfile" in repr(p)
        assert "TEST" in repr(p)

    def test_duplicate_layer_names_raises(self):
        data = _minimal_profile_data()
        data["layers"] = [VALID_LAYER, VALID_LAYER]
        with pytest.raises(ValidationError, match="nombres de capa duplicados"):
            NormProfile.model_validate(data)

    def test_multiple_default_text_styles_raises(self):
        data = _minimal_profile_data()
        data["text_styles"] = [
            VALID_TEXT_STYLE,
            {**VALID_TEXT_STYLE, "name": "OTRO", "is_default": True},
        ]
        with pytest.raises(ValidationError, match="is_default"):
            NormProfile.model_validate(data)

    def test_multiple_default_dim_styles_raises(self):
        data = _minimal_profile_data()
        data["dim_styles"] = [
            VALID_DIM_STYLE,
            {**VALID_DIM_STYLE, "name": "OTRO", "is_default": True},
        ]
        with pytest.raises(ValidationError, match="is_default"):
            NormProfile.model_validate(data)

    def test_default_text_style_helper(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        ts = p.default_text_style()
        assert ts is not None
        assert ts.name == "IRAM_STD"

    def test_default_text_style_none_when_missing(self):
        data = _minimal_profile_data()
        data["text_styles"] = [{**VALID_TEXT_STYLE, "is_default": False}]
        p = NormProfile.model_validate(data)
        assert p.default_text_style() is None

    def test_default_dim_style_helper(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        ds = p.default_dim_style()
        assert ds is not None
        assert ds.name == "IRAM_STANDARD"

    def test_layer_by_name_found(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        la = p.layer_by_name("VP-VISIBLE")
        assert la is not None
        assert la.color_aci == 7

    def test_layer_by_name_not_found(self):
        p = NormProfile.model_validate(_minimal_profile_data())
        assert p.layer_by_name("INEXISTENTE") is None
