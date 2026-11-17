"""Isolated real-signed billing UI fixture. NO Razorpay network or real payments."""
from tests.growth_fixture_server import app,settings,path
from app.database.connection import db_session
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
from pydantic import SecretStr
settings.billing_enabled=True
settings.billing_test_workspaces=PLANEBYTE_ORGANIZATION_ID
settings.razorpay_key_id='rzp_test_synthetic_browser_fixture'
settings.razorpay_key_secret=SecretStr('synthetic-browser-api-secret-only')
settings.razorpay_webhook_secret=SecretStr('synthetic-browser-webhook-secret-only')
# Missing provider mappings intentionally block payment initiation. This verifies
# real backend reads + access controls without pretending provider acceptance.

# Explicit archived-provider fixture; production defaults to Creem.
settings.billing_provider="razorpay"
