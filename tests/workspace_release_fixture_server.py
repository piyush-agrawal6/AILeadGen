"""A real owner, two scoped products, and an unrelated invitation recipient, in a new SQLite database."""
from pathlib import Path
import os
from app.config.settings import get_settings
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.database.connection import db_session
from app.platform.workspaces import select_workspace
settings=get_settings();path=Path(settings.database_path).resolve()
assert settings.app_env=='test' and settings.lead_engine_available and not path.exists() and path.is_relative_to(Path(__file__).resolve().parents[1]/'data/e2e') and os.environ.get('EMAIL_SENDING_ENABLED')=='false'
with db_session() as c:
    run_migrations(c)
    actor='founder@leadengine.example'
    base=create_organization(c,actor,'Browser QA Workspace')['organization_id']
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product IN ('LEADGEN','INTENT_RADAR')",(base,))
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(base,))
    select_workspace(c,actor,base)
from app.api.server import app
