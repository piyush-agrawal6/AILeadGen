"""Administer only the authenticated active workspace's isolated local beta grant.

Uses the existing signed gateway, live membership/RBAC and organization_products.
No production connection, subscription, membership or onboarding change is made.
"""
import argparse
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def local_grant(c, actor, organization_id, enabled):
    from app.api.organization import require_role, onboarding, products
    from app.database.prospects import now
    from app.platform.context import workspace_scope

    with workspace_scope(c, actor, organization_id):
        require_role(c, actor, organization_id, ('OWNER', 'ADMIN'))
        if enabled and (onboarding(c, organization_id) or {}).get('status') != 'COMPLETED':
            raise ValueError('Complete the existing workspace onboarding before enabling Intent Radar.')
        previous = products(c, organization_id)
        if not previous['LEADGEN']:
            raise ValueError('The local development workspace must retain its Lead Engine entitlement.')
        if previous['INTENT_RADAR'] == enabled:
            return False
        stamp = now()
        changed = c.execute("UPDATE organization_products SET enabled=?,updated_at=? WHERE organization_id=? AND product='INTENT_RADAR'",
                            (int(enabled), stamp, organization_id)).rowcount
        if changed != 1:
            raise ValueError('The workspace product record is missing; no data was changed.')
        c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
                  (str(uuid4()), actor, 'LOCAL_INTENT_RADAR_BETA_CHANGED', 'organization:' + organization_id, 'SUCCESS',
                   json.dumps({'previous_enabled': previous['INTENT_RADAR'], 'enabled': enabled, 'stage': 'Beta', 'scope': 'isolated-local-preview'}), organization_id, stamp))
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'enable', 'disable'))
    parser.add_argument('--actor', required=True, help='Existing authenticated local workspace administrator.')
    parser.add_argument('--organization', required=True, type=UUID, help='Expected active workspace ID; membership is verified server-side.')
    args = parser.parse_args()
    actor = args.actor.strip().lower()
    organization_id = str(args.organization)
    database = ROOT / 'data/e2e/local-preview/workspace.db'
    if not database.is_file():
        parser.error('Start the isolated local preview first. This command never creates or migrates a database.')
    values = dotenv_values(ROOT / '.env')
    allowed = [value.strip().lower() for value in values.get('ALLOWED_USER_EMAILS', '').split(',') if value.strip()]
    secret = values.get('LEADENGINE_API_SIGNING_SECRET')
    if actor not in allowed or not secret:
        parser.error('An existing allowlisted local administrator and configured signed gateway are required.')

    with httpx.Client(base_url='http://127.0.0.1:18790', timeout=10, follow_redirects=False, trust_env=False) as client:
        def read(path):
            timestamp, nonce = str(int(time.time())), str(uuid4())
            canonical = '\n'.join((timestamp, nonce, 'GET', path, hashlib.sha256(b'').hexdigest(), actor))
            response = client.get(path, headers={'x-le-user': actor, 'x-le-timestamp': timestamp, 'x-le-nonce': nonce,
                                                'x-le-signature': hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()})
            response.raise_for_status()
            return response.json()

        workspaces = read('/api/organization/workspaces')
        member = next((item for item in workspaces['items'] if item['organization_id'] == organization_id), None)
        if workspaces['active_organization_id'] != organization_id or not member or member['role'] not in ('OWNER', 'ADMIN'):
            parser.error('The requested workspace must be the authenticated active workspace with an owner/admin membership.')
        access = read('/api/organization/products')
        if access['organization_id'] != organization_id or access['intent_radar']['stage'] != 'Beta':
            parser.error('Restart the isolated local preview backend with its local Beta configuration first.')
        changed = False
        if args.action != 'status':
            from app.config.settings import get_settings
            from app.database.connection import get_connection
            settings = get_settings()
            settings.app_env = 'development'
            settings.allowed_user_emails = ','.join(allowed)
            c = get_connection(database)
            try:
                changed = local_grant(c, actor, organization_id, args.action == 'enable')
                c.commit()
            except Exception:
                c.rollback()
                raise
            finally:
                c.close()
        print(json.dumps({'changed': changed, 'role': member['role'], 'products': read('/api/organization/products')}, indent=2))


if __name__ == '__main__':
    main()
