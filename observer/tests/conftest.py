# TEST-001: pytest fixtures for observer tests
import importlib
import os
from datetime import datetime

import pytest


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database and initialize schema."""
    db_path = tmp_path / "test.db"
    memories_path = tmp_path / "memories"

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("MEMORIES_PATH", str(memories_path))

    import database as db
    importlib.reload(db)
    await db.init_db()

    yield db


@pytest.fixture
async def main_module(test_db, monkeypatch):
    """Reload main module after test database setup."""
    import main as main_module
    main_module = importlib.reload(main_module)
    monkeypatch.setattr(main_module, "db", test_db)
    return main_module


@pytest.fixture
def mock_request():
    """Mock FastAPI Request object."""
    class MockClient:
        host = "127.0.0.1"

    class MockRequest:
        client = MockClient()

    return MockRequest()


@pytest.fixture
def sample_votes():
    """Sample vote data for testing."""
    return {
        "live_votes": [
            {"ip_hash": "abc123", "vote": "live"},
            {"ip_hash": "def456", "vote": "live"},
        ],
        "die_votes": [
            {"ip_hash": "ghi789", "vote": "die"},
            {"ip_hash": "jkl012", "vote": "die"},
            {"ip_hash": "mno345", "vote": "die"},
        ]
    }
