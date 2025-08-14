import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db


@pytest.fixture(autouse=True)
def _override_db(monkeypatch):
    # Use a temporary SQLite DB for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield
        finally:
            app.dependency_overrides.clear()
            # Ensure engine is disposed so SQLite file handle is released on Windows
            engine.dispose()


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_predict_and_list():
    client = TestClient(app)
    payload = {"amount": 1500, "category": "general", "features": {"foo": "bar"}}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["risk_level"] == "medium"
    assert isinstance(data["id"], int)

    r2 = client.get("/predictions")
    assert r2.status_code == 200
    items = r2.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["risk_level"] in {"low", "medium", "high"}

