"""Tests for main.py — offline, lifespan patched to avoid Azure/ChromaDB."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@asynccontextmanager
async def _noop_lifespan(app):
    """No-op lifespan — prevents Azure/ChromaDB connections during testing."""
    yield


@pytest.fixture
def client():
    with patch("api.deps.lifespan", _noop_lifespan):
        sys.modules.pop("main", None)
        import main as _main
        with TestClient(_main.app) as c:
            yield c
    sys.modules.pop("main", None)


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_returns_status_ok(client):
    resp = client.get("/api/health")
    assert resp.json() == {"status": "ok"}


def test_health_no_app_state_dependency(client):
    """Health must succeed without app.state credentials populated.
    If it raises AttributeError, the endpoint illegally reads app.state."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
