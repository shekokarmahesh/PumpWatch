import socket

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(mode="replay", state_dir=tmp_path)


@pytest.fixture
def client(settings, monkeypatch):
    # Any accidental HTTP connection makes the entire replay integration suite fail.
    def reject(*args, **kwargs):
        raise AssertionError("Replay attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", reject)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
