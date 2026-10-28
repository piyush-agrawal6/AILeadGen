import pytest
from pydantic import ValidationError
from app.config.settings import Settings


def production(**overrides):
    values = dict(APP_ENV="production", DATABASE_URL="postgresql://localhost/test", LEADENGINE_API_SIGNING_SECRET="s" * 32,
                  ALLOWED_USER_EMAILS="founder@example.com", SCAN_EXECUTOR="gcp", GCP_PROJECT_ID="test-project", GCP_REGION="test-region",
                  R2_ENDPOINT="https://account.r2.cloudflarestorage.com", R2_ACCESS_KEY_ID="key", R2_SECRET_ACCESS_KEY="secret", R2_BUCKET_NAME="private-artifacts")
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_complete_production_configuration():
    assert production().allowed_emails == ["founder@example.com"]


@pytest.mark.parametrize("overrides", [
    {"DATABASE_URL": ""}, {"DATABASE_URL": "sqlite:///local.db"},
    {"LEADENGINE_API_SIGNING_SECRET": "short"}, {"ALLOWED_USER_EMAILS": ""},
    {"AUTH_DISABLED_LOCAL": True}, {"SCAN_EXECUTOR": "local"}, {"GCP_REGION": ""},
    {"R2_ENDPOINT": "http://insecure.example"}, {"R2_SECRET_ACCESS_KEY": ""},
    {"MAX_CITIES_PER_SCAN": 11}, {"MAX_TARGET_LEADS": 1001}, {"MAX_ACTIVE_SCANS": 0},
])
def test_production_rejects_unsafe_or_unbounded_configuration(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_validation_error_hides_secret_values():
    with pytest.raises(ValidationError) as error:
        production(LEADENGINE_API_SIGNING_SECRET="do-not-display-this")
    assert "do-not-display-this" not in str(error.value)
