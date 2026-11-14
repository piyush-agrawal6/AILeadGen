"""Intent-only real HTTP fixture; retains existing Lead Engine fixture grants."""
from tests.billing_fixture_server import app, settings, path
settings.lead_engine_available=False
from app.database.connection import db_session
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
with db_session() as c:
    c.execute("UPDATE organization_products SET enabled=1 WHERE product='LEADGEN' AND organization_id=?",(PLANEBYTE_ORGANIZATION_ID,))
