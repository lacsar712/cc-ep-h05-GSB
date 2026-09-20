"""血缘读回必须与新建时录入的指纹一致，不得左右交换。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app


# 两枚差异明显的指纹：数据集全 a，代码提交全 b（均为合法 hex）
DATASET_SHA = "a" * 64
CODE_SHA = "b" * 40


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, compiler, **kw):
        return "JSON"

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture()
def auth_headers():
    token = create_access_token("researcher", "researcher")
    return {"Authorization": f"Bearer {token}"}


def _create_run(client, headers):
    resp = client.post(
        "/api/runs",
        json={
            "project": "p1",
            "name": "lineage-alignment",
            "dataset_content_sha256": DATASET_SHA,
            "code_commit_sha": CODE_SHA,
            "description": None,
            "expected_version": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_lineage_fingerprints_match_create_input(client, auth_headers):
    created = _create_run(client, auth_headers)
    run_id = created["id"]

    lineage = client.get(f"/api/runs/{run_id}/lineage", headers=auth_headers)
    assert lineage.status_code == 200, lineage.text
    body = lineage.json()

    # 血缘读回与录入一致，字段不得错位
    assert body["dataset_content_sha256"] == DATASET_SHA
    assert body["code_commit_sha"] == CODE_SHA

    # 两枚指纹必须仍可明确区分（未被对调）
    assert body["dataset_content_sha256"] != body["code_commit_sha"]
    assert set(body["dataset_content_sha256"]) == {"a"}
    assert set(body["code_commit_sha"]) == {"b"}


def test_lineage_matches_run_detail(client, auth_headers):
    created = _create_run(client, auth_headers)
    run_id = created["id"]

    detail = client.get(f"/api/runs/{run_id}", headers=auth_headers).json()
    lineage = client.get(f"/api/runs/{run_id}/lineage", headers=auth_headers).json()

    # 详情页与血缘页对同一字段给出完全一致的值
    assert lineage["dataset_content_sha256"] == detail["dataset_content_sha256"]
    assert lineage["code_commit_sha"] == detail["code_commit_sha"]
    assert lineage["dataset_content_sha256"] == DATASET_SHA
    assert lineage["code_commit_sha"] == CODE_SHA
