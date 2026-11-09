"""Five owner-approved fixed introductions and one immutable company attachment."""
import hashlib,json,re
from pathlib import Path
from fastapi import HTTPException
from app.mail.contacted import organization
VERSION='v1'
ASSET_ID='PLANEBYTE_CAPABILITIES'
TEMPLATES=json.loads(Path(__file__).with_name('templates.json').read_text())

def render(company,template):
    if not isinstance(company,str) or not company.strip() or len(company)>240 or any(ord(x)<32 for x in company) or '{{' in company or '}}' in company:raise ValueError('A usable company identity is required.')
    if template not in TEMPLATES:raise ValueError('Choose one approved PlaneByte introduction.')
    return {k:v.replace('{{company_name}}',company.strip()) for k,v in TEMPLATES[template].items()}|{'template_id':template,'template_version':VERSION,'outreach_strategy':'FIXED_5','pdf_asset_id':ASSET_ID,'pdf_version':VERSION}

def assign(seed,counts):
    return min(TEMPLATES,key=lambda k:(counts.get(k,0),hashlib.sha256((seed+':'+k).encode()).hexdigest()))

def seed(c):
    from app.platform.context import require_internal_mailbox
    org=require_internal_mailbox().organization_id
    from app.database.prospects import now
    for tid,t in TEMPLATES.items():c.execute("INSERT INTO email_templates(id,name,category,subject,body_text,updated_at,organization_id) VALUES(?,?,'PlaneByte Introduction',?,?,?,?) ON CONFLICT(id) DO NOTHING",(tid,tid,t['subject'],t['body_text'],now(),org))

def asset(c,version=VERSION):
    row=c.execute('SELECT * FROM company_pdf_assets WHERE organization_id=? AND id=? AND version=? AND active=1',(organization(),ASSET_ID,version)).fetchone()
    if not row:raise HTTPException(409,'The approved PlaneByte capabilities PDF is not configured.')
    return dict(row)

def quality(c,pid,body):
    errors=[]
    row=c.execute('SELECT b.name FROM businesses b JOIN pipeline_runs p ON p.id=b.run_id WHERE b.prospect_id=? AND p.campaign_id=? ORDER BY b.id DESC LIMIT 1',(pid,body.get('campaign_id'))).fetchone()
    if not row:return ['The company must belong to the selected campaign.']
    try:expected=render(row['name'],body.get('template_id'))
    except ValueError as e:return [str(e)]
    for key in ('subject','body_text','template_version','outreach_strategy','pdf_asset_id','pdf_version'):
        if expected[key]!=body.get(key):errors.append('Use the approved fixed introduction and company PDF ('+key+').')
    if body.get('report_id'):errors.append('Fixed introductions use the shared company PDF, not a client report.')
    try:asset(c,body.get('pdf_version'))
    except HTTPException as e:errors.append(str(e.detail))
    return errors

def attachment(c,body):
    from app.storage import artifact_storage
    from pypdf import PdfReader
    from io import BytesIO
    a=asset(c,body.get('pdf_version'))
    with artifact_storage().get(a['object_key']) as f:raw=f.read(4_000_001)
    if len(raw)!=a['size_bytes'] or len(raw)>4_000_000 or hashlib.sha256(raw).hexdigest()!=a['sha256']:raise HTTPException(409,'Company PDF asset failed its immutable checksum.')
    reader=PdfReader(BytesIO(raw))
    if reader.is_encrypted or not 3<=len(reader.pages)<=4:raise HTTPException(422,'Approved company PDF must have3–4 pages.')
    return raw,a['filename']

def prepare(c,rid):
    from collections import Counter
    from app.workflows.service import row,select_items
    from app.mail.service import preview
    from app.database.prospects import now
    run=row(c,rid);seed(c);audience=select_items(c,rid);by_id={b['prospect_id']:b for b in audience['items']}
    counts=Counter()
    for r in c.execute('SELECT payload_json FROM outreach_run_items WHERE run_id=?',(rid,)).fetchall():
        tid=json.loads(r[0] or '{}').get('template_id')
        if tid in TEMPLATES:counts[tid]+=1
    for i in c.execute("SELECT * FROM outreach_run_items WHERE run_id=? AND status IN ('QUEUED','PREPARING') ORDER BY created_at,id LIMIT 100",(rid,)).fetchall():
        b=by_id.get(i['prospect_id'])
        if not b or b['disposition']!='READY':
            c.execute('UPDATE outreach_run_items SET status=?,error=?,updated_at=? WHERE id=?',(b['disposition'] if b else 'NEEDS_REVIEW',b['reason'] if b else 'Campaign membership changed.',now(),i['id']));continue
        prior=json.loads(i['payload_json'] or '{}');tid=prior.get('template_id') or assign(i['id'],counts)
        if not prior.get('template_id'):counts[tid]+=1
        body=render(b['name'],tid)|{'to_address':b['recipient'],'campaign_id':run['campaign_id'],'message_type':'FIRST_CONTACT','track_opens':True,'track_clicks':True,'followup_days':0,'preview_nonce':i['id'],'idempotency_key':i['idempotency_key'],'confirmation':'SEND'}
        review=preview(c,i['prospect_id'],run['created_by'],body,allow_disabled=True)
        if review['quality_issues']:raise HTTPException(422,review['quality_issues'])
        body['preview_token']=review['preview_token'];c.execute("UPDATE outreach_run_items SET status='READY',payload_json=?,preview_json=?,report_id=NULL,error=NULL,updated_at=? WHERE id=?",(json.dumps(body),json.dumps(review),now(),i['id']))
    pending=c.execute("SELECT COUNT(*) FROM outreach_run_items WHERE run_id=? AND status IN ('QUEUED','PREPARING')",(rid,)).fetchone()[0]
    c.execute('UPDATE workflow_runs SET status=? WHERE id=?',('PREPARING' if pending else 'DRAFT',rid))
