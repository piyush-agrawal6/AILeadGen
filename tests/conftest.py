"""Explicit offline test mode; production startup rejects local auth bypasses."""
import os
os.environ["APP_ENV"] = "test"
import pytest


@pytest.fixture(autouse=True)
def isolated_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_LOCAL_ROOT", str(tmp_path / "artifacts"))
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "test.db"))
