"""Real browser/API/worker integration; only the public source is synthetic."""
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
from app.api.organization import create_organization
from app.intent_radar import providers

settings = get_settings()
path = Path(settings.database_path).resolve()
root = Path(__file__).resolve().parents[1]
assert settings.app_env == 'test' and path.is_relative_to(root / 'data/e2e') and not path.exists()
assert os.environ.get('EMAIL_SENDING_ENABLED') == 'false'
path.parent.mkdir(parents=True, exist_ok=True)
c = get_connection(path)
run_migrations(c)
other = create_organization(c, 'founder@leadengine.example', 'Isolated Radar workspace')['organization_id']
disabled = create_organization(c, 'founder@leadengine.example', 'Radar unavailable workspace')['organization_id']
c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id IN (?,?,?)", (PLANEBYTE_ORGANIZATION_ID, other, disabled))
c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id IN (?,?) AND product='INTENT_RADAR'", (PLANEBYTE_ORGANIZATION_ID, other))
from app.platform.workspaces import select_workspace
select_workspace(c, 'founder@leadengine.example', PLANEBYTE_ORGANIZATION_ID)
c.commit()
c.close()

async def fetch(self, offset=0, permit=None, *, feeds=None, comments=False, limit=20, seen_ids=None):
    # Allow the actual cancel API to race a response; no browser route interception.
    for _ in range(10):
        if permit: permit()
        await asyncio.sleep(.1)
    item = providers.normalize({'id':999123,'type':'story','time':int(datetime.now(timezone.utc).timestamp()),'title':'Ask HN: recommend a website development partner?','text':'Looking for a website development tool. How do you compare options?'})
    return {'items':[item],'requests':2,'scanned':1,'next_offset':None,'synthetic':True,'coverage':'Synthetic public-source fixture for integrated browser testing; not live source evidence.'}

providers.HackerNews.fetch = fetch
from app.api.server import app
