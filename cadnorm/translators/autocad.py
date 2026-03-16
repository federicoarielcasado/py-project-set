"""Traductor AutoCAD — genera archivos .dwt vía ezdxf.

Sprint 2 implementa la generación completa.
Sprint 0: esqueleto con la interfaz definida.
"""
# TODO Sprint 2: implementar generación completa de .dwt con ezdxf

from __future__ import annotations
from pathlib import Path

from cadnorm.core.models import NormProfile
from cadnorm.translators.base import GenerationResult, Translator


class AutoCADTranslator(Translator):
    """Traduce un perfil normativo a un archivo plantilla AutoCAD (.dwt)."""

    @property
    def software_name(self) -> str:
        return "autocad"

    @property
    def output_extension(self) -> str:
        return ".dwt"

    def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult:
        """Genera un archivo .dwt con la configuración del perfil normativo.

        TODO Sprint 2:
        - Crear doc ezdxf R2010
        - Aplicar unidades (INSUNITS, MEASUREMENT, LUNITS, LUPREC)
        - Crear capas con color ACI, tipo de línea y espesor
        - Crear estilos de texto (STYLE)
        - Crear estilos de cota (DIMSTYLE)
        - Configurar layouts (paperspace A4-A0)
        - Guardar como .dwt
        """
        raise NotImplementedError("AutoCADTranslator.generate() — implementado en Sprint 2")
