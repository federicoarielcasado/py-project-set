"""Modelos Pydantic v2 para perfiles normativos CAD.

Cada clase refleja exactamente una sección del JSON normativo (schema.json).
La clase raíz NormProfile valida el perfil completo en un solo model_validate().
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sección: metadata
# ---------------------------------------------------------------------------

class Metadata(BaseModel):
    standard_name: str
    standard_version: str
    effective_date: str
    source: str
    profile_version: str
    description: str
    software_targets: list[str]
    country: str


# ---------------------------------------------------------------------------
# Sección: units
# ---------------------------------------------------------------------------

class Units(BaseModel):
    system: Literal["metric", "imperial"]
    linear_unit: str
    linear_precision: int = Field(ge=0, le=8)
    angular_unit: str
    angular_precision: int = Field(ge=0, le=8)
    insertion_scale: str
    measurement_system: int = Field(ge=0, le=1)


# ---------------------------------------------------------------------------
# Sección: linetypes
# ---------------------------------------------------------------------------

class Linetype(BaseModel):
    name: str
    description: str
    pattern: str
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Sección: layers
# ---------------------------------------------------------------------------

class Layer(BaseModel):
    name: str
    color_aci: int = Field(ge=-2, le=256)   # -2 = BYLAYER, -1 = BYBLOCK, 0-256 = ACI
    linetype: str
    lineweight: int                          # en centésimas de mm; -2/-1/0 = BY*
    plot: bool
    locked: bool
    frozen: bool
    description: str
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Sección: text_styles
# ---------------------------------------------------------------------------

class TextStyle(BaseModel):
    name: str
    font: str
    height: float = Field(ge=0.0)
    width_factor: float = Field(gt=0.0)
    oblique_angle: float = Field(ge=-85.0, le=85.0)
    is_default: bool
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Sección: dim_styles
# ---------------------------------------------------------------------------

class DimStyle(BaseModel):
    name: str
    dimscale: float = Field(gt=0.0)
    dimtxt: float = Field(gt=0.0)
    dimexo: float = Field(ge=0.0)
    dimexe: float = Field(ge=0.0)
    dimasz: float = Field(gt=0.0)
    dimgap: float = Field(ge=0.0)
    dimdec: int = Field(ge=0, le=8)
    dimtih: bool
    dimtoh: bool
    dimblk: str
    dimclrd: int = Field(ge=0, le=256)
    dimclre: int = Field(ge=0, le=256)
    dimclrt: int = Field(ge=0, le=256)
    dimtxsty: str
    dimlunit: int = Field(ge=1, le=6)
    dimadec: int = Field(ge=0, le=8)
    is_default: bool
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Sección: drawing_scales
# ---------------------------------------------------------------------------

class DrawingScale(BaseModel):
    label: str
    numerator: int = Field(gt=0)
    denominator: int = Field(gt=0)
    type: Literal["natural", "reduction", "amplification"]
    norm_ref: Optional[str] = None

    @model_validator(mode="after")
    def _check_type_consistency(self) -> DrawingScale:
        ratio = self.numerator / self.denominator
        if self.type == "natural" and ratio != 1.0:
            raise ValueError(f"Escala '{self.label}': tipo 'natural' requiere numerator == denominator")
        if self.type == "reduction" and ratio >= 1.0:
            raise ValueError(f"Escala '{self.label}': tipo 'reduction' requiere numerator < denominator")
        if self.type == "amplification" and ratio <= 1.0:
            raise ValueError(f"Escala '{self.label}': tipo 'amplification' requiere numerator > denominator")
        return self


# ---------------------------------------------------------------------------
# Sección: paper_sizes
# ---------------------------------------------------------------------------

class PaperSize(BaseModel):
    name: str
    width_mm: float = Field(gt=0.0)
    height_mm: float = Field(gt=0.0)
    margin_left: float = Field(ge=0.0)
    margin_right: float = Field(ge=0.0)
    margin_top: float = Field(ge=0.0)
    margin_bottom: float = Field(ge=0.0)
    orientation: Literal["portrait", "landscape"]
    norm_ref: Optional[str] = None

    @model_validator(mode="after")
    def _check_margins_fit(self) -> PaperSize:
        if (self.margin_left + self.margin_right) >= self.width_mm:
            raise ValueError(f"Papel '{self.name}': márgenes horizontales superan el ancho")
        if (self.margin_top + self.margin_bottom) >= self.height_mm:
            raise ValueError(f"Papel '{self.name}': márgenes verticales superan la altura")
        return self


# ---------------------------------------------------------------------------
# Sección: title_block
# ---------------------------------------------------------------------------

class TitleBlockField(BaseModel):
    id: str
    label: str
    required: bool
    default: str
    max_length: int = Field(gt=0)
    norm_ref: Optional[str] = None


class TitleBlock(BaseModel):
    norm_ref: Optional[str] = None
    fields: list[TitleBlockField]

    @field_validator("fields")
    @classmethod
    def _unique_field_ids(cls, v: list[TitleBlockField]) -> list[TitleBlockField]:
        ids = [f.id for f in v]
        if len(ids) != len(set(ids)):
            raise ValueError("title_block: IDs de campos duplicados")
        return v


# ---------------------------------------------------------------------------
# Sección: hatch_patterns
# ---------------------------------------------------------------------------

class HatchPattern(BaseModel):
    name: str
    description: str
    angle: float = Field(ge=0.0, lt=360.0)
    scale: float = Field(gt=0.0)
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Sección: plot_config
# ---------------------------------------------------------------------------

class PlotConfig(BaseModel):
    plot_style_type: Literal["ctb", "stb"]
    plot_style_file: str
    plot_area: str
    scale_to_paper: bool
    center_plot: bool
    plot_hidden: bool
    lineweight_scale: float = Field(gt=0.0)
    norm_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Raíz: NormProfile
# ---------------------------------------------------------------------------

class NormProfile(BaseModel):
    metadata: Metadata
    units: Units
    linetypes: list[Linetype]
    layers: list[Layer]
    text_styles: list[TextStyle]
    dim_styles: list[DimStyle]
    drawing_scales: list[DrawingScale]
    paper_sizes: list[PaperSize]
    title_block: TitleBlock
    hatch_patterns: list[HatchPattern]
    plot_config: PlotConfig

    @field_validator("layers")
    @classmethod
    def _unique_layer_names(cls, v: list[Layer]) -> list[Layer]:
        names = [la.name for la in v]
        if len(names) != len(set(names)):
            raise ValueError("layers: nombres de capa duplicados")
        return v

    @field_validator("text_styles")
    @classmethod
    def _single_default_text_style(cls, v: list[TextStyle]) -> list[TextStyle]:
        defaults = [ts for ts in v if ts.is_default]
        if len(defaults) > 1:
            raise ValueError("text_styles: más de un estilo marcado como is_default=true")
        return v

    @field_validator("dim_styles")
    @classmethod
    def _single_default_dim_style(cls, v: list[DimStyle]) -> list[DimStyle]:
        defaults = [ds for ds in v if ds.is_default]
        if len(defaults) > 1:
            raise ValueError("dim_styles: más de un estilo marcado como is_default=true")
        return v

    @property
    def name(self) -> str:
        return self.metadata.standard_name

    @property
    def version(self) -> str:
        return self.metadata.profile_version

    def default_text_style(self) -> Optional[TextStyle]:
        return next((ts for ts in self.text_styles if ts.is_default), None)

    def default_dim_style(self) -> Optional[DimStyle]:
        return next((ds for ds in self.dim_styles if ds.is_default), None)

    def layer_by_name(self, name: str) -> Optional[Layer]:
        return next((la for la in self.layers if la.name == name), None)

    def __repr__(self) -> str:
        return (
            f"NormProfile(name={self.name!r}, version={self.version!r}, "
            f"layers={len(self.layers)}, text_styles={len(self.text_styles)})"
        )
