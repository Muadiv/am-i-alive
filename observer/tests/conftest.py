# TEST-001: pytest fixtures for observer tests
import importlib
import os
from pathlib import Path

import pytest

# Get the observer directory for correct path resolution
OBSERVER_DIR = Path(__file__).parent.parent


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database and initialize schema."""
    db_path = tmp_path / "test.db"
    memories_path = tmp_path / "memories"

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("MEMORIES_PATH", str(memories_path))

    import database as db

    importlib.reload(db)
    await db.close_db()
    await db.init_db()

    try:
        yield db
    finally:
        await db.close_db()


@pytest.fixture
async def main_module(test_db, monkeypatch):
    """Reload main module after test database setup."""
    # Change to observer directory so static files can be found
    original_dir = os.getcwd()
    os.chdir(OBSERVER_DIR)
    try:
        import main as main_module

        main_module = importlib.reload(main_module)
        monkeypatch.setattr(main_module, "db", test_db)
        try:
            yield main_module
        finally:
            http_client = getattr(main_module, "_http_client", None)
            if http_client is not None and not http_client.is_closed:
                await http_client.aclose()
    finally:
        os.chdir(original_dir)


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
        ],
    }
