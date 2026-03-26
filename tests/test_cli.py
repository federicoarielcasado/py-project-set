"""Tests para la CLI de CADNorm (Sprint 3).

Cubre los tres comandos principales: generate, profile, info.
Usa CliRunner de Typer para invocaciones sin subproceso.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cadnorm.cli.main import app
from cadnorm.core.db import get_connection, init_db, save_profile
from cadnorm.core.loader import load_builtin_profile

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige DEFAULT_DB_PATH a un archivo temporal."""
    db_file = tmp_path / "test_cadnorm.db"
    import cadnorm.core.db as db_mod
    monkeypatch.setattr(db_mod, "DEFAULT_DB_PATH", db_file)
    return db_file


@pytest.fixture()
def populated_db(tmp_db: Path) -> Path:
    """DB con un perfil IRAM precargado."""
    conn = get_connection(tmp_db)
    init_db(conn)
    profile = load_builtin_profile("iram_general")
    data = json.loads(profile.model_dump_json())
    save_profile(conn, "TestIRAM", "IRAM", data)
    conn.close()
    return tmp_db


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_generate_librecad_ok(self, tmp_path: Path, tmp_db: Path) -> None:
        out = tmp_path / "test_output.dxf"
        result = runner.invoke(
            app,
            ["generate", "--norm", "iram_general", "--software", "librecad", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        assert "✓ Archivo generado" in result.output

    def test_generate_autocad_ok(self, tmp_path: Path, tmp_db: Path) -> None:
        out = tmp_path / "test_output.dwt"
        result = runner.invoke(
            app,
            ["generate", "--norm", "iram_general", "--software", "autocad", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_generate_invalid_software(self, tmp_db: Path) -> None:
        result = runner.invoke(
            app,
            ["generate", "--norm", "iram_general", "--software", "solidworks"],
        )
        assert result.exit_code != 0
        assert "no soportado" in result.output

    def test_generate_invalid_norm(self, tmp_db: Path) -> None:
        result = runner.invoke(
            app,
            ["generate", "--norm", "norma_inexistente", "--software", "librecad"],
        )
        assert result.exit_code != 0

    def test_generate_from_saved_profile(self, tmp_path: Path, populated_db: Path) -> None:
        out = tmp_path / "from_profile.dxf"
        result = runner.invoke(
            app,
            [
                "generate",
                "--norm", "iram_general",
                "--software", "librecad",
                "--output", str(out),
                "--profile", "TestIRAM",
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_generate_missing_saved_profile(self, tmp_path: Path, tmp_db: Path) -> None:
        result = runner.invoke(
            app,
            [
                "generate",
                "--norm", "iram_general",
                "--software", "librecad",
                "--profile", "perfil_que_no_existe",
            ],
        )
        assert result.exit_code != 0
        assert "no encontrado" in result.output

    def test_generate_logs_to_db(self, tmp_path: Path, tmp_db: Path) -> None:
        from cadnorm.core.db import get_generation_log
        out = tmp_path / "log_test.dxf"
        runner.invoke(
            app,
            ["generate", "--norm", "iram_general", "--software", "librecad", "--output", str(out)],
        )
        conn = get_connection(tmp_db)
        log = get_generation_log(conn)
        assert len(log) >= 1
        assert log[0]["software"] == "librecad"


# ---------------------------------------------------------------------------
# profile list / export / import / delete
# ---------------------------------------------------------------------------

class TestProfile:
    def test_list_empty(self, tmp_db: Path) -> None:
        result = runner.invoke(app, ["profile", "list"])
        assert result.exit_code == 0
        assert "No hay perfiles" in result.output

    def test_list_with_profiles(self, populated_db: Path) -> None:
        result = runner.invoke(app, ["profile", "list"])
        assert result.exit_code == 0
        assert "TestIRAM" in result.output

    def test_export_ok(self, tmp_path: Path, populated_db: Path) -> None:
        out = tmp_path / "exported.json"
        result = runner.invoke(
            app,
            ["profile", "export", "--name", "TestIRAM", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "metadata" in data

    def test_export_missing_profile(self, tmp_db: Path) -> None:
        result = runner.invoke(app, ["profile", "export", "--name", "NoExiste"])
        assert result.exit_code != 0
        assert "no encontrado" in result.output

    def test_export_missing_name(self, tmp_db: Path) -> None:
        result = runner.invoke(app, ["profile", "export"])
        assert result.exit_code != 0

    def test_import_ok(self, tmp_path: Path, tmp_db: Path) -> None:
        # Primero exportamos el perfil builtin a un archivo temporal
        profile = load_builtin_profile("iram_general")
        src = tmp_path / "perfil_import.json"
        src.write_text(profile.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

        result = runner.invoke(
            app,
            ["profile", "import", "--input", str(src), "--name", "PruebaImport"],
        )
        assert result.exit_code == 0, result.output
        assert "importado" in result.output

        # Verificar que está en la DB
        list_result = runner.invoke(app, ["profile", "list"])
        assert "PruebaImport" in list_result.output

    def test_import_missing_file(self, tmp_db: Path) -> None:
        result = runner.invoke(
            app,
            ["profile", "import", "--input", "archivo_fantasma.json"],
        )
        assert result.exit_code != 0
        assert "no encontrado" in result.output

    def test_import_missing_flag(self, tmp_db: Path) -> None:
        result = runner.invoke(app, ["profile", "import"])
        assert result.exit_code != 0

    def test_delete_ok(self, populated_db: Path) -> None:
        result = runner.invoke(
            app,
            ["profile", "delete", "--name", "TestIRAM"],
            input="y\n",
        )
        assert result.exit_code == 0, result.output
        assert "eliminado" in result.output

    def test_delete_not_found(self, tmp_db: Path) -> None:
        result = runner.invoke(
            app,
            ["profile", "delete", "--name", "NoExiste"],
            input="y\n",
        )
        assert result.exit_code != 0

    def test_invalid_action(self, tmp_db: Path) -> None:
        result = runner.invoke(app, ["profile", "sync"])
        assert result.exit_code != 0
        assert "no reconocida" in result.output


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

class TestInfo:
    def test_info_all_categories(self) -> None:
        result = runner.invoke(app, ["info", "--norm", "iram_general"])
        assert result.exit_code == 0, result.output
        assert "IRAM" in result.output

    def test_info_category_units(self) -> None:
        result = runner.invoke(
            app, ["info", "--norm", "iram_general", "--category", "units"]
        )
        assert result.exit_code == 0
        assert "metric" in result.output or "mm" in result.output

    def test_info_category_layers(self) -> None:
        result = runner.invoke(
            app, ["info", "--norm", "iram_general", "--category", "layers"]
        )
        assert result.exit_code == 0
        assert "Capas" in result.output

    def test_info_category_scales(self) -> None:
        result = runner.invoke(
            app, ["info", "--norm", "iram_general", "--category", "drawing_scales"]
        )
        assert result.exit_code == 0

    def test_info_invalid_norm(self) -> None:
        result = runner.invoke(app, ["info", "--norm", "norma_xyz"])
        assert result.exit_code != 0

    def test_info_invalid_category(self) -> None:
        result = runner.invoke(
            app, ["info", "--norm", "iram_general", "--category", "categoria_invalida"]
        )
        assert result.exit_code != 0
        assert "no reconocida" in result.output

    def test_info_metadata_category(self) -> None:
        result = runner.invoke(
            app, ["info", "--norm", "iram_general", "--category", "metadata"]
        )
        assert result.exit_code == 0
        assert "IRAM" in result.output


# ---------------------------------------------------------------------------
# Sistema de advertencias normativas
# ---------------------------------------------------------------------------

class TestWarnings:
    def test_warn_param_modified(self) -> None:
        from cadnorm.cli.main import _check_modification_warning, WARN_PARAM_MODIFIED
        w = _check_modification_warning("linear_precision", 2, 3, "IRAM 4-1")
        assert w is not None
        assert WARN_PARAM_MODIFIED in w
        assert "linear_precision" in w
        assert "IRAM 4-1" in w

    def test_no_warn_same_value(self) -> None:
        from cadnorm.cli.main import _check_modification_warning
        w = _check_modification_warning("linear_precision", 2, 2, "IRAM 4-1")
        assert w is None

    def test_no_warn_without_norm_ref(self) -> None:
        from cadnorm.cli.main import _check_modification_warning
        w = _check_modification_warning("some_field", "a", "b", None)
        assert w is None
