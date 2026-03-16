"""Modelos Pydantic para perfiles normativos CAD.

Sprint 1 implementa la validación completa.
Sprint 0: esqueleto con clases base.
"""
# TODO Sprint 1: implementar validación completa con Pydantic v2

from __future__ import annotations
from typing import Any


class NormProfile:
    """Representa un perfil normativo completo (ej: IRAM, ISO, ASME).

    En Sprint 1 se convierte a BaseModel de Pydantic con validación
    contra schema.json.
    """
    # TODO Sprint 1: convertir a pydantic.BaseModel
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.metadata = data.get("metadata", {})
        self.units = data.get("units", {})
        self.layers = data.get("layers", [])
        self.linetypes = data.get("linetypes", [])
        self.text_styles = data.get("text_styles", [])
        self.dim_styles = data.get("dim_styles", [])
        self.drawing_scales = data.get("drawing_scales", [])
        self.paper_sizes = data.get("paper_sizes", [])
        self.title_block = data.get("title_block", {})
        self.hatch_patterns = data.get("hatch_patterns", [])
        self.plot_config = data.get("plot_config", {})

    @property
    def name(self) -> str:
        return self.metadata.get("standard_name", "")

    @property
    def version(self) -> str:
        return self.metadata.get("profile_version", "")

    def __repr__(self) -> str:
        return f"NormProfile(name={self.name!r}, version={self.version!r})"
