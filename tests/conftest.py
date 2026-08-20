"""Pytest-Konfiguration: Projekt-Root in den Importpfad legen."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── v0.3.01: SQLAlchemy-Stub NUR bei fehlender Installation ──────────────────
# In der Prüf-Sandbox ohne pip macht dieser Minimal-Stub database.models,
# rule_engine, rotation_engine und dashboard_service importierbar. In der
# echten CI ist SQLAlchemy installiert; der Stub wird dann NIE aktiviert und
# alle Tests laufen gegen das echte ORM.
from tests._stub_env import install_sqlalchemy_stub
install_sqlalchemy_stub()

class FakeInk:
    """Minimaler Ink-Stub für reine Logik-Tests (kein SQLAlchemy)."""
    def __init__(self, **kw):
        self.wetness_level   = kw.get("wetness_level", 3)
        self.cleaning_effort = kw.get("cleaning_effort", 3)
        self.has_shimmer     = kw.get("has_shimmer", False)
        self.is_pigment      = kw.get("is_pigment", False)
        self.is_waterproof   = kw.get("is_waterproof", False)
        self.has_sheen       = kw.get("has_sheen", False)
        self.sheen_level     = kw.get("sheen_level", 0)
        self.shading_level   = kw.get("shading_level", 0)
        self.feathering_level= kw.get("feathering_level", 2)
        self.usage_tags      = kw.get("usage_tags", "")
        self.color_hex       = kw.get("color_hex", "#336699")
        self.color_family    = kw.get("color_family", "blue")
        self.id              = kw.get("id", 1)
        self.brand           = kw.get("brand", "TestBrand")
        self.name            = kw.get("name", "TestInk")


import pytest


@pytest.fixture(scope="session", autouse=True)
def _close_database_after_suite():
    """Keine SQLite-/SQLAlchemy-Verbindungen über das Testende hinaus halten."""
    yield
    try:
        from database.db import close_db
        close_db()
    except Exception:
        pass
