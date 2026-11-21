"""Explicit offline test mode; production startup rejects local auth bypasses."""
import os
os.environ["APP_ENV"] = "test"
# Explicit fixture identity keeps migration ownership and the HTTP test actor
# identical, including checkouts that have no owner .env file.
os.environ["ALLOWED_USER_EMAILS"] = "fixture-owner@example.test"
for _flag in ("HEYSOW_ACCOUNTS_ENABLED","HEYSOW_ACCESS_PERIODS_ENABLED","TRANSACTIONAL_MAIL_ENABLED"):
    os.environ[_flag]="false"
for _secret in ("RESEND_API_KEY","RESEND_WEBHOOK_SECRET"):
    os.environ[_secret]=""
# Existing Lead Engine regressions exercise its preserved, enabled implementation.
# Intent-only availability tests explicitly turn this gate off and verify denial.
os.environ['LEAD_ENGINE_AVAILABLE']='true'
# Offline tests must not inherit the owner's live Redis connection. Cache tests
# supply an explicit MockTransport and fixture configuration instead.
os.environ["UPSTASH_REDIS_REST_URL"] = ""
os.environ["UPSTASH_REDIS_REST_TOKEN"] = ""
# Isolated financial tests never inherit live sandbox credentials.
for _key in ("RAZORPAY_KEY_ID","RAZORPAY_KEY_SECRET","RAZORPAY_WEBHOOK_SECRET"):
    os.environ[_key]=""
os.environ["BILLING_ENABLED"]="false"
import pytest


@pytest.fixture(autouse=True)
def isolated_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_LOCAL_ROOT", str(tmp_path / "artifacts"))
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "test.db"))
