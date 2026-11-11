"""Read-only signed inspection of existing local preview; never prints credentials."""
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
values = dotenv_values(ROOT/'.env')
actor = (values.get('ALLOWED_USER_EMAILS') or '').split(',')[0].strip().lower()
secret = values.get('LEADENGINE_API_SIGNING_SECRET')
assert actor and secret, 'Existing approved local gateway configuration required.'
results = {}
with httpx.Client(base_url='http://127.0.0.1:18790', timeout=15, trust_env=False) as client:
    for path in ('/api/organization/products', '/api/intent-radar/capabilities', '/api/intent-radar/sources/configurations', '/api/intent-radar/sources/health'):
        stamp, nonce = str(int(time.time())), str(uuid.uuid4())
        message = '\n'.join((stamp, nonce, 'GET', path, hashlib.sha256(b'').hexdigest(), actor))
        response = client.get(path, headers={'x-le-user': actor, 'x-le-timestamp': stamp,
            'x-le-nonce': nonce, 'x-le-signature': hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()})
        data = response.json()
        # Capability/status metadata only; do not publish owner/profile/source records.
        if path.endswith('capabilities'):
            result = {'sources': [{k: source.get(k) for k in ('id','name','state','coverage')} for source in data.get('sources', [])],
                'source_count': len(data.get('sources', [])), 'stage': data.get('stage'), 'usage': data.get('usage')}
        elif path.endswith('configurations'):
            result = {'configuration_count': len(data.get('items', []))}
        elif path.endswith('products'):
            result = {'lead_engine': data.get('lead_engine'), 'intent_radar': data.get('intent_radar')}
        else:
            result = data if response.status_code != 200 else {'items': data.get('items', [])}
        results[path] = {'http_status': response.status_code, 'result': result}
print(json.dumps(results, indent=2))
