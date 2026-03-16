"""Traductor LibreCAD — genera archivos .dxf vía ezdxf.

Sprint 2 implementa la generación completa.
Sprint 0: esqueleto con la interfaz definida.
"""
# TODO Sprint 2: implementar generación completa de .dxf con ezdxf

from __future__ import annotations
from pathlib import Path

from cadnorm.core.models import NormProfile
from cadnorm.translators.base import GenerationResult, Translator


class LibreCADTranslator(Translator):
    """Traduce un perfil normativo a un archivo DXF compatible con LibreCAD."""

    @property
    def software_name(self) -> str:
        return "librecad"

    @property
    def output_extension(self) -> str:
        return ".dxf"

    def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult:
        """Genera un archivo .dxf con la configuración del perfil normativo.

        TODO Sprint 2:
        - Crear doc ezdxf R2010 (compatible con LibreCAD)
        - Aplicar unidades y configuración general
        - Crear capas con color ACI y tipo de línea
        - Crear estilos de texto
        - Guardar como .dxf
        """
        raise NotImplementedError("LibreCADTranslator.generate() — implementado en Sprint 2")
