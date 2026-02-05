from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from observer_v2.app import create_app
from observer_v2.storage import SqliteStorage


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "observer_v2_test.db"
    app: FastAPI = create_app(storage=SqliteStorage(str(db_path)))
    with TestClient(app) as test_client:
        yield test_client
