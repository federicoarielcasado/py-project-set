"""Tests del módulo db — Sprint 1.

Usa SQLite en memoria (':memory:') para que los tests sean rápidos
y no dejen archivos en disco.
"""
import json

import pytest

from cadnorm.core.db import (
    delete_profile,
    get_connection,
    get_generation_log,
    get_profile,
    init_db,
    list_profiles,
    log_generation,
    save_profile,
)

# ---------------------------------------------------------------------------
# Fixture: conexión en memoria por cada test
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """Conexión SQLite en memoria, inicializada con las tablas."""
    connection = get_connection(":memory:")
    init_db(connection)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------

SAMPLE_DATA = {
    "metadata": {"standard_name": "IRAM", "profile_version": "1.0.0"},
    "layers": [{"name": "VP-VISIBLE"}],
}


# ---------------------------------------------------------------------------
# Tests: get_connection + init_db
# ---------------------------------------------------------------------------

class TestConnection:
    def test_in_memory_connection(self):
        c = get_connection(":memory:")
        assert c is not None
        c.close()

    def test_init_db_creates_tables(self, conn):
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "profiles" in tables
        assert "generation_log" in tables

    def test_init_db_is_idempotent(self, conn):
        init_db(conn)  # segunda vez — no debe fallar
        init_db(conn)  # tercera vez
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "profiles" in tables


# ---------------------------------------------------------------------------
# Tests: CRUD profiles
# ---------------------------------------------------------------------------

class TestProfiles:
    def test_save_and_get_profile(self, conn):
        row_id = save_profile(conn, "Mi_IRAM", "IRAM", SAMPLE_DATA)
        assert row_id >= 1

        profile = get_profile(conn, "Mi_IRAM")
        assert profile is not None
        assert profile["name"] == "Mi_IRAM"
        assert profile["standard_name"] == "IRAM"
        assert profile["data"] == SAMPLE_DATA

    def test_get_nonexistent_returns_none(self, conn):
        assert get_profile(conn, "NO_EXISTE") is None

    def test_save_duplicate_updates(self, conn):
        save_profile(conn, "PERFIL", "IRAM", {"v": 1})
        save_profile(conn, "PERFIL", "IRAM", {"v": 2})  # debe actualizar

        profile = get_profile(conn, "PERFIL")
        assert profile["data"]["v"] == 2

    def test_list_profiles_empty(self, conn):
        assert list_profiles(conn) == []

    def test_list_profiles_returns_all(self, conn):
        save_profile(conn, "A", "IRAM", {})
        save_profile(conn, "B", "ISO", {})
        profiles = list_profiles(conn)
        assert len(profiles) == 2
        names = {p["name"] for p in profiles}
        assert names == {"A", "B"}

    def test_list_profiles_sorted_by_name(self, conn):
        save_profile(conn, "Z", "IRAM", {})
        save_profile(conn, "A", "ISO", {})
        save_profile(conn, "M", "ASME", {})
        names = [p["name"] for p in list_profiles(conn)]
        assert names == sorted(names)

    def test_list_profiles_no_data_json_field(self, conn):
        save_profile(conn, "X", "IRAM", {"big": "data"})
        profiles = list_profiles(conn)
        assert "data_json" not in profiles[0]

    def test_delete_existing_profile(self, conn):
        save_profile(conn, "BORRABLE", "IRAM", {})
        deleted = delete_profile(conn, "BORRABLE")
        assert deleted is True
        assert get_profile(conn, "BORRABLE") is None

    def test_delete_nonexistent_returns_false(self, conn):
        assert delete_profile(conn, "NO_EXISTE") is False

    def test_profile_timestamps_set(self, conn):
        save_profile(conn, "T", "IRAM", {})
        profile = get_profile(conn, "T")
        assert profile["created_at"]
        assert profile["updated_at"]

    def test_profile_data_roundtrip(self, conn):
        data = {"unicode": "áéíóú — ñ", "list": [1, 2, 3], "nested": {"a": True}}
        save_profile(conn, "UNICODE", "TEST", data)
        loaded = get_profile(conn, "UNICODE")
        assert loaded["data"] == data


# ---------------------------------------------------------------------------
# Tests: generation_log
# ---------------------------------------------------------------------------

class TestGenerationLog:
    def test_log_generation_basic(self, conn):
        log_id = log_generation(conn, "Mi_IRAM", "autocad", "/output/plano.dwt")
        assert log_id >= 1

    def test_log_generation_success_default(self, conn):
        log_generation(conn, "P", "autocad", "/out.dwt")
        entries = get_generation_log(conn)
        assert entries[0]["success"] is True

    def test_log_generation_failure(self, conn):
        log_generation(conn, "P", "autocad", "/out.dwt", success=False)
        entries = get_generation_log(conn)
        assert entries[0]["success"] is False

    def test_log_with_warnings(self, conn):
        warnings = ["WARN-001: escala no normalizada", "WARN-002: color fuera de rango"]
        log_generation(conn, "P", "librecad", "/out.dxf", warnings=warnings)
        entries = get_generation_log(conn)
        assert entries[0]["warnings"] == warnings

    def test_log_empty_warnings(self, conn):
        log_generation(conn, "P", "autocad", "/out.dwt")
        entries = get_generation_log(conn)
        assert entries[0]["warnings"] == []

    def test_get_log_returns_most_recent_first(self, conn):
        log_generation(conn, "A", "autocad", "/a.dwt")
        log_generation(conn, "B", "autocad", "/b.dwt")
        log_generation(conn, "C", "autocad", "/c.dwt")
        entries = get_generation_log(conn)
        names = [e["profile_name"] for e in entries]
        assert names == ["C", "B", "A"]

    def test_get_log_limit(self, conn):
        for i in range(10):
            log_generation(conn, f"P{i}", "autocad", f"/out{i}.dwt")
        entries = get_generation_log(conn, limit=3)
        assert len(entries) == 3

    def test_get_log_filter_by_profile(self, conn):
        log_generation(conn, "IRAM", "autocad", "/a.dwt")
        log_generation(conn, "ISO", "autocad", "/b.dwt")
        log_generation(conn, "IRAM", "librecad", "/c.dxf")
        entries = get_generation_log(conn, profile_name="IRAM")
        assert all(e["profile_name"] == "IRAM" for e in entries)
        assert len(entries) == 2

    def test_get_log_entry_has_all_fields(self, conn):
        log_generation(conn, "P", "autocad", "/out.dwt", warnings=["W1"])
        entry = get_generation_log(conn)[0]
        assert "id" in entry
        assert "profile_name" in entry
        assert "software" in entry
        assert "output_path" in entry
        assert "generated_at" in entry
        assert "success" in entry
        assert "warnings" in entry

    def test_get_log_empty(self, conn):
        assert get_generation_log(conn) == []
