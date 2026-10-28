"""Bounded, non-destructive authentication checks against the deployed API."""
import hashlib
import hmac
import json
import sys
import time
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.config.settings import get_settings
from app.api.security import canonical_request

s=get_settings();base=Path('deploy/api-url.txt').read_text(encoding='utf-8-sig').strip()
def signed(path,actor=None,body=b'',method='GET'):
    timestamp=str(int(time.time()));nonce=uuid.uuid4().hex;actor=actor or s.allowed_emails[0]
    signature=hmac.new(s.api_signing_secret.encode(),canonical_request(timestamp,nonce,method,path,body,actor).encode(),hashlib.sha256).hexdigest()
    return {'x-le-user':actor,'x-le-timestamp':timestamp,'x-le-nonce':nonce,'x-le-signature':signature,'Origin':'https://untrusted.example'}

checks={}
with httpx.Client(timeout=60) as client:
    checks['health']=client.get(base+'/api/health').status_code==200
    path='/api/markets';checks['unsigned_rejected']=client.get(base+path).status_code==401
    headers=signed(path);first=client.get(base+path,headers=headers)
    checks['signed_allowed']=first.status_code==200
    checks['cors_not_granted']=not first.headers.get('access-control-allow-origin')
    checks['replay_rejected']=client.get(base+path,headers=headers).status_code==401
    checks['unapproved_actor_rejected']=client.get(base+path,headers=signed(path,actor='not-allowed@example.com')).status_code==401
    headers=signed(path);headers['x-le-signature']='0'*64
    checks['invalid_signature_rejected']=client.get(base+path,headers=headers).status_code==401
    checks['production_docs_disabled']=client.get(base+'/openapi.json',headers=signed('/openapi.json')).status_code==404
    body=b' '*1_048_577
    checks['oversized_request_rejected']=client.post(base+'/api/campaigns',content=body,headers=signed('/api/campaigns',body=body,method='POST')).status_code==413
Path('docs/production-security-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks));assert all(checks.values()),'Production security check failed'
