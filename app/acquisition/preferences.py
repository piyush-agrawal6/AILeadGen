"""Owned source toggles/budgets; provider credentials and cooldown remain platform state."""
import json
from app.platform.context import organization
from app.database.prospects import now


def load(c):
    org=organization()
    row=c.execute('SELECT configuration_json FROM organization_acquisition_preferences WHERE organization_id=?',(org,)).fetchone()
    data=json.loads(row[0]) if row else {}
    return {key:data[key] for key in ('enabled','budgets') if key in data}


def save(c,actor,values):
    org=organization()
    from app.api.permissions import require_owner
    require_owner(c,actor,org)
    data={key:value for key,value in values.items() if key in ('enabled','budgets')}
    c.execute('''INSERT INTO organization_acquisition_preferences(organization_id,configuration_json,updated_by,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET configuration_json=excluded.configuration_json,
        updated_by=excluded.updated_by,updated_at=excluded.updated_at''',(org,json.dumps(data),actor,now()))
