"""Persistencia SQLite para perfiles de usuario e historial de generación.

Sprint 1 implementa el schema completo y las operaciones CRUD.
Sprint 0: esqueleto con función de inicialización.
"""
# TODO Sprint 1: implementar schema SQLite, operaciones CRUD y migraciones

from __future__ import annotations
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".cadnorm" / "cadnorm.db"


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Abre (o crea) la base de datos SQLite de CADNorm.

    Args:
        db_path: Ruta al archivo de base de datos.

    Returns:
        Conexión SQLite configurada.
    """
    # TODO Sprint 1: crear tablas si no existen (profiles, generation_log)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
