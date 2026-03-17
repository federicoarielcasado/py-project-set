"""Traductor LibreCAD — genera archivos .dxf vía ezdxf.

Genera un DXF R2004 (AC1018) compatible con LibreCAD, aplicando:
  - Variables de encabezado (unidades métricas)
  - Tipos de línea (IRAM 4502)
  - Capas con color ACI, tipo de línea y espesor
  - Estilos de texto (IRAM 4503)

Nota: LibreCAD tiene soporte limitado de estilos de cota (DimStyle),
por lo que solo se generan los parámetros compatibles con R2004.

Patrón Strategy: implementa la interfaz Translator definida en base.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

import ezdxf

from cadnorm.core.models import NormProfile
from cadnorm.translators.autocad import (
    _apply_header,
    _apply_layers,
    _apply_linetypes,
    _apply_text_styles,
)
from cadnorm.translators.base import GenerationResult, Translator

logger = logging.getLogger(__name__)


class LibreCADTranslator(Translator):
    """Traduce un perfil normativo a un archivo DXF compatible con LibreCAD."""

    @property
    def software_name(self) -> str:
        return "librecad"

    @property
    def output_extension(self) -> str:
        return ".dxf"

    def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult:
        """Genera un archivo .dxf R2004 con la configuración del perfil normativo.

        Usa DXF versión R2004 (AC1018) por su alta compatibilidad con LibreCAD.
        Los estilos de cota (DimStyle) no se exportan por limitaciones del software.

        Args:
            profile: Perfil normativo validado por Pydantic.
            output_path: Ruta destino del archivo .dxf.

        Returns:
            GenerationResult con éxito/fallo, warnings y estadísticas.
        """
        warnings: list[str] = []

        try:
            # R2004 (AC1018) — mejor compatibilidad con LibreCAD
            doc = ezdxf.new(dxfversion="R2004", setup=True)

            # Encabezado (unidades métricas)
            _apply_header(doc, profile)

            # Tipos de línea
            lt_count = _apply_linetypes(doc, profile.linetypes, warnings)

            # Capas
            la_count = _apply_layers(doc, profile.layers, warnings)

            # Estilos de texto
            ts_count = _apply_text_styles(doc, profile.text_styles, warnings)

            # Estilos de cota: omitidos (compatibilidad limitada en LibreCAD)
            warnings.append(
                "INFO-001: Estilos de cota (DimStyle) no exportados — "
                "LibreCAD los gestiona internamente"
            )

            # Guardar
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(output_path))

            return GenerationResult(
                success=True,
                output_path=output_path,
                warnings=warnings,
                stats={
                    "linetypes": lt_count,
                    "layers": la_count,
                    "text_styles": ts_count,
                    "dim_styles": 0,
                },
            )

        except Exception as exc:
            logger.exception("Error generando archivo LibreCAD")
            return GenerationResult(
                success=False,
                errors=[f"Error de generación: {exc}"],
            )
