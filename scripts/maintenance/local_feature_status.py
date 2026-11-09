"""Owner-authenticated checks against ONLY the private localhost preview.

Never prints credentials, headers or provider text. --check-ai makes one bounded
Vertex request producing an inert review proposal, never a profile/run/email.
"""
import argparse
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from dotenv import dotenv_values
from app.api.security import canonical_request


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-ai',action='store_true');parser.add_argument('--business-ai',action='store_true');parser.add_argument('--mail-health',action='store_true');parser.add_argument('--unpause-mail-to');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];values=dotenv_values(root/'.env')
    c=sqlite3.connect((root/'data/e2e/local-preview/workspace.db').as_uri()+'?mode=ro',uri=True)
    actor=c.execute("SELECT m.user_id FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id WHERE o.slug='planebyte' AND m.status='ACTIVE' AND m.role='OWNER' ORDER BY m.created_at LIMIT 1").fetchone()[0];c.close()
    assert actor in [item.strip().lower() for item in values['ALLOWED_USER_EMAILS'].split(',')]
    def call(path,payload=None,method=None):
        method=method or ('POST' if payload is not None else 'GET');body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b''
        stamp=str(int(time.time()));nonce=secrets.token_hex(24)
        headers={'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical_request(stamp,nonce,method,path,body,actor).encode(),hashlib.sha256).hexdigest(),'Content-Type':'application/json'}
        request=urllib.request.Request('http://127.0.0.1:18790'+path,data=body if payload is not None else None,headers=headers,method=method)
        try:
            with urllib.request.urlopen(request,timeout=40) as response:return response.status,json.loads(response.read())
        except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
        except urllib.error.URLError:return 0,{}
    checks={}
    specifications=[('icp','/api/organization/icps/ai-status',['enabled','configured','can_generate','provider']),('assistant','/api/assistant/status',['enabled','configured','can_use']),('developer','/api/organization/developer/status',['enabled','can_manage','mcp_available']),('company','/api/organization/website-reviews/capabilities',['enabled','can_analyze','ai_enabled','configured']),('sources','/api/acquisition/settings',['features','environment_flags','configured']),('integrations','/api/organization/integrations',['google_sheets_configured','google_sheets_import_enabled']),('safety','/api/workflow/safety',['sending_enabled','scan_paused','email_paused'])]
    specifications=[(name,path,fields+(['webhooks_available'] if name=='developer' else [])) for name,path,fields in specifications]
    for name,path,fields in specifications:
        code,data=call(path);checks[name]={'http':code,**{key:data.get(key) for key in fields if key in data}}
    if args.mail_health or args.unpause_mail_to:
        code,account=call('/api/email/account')
        checks['controlled_mail']={'http':code,**{key:account.get(key) for key in ('status','provider','send_mode','test_recipient','can_send','live_approved','tracking_base_url')}}
        if args.mail_health:
            code,data=call('/api/email/health',{})
            checks['mail_health']={'http':code,'smtp':data.get('smtp'),'imap':data.get('imap')}
        if args.unpause_mail_to:
            if code!=200 or account.get('send_mode')!='test' or account.get('live_approved') or account.get('test_recipient')!=args.unpause_mail_to:
                raise SystemExit('Controlled-mail configuration did not match; no queue was unpaused.')
            code,_=call('/api/automation/controls',{'scan_paused':False,'email_paused':False},'PUT')
            checks['controlled_mail_unpause']={'http':code,'recipient':args.unpause_mail_to}
    if args.check_ai or args.business_ai:
        payload={'mode':'BUSINESS_PROFILE','candidate_count':3} if args.business_ai else {'mode':'DESCRIPTION','candidate_count':1,'prompt':'We provide custom web application engineering. Recommend a customer profile for software companies in the United Kingdom, with CTOs as the decision-makers.'}
        code,data=call('/api/organization/icps/suggest',payload)
        checks['live_vertex_icp']={'http':code,'candidate_count':len(data.get('candidates',[])),'review_required':data.get('review_required'),'profile_created':data.get('profile_created'),'discovery_started':data.get('discovery_started')}
    record={'checks':checks,'production_changed':False,'root_env_changed':False,'real_emails_sent':0,'scope':'Local preview only; complete Phase 6 is not certified.'}
    artifact=root/'data/artifacts/verification/phase6/local-all-features-acceptance.json';artifact.parent.mkdir(exist_ok=True,parents=True);artifact.write_text(json.dumps(record,indent=2))
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
