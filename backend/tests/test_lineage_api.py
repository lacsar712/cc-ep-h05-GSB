"""Lineage read-back must match creation input: no fingerprint swap anywhere."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import router
from app.auth import create_access_token
from app.database import Base, get_db

# Two deliberately distinct fingerprints: a-s for dataset, b-s for code.
DATASET_SHA = "a" * 64
CODE_SHA = "b" * 40


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # JSONB not available on SQLite — compile as JSON (same shim as test_state_machine)
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, compiler, **kw):
        return "JSON"

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def headers():
    token = create_access_token("researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


def test_lineage_readback_matches_creation_input(client, headers):
    created = client.post(
        "/api/runs",
        json={
            "project": "p1",
            "name": "lineage-fingerprint-check",
            "dataset_content_sha256": DATASET_SHA,
            "code_commit_sha": CODE_SHA,
            "expected_version": 0,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]

    # Create response itself echoes the fingerprints unswapped
    assert created.json()["dataset_content_sha256"] == DATASET_SHA
    assert created.json()["code_commit_sha"] == CODE_SHA

    # Detail view read-back is not swapped either
    detail = client.get(f"/api/runs/{run_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["dataset_content_sha256"] == DATASET_SHA
    assert detail.json()["code_commit_sha"] == CODE_SHA

    # Lineage read-back matches what was entered at creation
    lineage = client.get(f"/api/runs/{run_id}/lineage", headers=headers)
    assert lineage.status_code == 200, lineage.text
    body = lineage.json()
    assert body["dataset_content_sha256"] == DATASET_SHA
    assert body["code_commit_sha"] == CODE_SHA
