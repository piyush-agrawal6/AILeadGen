from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.mail import tracking
from app.config.settings import get_settings


def test_local_tracking_only_allows_exact_opted_in_development_preview(monkeypatch):
    config=get_settings();monkeypatch.setattr(config,'app_env','development')
    monkeypatch.setattr(tracking,'mail_settings',lambda:SimpleNamespace(tracking_base_url='http://localhost:3000/t'))
    monkeypatch.delenv('HEYSOW_LOCAL_PREVIEW',raising=False)
    with pytest.raises(HTTPException):tracking.tracking_base()
    monkeypatch.setenv('HEYSOW_LOCAL_PREVIEW','true');assert tracking.tracking_base()=='http://localhost:3000/t'
    for url in ('http://localhost:9999/t','http://127.0.0.1:3000/t?next=x','http://169.254.169.254/t','http://localhost:3000/other'):
        monkeypatch.setattr(tracking,'mail_settings',lambda:SimpleNamespace(tracking_base_url=url))
        with pytest.raises(HTTPException):tracking.tracking_base()
    monkeypatch.setattr(config,'app_env','production');monkeypatch.setattr(tracking,'mail_settings',lambda:SimpleNamespace(tracking_base_url='http://localhost:3000/t'))
    with pytest.raises(HTTPException):tracking.tracking_base()
    assert tracking.allowed_url('http://localhost:3000/private') is None
