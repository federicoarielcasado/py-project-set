"""Fixtures compartidas para los tests de CADNorm."""
import json
from pathlib import Path

import pytest

STANDARDS_DIR = Path(__file__).parent.parent / "cadnorm" / "standards"


@pytest.fixture(scope="session")
def schema() -> dict:
    """Carga schema.json una sola vez por sesión de tests."""
    with (STANDARDS_DIR / "schema.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def iram_profile() -> dict:
    """Carga iram_general.json una sola vez por sesión de tests."""
    with (STANDARDS_DIR / "iram_general.json").open(encoding="utf-8") as f:
        return json.load(f)
