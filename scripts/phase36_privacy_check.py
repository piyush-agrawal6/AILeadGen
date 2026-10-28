"""Verify signed object access without printing a signed URL or credentials."""
import os,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlsplit,urlunsplit
import requests
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.storage import R2ArtifactStorage
with db_session() as c:
    row=c.execute("SELECT object_key FROM website_captures WHERE status='READY' ORDER BY captured_at DESC LIMIT 1").fetchone()
    if not row:raise SystemExit('No new scan-time screenshot is available for the privacy check yet.')
    key=row[0]
storage=R2ArtifactStorage();signed=storage.client.generate_presigned_url('get_object',Params={'Bucket':storage.bucket,'Key':key},ExpiresIn=60)
parsed=urlsplit(signed);unsigned=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))
try:
    with requests.get(signed,timeout=20,stream=True) as response:signed_status=response.status_code
    with requests.get(unsigned,timeout=20,stream=True) as response:unsigned_status=response.status_code
except Exception as exc:raise SystemExit('Storage privacy probe could not complete: '+type(exc).__name__)
result={'signed_get_status':signed_status,'unsigned_get_status':unsigned_status,'private_access_verified':signed_status==200 and unsigned_status in (400,401,403,404),'account_public_access_settings':'Previously confirmed by user: public r2.dev disabled; no public custom domain.'}
Path('docs/phase36-r2-privacy.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert result['private_access_verified']
