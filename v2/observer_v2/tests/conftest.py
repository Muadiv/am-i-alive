from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from observer_v2.app import create_app
from observer_v2.storage import SqliteStorage


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "observer_v2_test.db"


@pytest.fixture
def client(database_path: Path) -> TestClient:
    app: FastAPI = create_app(storage=SqliteStorage(str(database_path)))
    with TestClient(app) as test_client:
        yield test_client
