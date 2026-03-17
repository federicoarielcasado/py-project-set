"""Persistencia SQLite para perfiles de usuario e historial de generación.

Tablas:
  - profiles       : perfiles normativos personalizados (JSON exportado por el usuario)
  - generation_log : historial de archivos CAD generados con cadnorm

Uso típico:
    conn = get_connection()
    init_db(conn)
    save_profile(conn, "Mi_IRAM", "IRAM", profile_json)
    entries = list_profiles(conn)
    log_generation(conn, ...)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path.home() / ".cadnorm" / "cadnorm.db"

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    standard_name TEXT    NOT NULL,
    data_json     TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name  TEXT    NOT NULL,
    software      TEXT    NOT NULL,
    output_path   TEXT    NOT NULL,
    generated_at  TEXT    NOT NULL,
    success       INTEGER NOT NULL DEFAULT 1,
    warnings_json TEXT    NOT NULL DEFAULT '[]'
);
"""


# ---------------------------------------------------------------------------
# Conexión e inicialización
# ---------------------------------------------------------------------------

def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Abre (o crea) la base de datos SQLite de CADNorm.

    Args:
        db_path: Ruta al archivo .db. Usa ':memory:' para tests en memoria.

    Returns:
        Conexión SQLite configurada con row_factory y WAL mode.
    """
    db_path = Path(db_path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas si no existen. Idempotente."""
    conn.executescript(_DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# CRUD: profiles
# ---------------------------------------------------------------------------

def save_profile(
    conn: sqlite3.Connection,
    name: str,
    standard_name: str,
    data: dict,
) -> int:
    """Inserta o reemplaza un perfil de usuario.

    Args:
        conn: Conexión abierta con init_db() ya ejecutado.
        name: Nombre único del perfil (ej: 'Estudio_XYZ_IRAM').
        standard_name: Norma base (ej: 'IRAM').
        data: Diccionario del perfil (será serializado a JSON).

    Returns:
        ID del registro insertado o actualizado.
    """
    now = _utcnow()
    data_json = json.dumps(data, ensure_ascii=False)

    existing = conn.execute(
        "SELECT id FROM profiles WHERE name = ?", (name,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE profiles SET standard_name=?, data_json=?, updated_at=? WHERE name=?",
            (standard_name, data_json, now, name),
        )
        conn.commit()
        return existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO profiles (name, standard_name, data_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, standard_name, data_json, now, now),
        )
        conn.commit()
        return cur.lastrowid


def get_profile(conn: sqlite3.Connection, name: str) -> Optional[dict]:
    """Devuelve el perfil por nombre como diccionario, o None si no existe."""
    row = conn.execute(
        "SELECT * FROM profiles WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "standard_name": row["standard_name"],
        "data": json.loads(row["data_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_profiles(conn: sqlite3.Connection) -> list[dict]:
    """Lista todos los perfiles (sin el data_json completo para liviandad)."""
    rows = conn.execute(
        "SELECT id, name, standard_name, created_at, updated_at FROM profiles ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def delete_profile(conn: sqlite3.Connection, name: str) -> bool:
    """Elimina un perfil por nombre. Devuelve True si existía."""
    cur = conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# CRUD: generation_log
# ---------------------------------------------------------------------------

def log_generation(
    conn: sqlite3.Connection,
    profile_name: str,
    software: str,
    output_path: str | Path,
    success: bool = True,
    warnings: Optional[list[str]] = None,
) -> int:
    """Registra una entrada en el historial de generación.

    Args:
        conn: Conexión abierta.
        profile_name: Nombre del perfil usado.
        software: Software destino (ej: 'autocad', 'librecad').
        output_path: Ruta del archivo generado.
        success: True si la generación fue exitosa.
        warnings: Lista de strings con advertencias normativas.

    Returns:
        ID del registro creado.
    """
    cur = conn.execute(
        "INSERT INTO generation_log "
        "(profile_name, software, output_path, generated_at, success, warnings_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            profile_name,
            software,
            str(output_path),
            _utcnow(),
            int(success),
            json.dumps(warnings or [], ensure_ascii=False),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_generation_log(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    profile_name: Optional[str] = None,
) -> list[dict]:
    """Devuelve entradas del historial, más recientes primero.

    Args:
        conn: Conexión abierta.
        limit: Máximo de entradas a devolver.
        profile_name: Si se especifica, filtra por ese perfil.
    """
    if profile_name:
        rows = conn.execute(
            "SELECT * FROM generation_log WHERE profile_name = ? "
            "ORDER BY id DESC LIMIT ?",
            (profile_name, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM generation_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "profile_name": r["profile_name"],
            "software": r["software"],
            "output_path": r["output_path"],
            "generated_at": r["generated_at"],
            "success": bool(r["success"]),
            "warnings": json.loads(r["warnings_json"]),
        })
    return result


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
