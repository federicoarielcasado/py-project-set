"""Interfaz abstracta para traductores de perfiles normativos a formatos CAD.

Cada software CAD soportado implementa esta interfaz (patrón Strategy).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from cadnorm.core.models import NormProfile


@dataclass
class GenerationResult:
    """Resultado de una operación de generación de archivo CAD."""
    success: bool
    output_path: Path | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "OK" if self.success else "FALLO"
        lines = [f"GenerationResult [{status}]"]
        if self.output_path:
            lines.append(f"  Archivo: {self.output_path}")
        if self.warnings:
            lines.extend(f"  WARN: {w}" for w in self.warnings)
        if self.errors:
            lines.extend(f"  ERROR: {e}" for e in self.errors)
        if self.stats:
            for k, v in self.stats.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


class Translator(ABC):
    """Interfaz base para todos los traductores CAD.

    Cada implementación concreta conoce la sintaxis específica de un
    software (AutoCAD, LibreCAD, BricsCAD, etc.) y traduce el perfil
    normativo abstracto a ese formato.
    """

    @property
    @abstractmethod
    def software_name(self) -> str:
        """Nombre del software CAD objetivo (ej: 'autocad', 'librecad')."""
        ...

    @property
    @abstractmethod
    def output_extension(self) -> str:
        """Extensión del archivo generado (ej: '.dwt', '.dxf')."""
        ...

    @abstractmethod
    def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult:
        """Genera el archivo CAD configurado según el perfil normativo.

        Args:
            profile: Perfil normativo validado.
            output_path: Ruta destino del archivo generado.

        Returns:
            GenerationResult con el resultado de la operación.
        """
        ...

    def validate_profile(self, profile: NormProfile) -> list[str]:
        """Valida que el perfil tiene los datos necesarios para este traductor.

        Override en subclases para validaciones específicas del software.

        Returns:
            Lista de mensajes de advertencia (vacía si todo OK).
        """
        # TODO Sprint 2: agregar validaciones específicas por software
        return []
