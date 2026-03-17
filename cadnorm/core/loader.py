"""Carga y validación de perfiles normativos desde JSON.

Flujo de carga:
  1. Leer el archivo JSON
  2. Validar contra schema.json (jsonschema)
  3. Parsear con NormProfile.model_validate() (Pydantic v2)

Los errores de validación usan tipos tipificados (ProfileLoadError,
SchemaValidationError) para que la CLI pueda mostrar mensajes claros.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from pydantic import ValidationError

from cadnorm.core.models import NormProfile

STANDARDS_DIR = Path(__file__).parent.parent / "standards"
SCHEMA_PATH = STANDARDS_DIR / "schema.json"


# ---------------------------------------------------------------------------
# Errores tipificados
# ---------------------------------------------------------------------------

class ProfileLoadError(Exception):
    """Error genérico al cargar un perfil normativo."""


class SchemaValidationError(ProfileLoadError):
    """El JSON no cumple el schema.json."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"SCHEMA-ERR: '{path.name}' — {detail}")


class ProfileParseError(ProfileLoadError):
    """El JSON cumple el schema pero falla la validación Pydantic."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"PARSE-ERR: '{path.name}' — {detail}")


# ---------------------------------------------------------------------------
# Funciones públicas
# ---------------------------------------------------------------------------

def load_profile(path: Path | str, *, validate_schema: bool = True) -> NormProfile:
    """Carga un perfil normativo desde un archivo JSON.

    Args:
        path: Ruta al archivo JSON del perfil.
        validate_schema: Si es True (default), valida contra schema.json antes
                         de construir el modelo Pydantic.

    Returns:
        NormProfile validado.

    Raises:
        FileNotFoundError: El archivo no existe.
        json.JSONDecodeError: El archivo no es JSON válido.
        SchemaValidationError: El JSON no cumple schema.json.
        ProfileParseError: El JSON cumple el schema pero falla la validación Pydantic.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if validate_schema:
        _validate_against_schema(path, data)

    try:
        return NormProfile.model_validate(data)
    except ValidationError as exc:
        raise ProfileParseError(path, str(exc)) from exc


def load_builtin_profile(standard_name: str) -> NormProfile:
    """Carga un perfil normativo incluido en el paquete.

    Args:
        standard_name: Nombre de la norma sin extensión (ej: 'iram_general').

    Returns:
        NormProfile del perfil estándar solicitado.

    Raises:
        FileNotFoundError: La norma solicitada no existe en el paquete.
    """
    path = STANDARDS_DIR / f"{standard_name}.json"
    if not path.exists():
        available = [p.stem for p in STANDARDS_DIR.glob("*.json") if p.stem != "schema"]
        raise FileNotFoundError(
            f"Norma '{standard_name}' no encontrada. "
            f"Disponibles: {available}"
        )
    return load_profile(path)


def load_schema() -> dict:
    """Carga el schema.json del paquete."""
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _validate_against_schema(path: Path, data: dict) -> None:
    """Valida `data` contra schema.json. Lanza SchemaValidationError si falla."""
    schema = load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise SchemaValidationError(path, exc.message) from exc
    except jsonschema.SchemaError as exc:
        raise SchemaValidationError(SCHEMA_PATH, f"schema.json inválido: {exc.message}") from exc
