from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'apps' / 'api' / 'test_app.db'}"

from app.main import app  # noqa: E402
from app.db import init_db, get_session  # noqa: E402
from app.demo_store import seed_demo_database  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    init_db()
    for session in get_session():
        seed_demo_database(session)
    with TestClient(app) as test_client:
        yield test_client
