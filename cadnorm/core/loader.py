"""Carga y validación de perfiles normativos desde JSON.

Sprint 1 implementa validación contra schema.json y persistencia en SQLite.
Sprint 0: carga básica sin validación de schema.
"""
# TODO Sprint 1: agregar validación jsonschema y manejo de errores tipificados

from __future__ import annotations
import json
from pathlib import Path

from cadnorm.core.models import NormProfile

STANDARDS_DIR = Path(__file__).parent.parent / "standards"


def load_profile(path: Path | str) -> NormProfile:
    """Carga un perfil normativo desde un archivo JSON.

    Args:
        path: Ruta al archivo JSON del perfil.

    Returns:
        NormProfile con los datos cargados.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        json.JSONDecodeError: Si el JSON es inválido.
    """
    # TODO Sprint 1: validar contra schema.json antes de retornar
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return NormProfile(data)


def load_builtin_profile(standard_name: str) -> NormProfile:
    """Carga un perfil normativo incluido en el paquete.

    Args:
        standard_name: Nombre de la norma (ej: 'iram_general').

    Returns:
        NormProfile del perfil estándar solicitado.
    """
    path = STANDARDS_DIR / f"{standard_name}.json"
    return load_profile(path)
