"""Foundation read models built on existing campaigns, observations and mail."""
import json,uuid
from fastapi import APIRouter,Depends,Query,HTTPException,Request
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
from app.config.locations import Location
from app.api.dependencies import get_db
from app.api.routes.workflows import Run
from app.workflows import history
from app.pipeline.reuse import efficiency
router=APIRouter(prefix='/foundation',tags=['Foundation'])

@router.post('/repeat')
def repeat(body:Run,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    value=history.effective(c,body.model_dump());sig=history.signature(value)
    matches=[dict(r) for r in c.execute('SELECT h.campaign_id,h.captured_at,s.status,s.target_total FROM campaign_settings_snapshots h JOIN scan_campaigns s ON s.id=h.campaign_id WHERE h.signature=? AND h.organization_id=? ORDER BY h.captured_at DESC LIMIT 10',(sig,organization)).fetchall()]
    for m in matches:
        r=c.execute("SELECT COUNT(DISTINCT b.prospect_id) qualified,COUNT(DISTINCT p.business_id) analyzed FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id LEFT JOIN website_profiles p ON p.business_id=b.id WHERE r.campaign_id=? AND r.organization_id=? AND b.processing_status='QUALIFIED'",(m['campaign_id'],organization)).fetchone()
        m.update(dict(r))
    return {'signature':sig,'matches':matches,'recommended':'INCREMENTAL'}

@router.get('/campaigns/{cid}/intelligence')
def intelligence(cid:str,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,organization)).fetchone():raise HTTPException(404,'Campaign not found')
    from app.workflows.campaigns import campaign_summary
    result=campaign_summary(c,cid);result['settings_snapshot']=history.settings(c,cid);result['matching_campaigns']=history.previous(c,cid);result['efficiency']=efficiency(c,cid)
    result['funnel']=dict(c.execute('''SELECT
      COUNT(*) observations,COUNT(DISTINCT b.prospect_id) unique_businesses,
      SUM(CASE WHEN b.is_rejected=1 THEN 1 ELSE 0 END) rejected,
      SUM(CASE WHEN p.reachable=1 THEN 1 ELSE 0 END) reachable_websites,
      COUNT(p.business_id) analyzed_websites
      FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id LEFT JOIN website_profiles p ON p.business_id=b.id WHERE r.campaign_id=? AND r.organization_id=?''',(cid,organization)).fetchone())
    result['funnel'].update(raw_discovered=result['raw_found'],qualified=result['qualified'],email_eligible=result['email_eligible'],manual_contact=result['manual_contact'],needs_review=result['needs_review'],replies=result['replied'])
    result['funnel']['reports_generated']=c.execute("SELECT COUNT(*) FROM client_reports p JOIN businesses b ON b.id=p.business_id JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=? AND p.status='READY' AND p.organization_id=?",(cid,organization)).fetchone()[0]
    scope='SELECT b.prospect_id FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=? AND r.organization_id=?'
    result['funnel']['emails_sent']=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status='SENT' AND test_mode=0 AND organization_id=? AND prospect_id IN ("+scope+')',(organization,cid,organization)).fetchone()[0]
    for state,key in [('MEETING','meetings'),('WON','won')]:result['funnel'][key]=c.execute('SELECT COUNT(*) FROM prospect_sales WHERE prospect_id IN ('+scope+') AND organization_id=? AND prospect_id IN (SELECT prospect_id FROM master_lead_state WHERE sales_state=? AND organization_id=?)',(cid,organization,organization,state,organization)).fetchone()[0]
    source=c.execute('SELECT r.started_at,r.schedule_id,s.name schedule_name FROM workflow_runs r LEFT JOIN automation_schedules s ON s.id=r.schedule_id WHERE r.id=? AND r.organization_id=?',(cid,organization)).fetchone()
    result['source']=dict(source) if source else {'started_at':None,'schedule_id':None,'schedule_name':None}
    if result.get('source_type','OVERTURE')!='OVERTURE':
        acquisition=c.execute('SELECT id,status,origin_json,mapping_json,counts_json FROM acquisition_jobs WHERE campaign_id=? AND organization_id=?',(cid,organization)).fetchone()
        if acquisition:result['acquisition']={**{k:acquisition[k] for k in ('id','status')},'origin':json.loads(acquisition['origin_json']),'mapping':json.loads(acquisition['mapping_json'] or '{}'),'counts':json.loads(acquisition['counts_json'])}
    from app.qualification.diagnostics import campaign_diagnostics,source_funnel
    result['qualification_diagnostics']=campaign_diagnostics(c,cid)
    result['historical_assessment_metrics']={'funnel':result['funnel'],'efficiency':result['efficiency']}
    result['funnel']=source_funnel(result)
    return result

@router.get('/campaigns/{cid}/qualification')
def qualification(request:Request,cid:str,reason:str=Query('',max_length=100),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,organization)).fetchone():raise HTTPException(404,'Campaign not found')
    from app.workflows.campaigns import campaign
    campaign(c,cid)
    where='r.campaign_id=? AND r.organization_id=?';args=[cid,organization]
    if reason:where+=' AND b.rejection_reason=?';args.append(reason)
    base=' FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE '+where
    total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0];items=[]
    for row in c.execute('SELECT b.id,b.name,b.processing_status,b.rejection_reason,b.source_tags_json'+base+' ORDER BY b.id LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
        item=dict(row);item['qualification']=json.loads(item.pop('source_tags_json') or '{}').get('qualification',{});items.append(item)
    return {'items':items,'total':total,'page':page,'page_size':page_size}

@router.get('/campaigns/{cid}/comparison')
def comparison(cid:str,previous:str|None=Query(None,max_length=36),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),state:str=Query('',max_length=30),c=Depends(get_db,scope='function')):
    result=history.compare(c,cid,previous);items=result.pop('businesses');items=[r for r in items if not state or r['state']==state]
    return {**result,'items':items[(page-1)*page_size:page*page_size],'total':len(items),'page':page,'page_size':page_size}

@router.get('/campaigns/{cid}/export')
def export_campaign(cid:str,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,organization)).fetchone():raise HTTPException(404,'Campaign not found')
    import csv,io
    from fastapi.responses import Response
    from app.workflows.campaigns import audience
    from app.exports.phase3 import safe_cell
    data=audience(c,cid);out=io.StringIO();writer=csv.writer(out)
    columns=['name','city','country','vertical','commercial_fit','recipient','phone','disposition']
    writer.writerow(columns)
    for b in data['items']:writer.writerow([safe_cell(b.get(k) or '') for k in columns])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="campaign-{cid}.csv"','Cache-Control':'no-store'})

@router.get('/cache')
def cache_health():
    from app.api.read_cache import read_cache
    return read_cache.health()

@router.get('/countries')
def countries():
    from app.config.locations import countries as dataset
    return dataset()

@router.get('/locations')
async def locations(q:str=Query(min_length=3,max_length=120),country:str=Query(min_length=2,max_length=3),c=Depends(get_db,scope='function')):
    from app.config.locations import search
    try:return await search(c,q,country)
    except ValueError:raise HTTPException(422,'Choose a valid country code.') from None

class MarketGroup(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    locations:list[Location]=Field(min_length=1,max_length=10)

@router.get('/market-groups')
def groups(request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    return [{**dict(r),'locations':json.loads(r['locations_json'])} for r in c.execute('SELECT * FROM saved_market_groups WHERE organization_id=? ORDER BY name LIMIT 100',(organization,)).fetchall()]

@router.post('/market-groups',status_code=201)
def save_group(body:MarketGroup,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    key=str(uuid.uuid4());c.execute('INSERT INTO saved_market_groups(id,name,locations_json,created_by,created_at,organization_id) VALUES(?,?,?,?,?,?)',(key,body.name,json.dumps([loc.model_dump() for loc in body.locations]),request.state.user_email,history.now(),organization))
    return {'id':key}

@router.delete('/market-groups/{gid}')
def delete_group(gid:str,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    c.execute('DELETE FROM saved_market_groups WHERE id=? AND organization_id=?',(gid,organization));return {'deleted':True}

@router.get('/me')
def me(request:Request,c=Depends(get_db,scope='function')):
    from app.api.permissions import role
    return {'email':request.state.user_email,'role':role(c,request.state.user_email)}

@router.get('/roles')
def roles(request:Request,c=Depends(get_db,scope='function')):
    from app.api.permissions import require_owner
    from app.platform.context import organization
    org=organization(request.state.organization_id)
    require_owner(c,request.state.user_email,org)
    owner_count=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND role='OWNER' AND status='ACTIVE'",(org,)).fetchone()[0]
    return [{'email':r['user_id'],'role':'OPERATOR' if r['role']=='MEMBER' else r['role'],'primary_owner':r['role']=='OWNER' and r['status']=='ACTIVE' and owner_count==1,'status':r['status']} for r in c.execute("SELECT user_id,role,status FROM organization_memberships WHERE organization_id=? ORDER BY created_at,user_id LIMIT 200",(org,)).fetchall()]

class RoleChange(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email:str=Field(max_length=254)
    role:Literal['OWNER','ADMIN','OPERATOR','MEMBER','VIEWER']

@router.put('/roles')
def set_role(body:RoleChange,request:Request,c=Depends(get_db,scope='function')):
    from app.api.permissions import require_owner
    from app.api.organization import membership_role
    from app.config.settings import get_settings
    from app.platform.context import organization
    org=organization(request.state.organization_id)
    require_owner(c,request.state.user_email,org)
    target=body.email.strip().lower()
    allowed=get_settings().allowed_emails
    # Allow changing the role of any existing active workspace member, while
    # keeping brand-new direct additions restricted to allowlisted accounts
    # (other teammates must join through verified invitations).
    if target not in allowed and not membership_role(c,target,org):
        raise HTTPException(422,'Invite this teammate first before assigning a workspace role.')
    from app.platform.memberships import change_role
    return change_role(c,request.state.user_email,target,body.role)

_AUDIT_BLOCKED_KEYS=('secret','token','password','api_key','key_hash','authorization','cookie','credential','private_key','client_secret','challenge_hash','access_token','refresh_token','signature')


def _scrub_audit_value(val):
    import re
    if isinstance(val,dict):
        return {k:('[redacted]' if any(b in str(k).lower() for b in _AUDIT_BLOCKED_KEYS) else _scrub_audit_value(v)) for k,v in val.items()}
    if isinstance(val,list):
        return [_scrub_audit_value(item) for item in val]
    if isinstance(val,str):
        if re.search(r'(?:pbk_[a-f0-9-]{16,}|ghp_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{16,}|Bearer\s+\S+)',val):
            return '[redacted]'
    return val


def _safe_audit_details(raw):
    if not raw:return None
    try:
        parsed=json.loads(raw) if isinstance(raw,str) else raw
    except Exception:
        return None
    if not isinstance(parsed,dict):return None
    return _scrub_audit_value(parsed)

def _audit_query(organization:str,action:str|None,actor:str|None,result:str|None,search:str|None,from_date:str|None,to_date:str|None):
    where=['organization_id=?'];args=[organization]
    if action and action!='all':
        where.append('LOWER(action) LIKE ?');args.append('%'+action.strip().lower()+'%')
    if actor and actor.strip():
        where.append('LOWER(actor) LIKE ?');args.append('%'+actor.strip().lower()+'%')
    if result and result!='all':
        if result.upper()=='FAILED':
            where.append("result<>'SUCCESS'")
        else:
            where.append('UPPER(result)=?');args.append(result.strip().upper())
    if search and search.strip():
        q='%'+search.strip().lower()+'%'
        where.append('(LOWER(action) LIKE ? OR LOWER(actor) LIKE ? OR LOWER(entity) LIKE ? OR LOWER(result) LIKE ?)')
        args.extend([q,q,q,q])
    if from_date and from_date.strip():
        where.append('created_at>=?');args.append(from_date.strip()[:32])
    if to_date and to_date.strip():
        val=to_date.strip()[:32]
        if len(val)==10:val=val+'T23:59:59+00:00'
        where.append('created_at<=?');args.append(val)
    return ' AND '.join(where),args

@router.get('/audit')
def audit(
    request:Request,
    page:int=Query(1,ge=1),
    page_size:int=Query(25,ge=1,le=100),
    action:str|None=None,
    actor:str|None=None,
    result:str|None=None,
    search:str|None=None,
    from_date:str|None=None,
    to_date:str|None=None,
    c=Depends(get_db,scope='function'),
):
    from app.api.permissions import role
    if role(c,request.state.user_email) not in ('OWNER','ADMIN'):raise HTTPException(403,'Audit history requires owner or administrator access.')
    organization=request.state.organization_id
    where_sql,args=_audit_query(organization,action,actor,result,search,from_date,to_date)
    rows=c.execute(f'SELECT id,actor,action,entity,result,details_json,created_at FROM audit_log WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?',(*args,page_size,(page-1)*page_size)).fetchall()
    total=c.execute(f'SELECT COUNT(*) FROM audit_log WHERE {where_sql}',tuple(args)).fetchone()[0]
    items=[{
        'id':r['id'],
        'actor':r['actor'],
        'action':r['action'],
        'entity':r['entity'],
        'result':r['result'],
        'details':_safe_audit_details(r['details_json']),
        'created_at':r['created_at'],
    } for r in rows]
    return {'items':items,'total':total,'page':page,'page_size':page_size}

@router.get('/audit/export')
def audit_export(
    request:Request,
    format:Literal['csv','json']='csv',
    action:str|None=None,
    actor:str|None=None,
    result:str|None=None,
    search:str|None=None,
    from_date:str|None=None,
    to_date:str|None=None,
    c=Depends(get_db,scope='function'),
):
    import csv,io
    from fastapi.responses import Response
    from app.api.permissions import role
    if role(c,request.state.user_email) not in ('OWNER','ADMIN'):raise HTTPException(403,'Audit export requires owner or administrator access.')
    organization=request.state.organization_id
    where_sql,args=_audit_query(organization,action,actor,result,search,from_date,to_date)
    rows=c.execute(f'SELECT id,created_at,actor,action,entity,result,details_json FROM audit_log WHERE {where_sql} ORDER BY created_at DESC LIMIT 1000',tuple(args)).fetchall()
    records=[{
        'id':r['id'],
        'created_at':r['created_at'],
        'actor':r['actor'],
        'action':r['action'],
        'entity':r['entity'],
        'result':r['result'],
        'details':_safe_audit_details(r['details_json']),
    } for r in rows]
    if format=='json':
        return Response(content=json.dumps({'items':records,'count':len(records)},indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="planebyte-audit-log.json"','Cache-Control':'no-store'})
    buf=io.StringIO()
    writer=csv.DictWriter(buf,fieldnames=['id','created_at','actor','action','entity','result','details'])
    writer.writeheader()
    for rec in records:
        writer.writerow({**rec,'details':json.dumps(rec['details']) if rec['details'] else ''})
    return Response(content=buf.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="planebyte-audit-log.csv"','Cache-Control':'no-store'})

@router.get('/quality')
def data_quality(c=Depends(get_db,scope='function')):
    from app.workflows.quality import quality,reviews
    return {**quality(c),'needs_review':reviews(c,size=1)['total']}

@router.get('/contacts/{pid}')
def contact_evidence(pid:str,c=Depends(get_db,scope='function')):
    from app.workflows.quality import contacts
    return contacts(c,pid)

class Person(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=150)
    role:str=Field('',max_length=150)
    profile_url:str=Field('',max_length=500)
    work_email:str=Field('',max_length=254)
    confidence:Literal['HIGH','MEDIUM','LOW','UNKNOWN']='UNKNOWN'
    source_url:str=Field(min_length=5,max_length=600)

@router.post('/contacts/{pid}/people',status_code=201)
def person(pid:str,body:Person,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if not c.execute('SELECT 1 FROM prospects WHERE id=? AND organization_id=?',(pid,organization)).fetchone():raise HTTPException(404,'Prospect not found.')
    from app.reports.data import public_url
    from app.mail.service import address
    if not public_url(body.source_url) or body.profile_url and not public_url(body.profile_url):raise HTTPException(422,'Use a public source URL for this contact evidence.')
    email=address(body.work_email) if body.work_email else None
    key=str(uuid.uuid4());c.execute('INSERT INTO contact_people(id,prospect_id,name,role,profile_url,work_email,confidence,source_url,created_at,created_by,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(key,pid,body.name,body.role,body.profile_url or None,email,body.confidence,body.source_url,history.now(),request.state.user_email,organization))
    return {'id':key,'provenance':'MANUALLY_RECORDED_SOURCE'}

@router.post('/contacts/{contact_id}/validate-domain')
def validate_domain(contact_id:int,request:Request,c=Depends(get_db,scope='function')):
    from app.platform.contact_verification import validate_domain as check
    return check(c,contact_id)

@router.get('/reviews')
def review_list(search:str=Query('',max_length=150),reason:str=Query('',max_length=80),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
    from app.workflows.quality import reviews
    return reviews(c,search,reason,page,page_size)

class ManualReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    business_id:int=Field(ge=1)
    reason:Literal['Uncertain email','Insufficient findings','Report quality failure','Pitch mismatch','Ambiguous contact','Website ownership uncertainty','Provider conflict','Analysis failure','Manual verification']
    note:str=Field(min_length=5,max_length=1500)

@router.post('/reviews',status_code=201)
def new_review(body:ManualReview,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    b=c.execute('SELECT b.prospect_id,r.campaign_id FROM businesses b LEFT JOIN pipeline_runs r ON r.id=b.run_id WHERE b.id=? AND b.prospect_id IN (SELECT id FROM prospects WHERE organization_id=?)',(body.business_id,organization)).fetchone()
    if not b:raise HTTPException(404,'Business observation not found.')
    key=str(uuid.uuid4());c.execute('INSERT INTO review_cases(id,prospect_id,business_id,campaign_id,reason,evidence_json,created_at,organization_id) VALUES(?,?,?,?,?,?,?,?)',(key,b['prospect_id'],body.business_id,b['campaign_id'],body.reason,json.dumps({'note':body.note,'recorded_by':request.state.user_email}),history.now(),organization))
    if b['prospect_id']:
        c.execute("UPDATE master_lead_state SET contact_state='NEEDS_REVIEW',manual_reason='Owner requested review',updated_at=? WHERE prospect_id=? AND organization_id=?",(history.now(),b['prospect_id'],organization))
        c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM master_lead_state WHERE organization_id=?)",(b['prospect_id'],organization))
    return {'id':key}

@router.get('/reviews/{rid}')
def review_detail(rid:str,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    r=c.execute('SELECT * FROM review_cases WHERE id=? AND organization_id=?',(rid,organization)).fetchone()
    if not r:raise HTTPException(404,'Review evidence has not been recorded for this item.')
    result=dict(r);result['evidence']=json.loads(result.pop('evidence_json'))
    ids=result['evidence'].get('candidate_prospect_ids',[])
    result['candidates']=[dict(x) for x in c.execute('SELECT id,lead_status,first_seen_at,last_seen_at FROM prospects WHERE id IN ('+','.join('?' for _ in ids)+') AND organization_id=?',[*ids,organization]).fetchall()] if ids else []
    return result

class Resolution(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['ACKNOWLEDGE','IGNORE','KEEP_SEPARATE']
    note:str=Field(min_length=5,max_length=1000)

@router.post('/reviews/{rid}/resolve')
def resolve(rid:str,body:Resolution,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    r=c.execute('SELECT * FROM review_cases WHERE id=? AND organization_id=?',(rid,organization)).fetchone()
    if body.action=='KEEP_SEPARATE':
        if not r or not r['business_id'] or r['reason']!='Identity conflict':raise HTTPException(422,'Keep Separate requires a recorded identity conflict.')
        from app.database.repositories import BusinessRepository
        from app.workflows.duplicates import keep_separate
        keep_separate(c,BusinessRepository(c).get_by_id(r['business_id']),request.state.user_email,organization=organization)
    c.execute("INSERT INTO review_cases(id,reason,evidence_json,status,resolution,created_at,resolved_at,resolved_by,organization_id) VALUES(?,'Manual verification','{}','RESOLVED',?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status='RESOLVED',resolution=excluded.resolution,resolved_at=excluded.resolved_at,resolved_by=excluded.resolved_by WHERE organization_id=?",(rid,body.action+': '+body.note,history.now(),history.now(),request.state.user_email,organization,organization))
    return {'resolved':True,'delivery_blocks_preserved':True}

class Merge(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_id:str=Field(max_length=36)
    target_id:str=Field(max_length=36)
    confirmation:Literal['MERGE']
    review_id:str|None=Field(None,max_length=80)

@router.post('/duplicates/merge')
def merge_duplicates(body:Merge,request:Request,c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    from app.api.permissions import require_owner
    from app.workflows.duplicates import merge
    require_owner(c,request.state.user_email)
    result=merge(c,body.source_id,body.target_id,request.state.user_email)
    if body.review_id:
        case=c.execute('SELECT * FROM review_cases WHERE id=? AND organization_id=?',(body.review_id,organization)).fetchone()
        if not case:raise HTTPException(404,'Review case not found.')
        candidates=json.loads(case['evidence_json']).get('candidate_prospect_ids',[])
        if not {body.source_id,body.target_id}<=set(candidates):raise HTTPException(422,'Choose the identities supported by this review evidence.')
        if case['business_id']:
            from app.database.repositories import BusinessRepository
            from app.database.prospects import ProspectRepository
            b=BusinessRepository(c).get_by_id(case['business_id']);ProspectRepository(c).observe(b,case['campaign_id'],request.state.user_email,organization=organization)
            c.execute("UPDATE businesses SET is_rejected=0,rejection_reason=NULL,processing_status='DISCOVERED' WHERE id=?",(b.id,))
        c.execute("UPDATE review_cases SET status='RESOLVED',resolution='OWNER_CONFIRMED_MERGE',resolved_at=?,resolved_by=? WHERE id=? AND organization_id=?",(history.now(),request.state.user_email,body.review_id,organization))
    return result

@router.get('/usage')
def usage(request:Request,days:int=Query(7,ge=1,le=30),c=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    from datetime import datetime,timedelta,timezone
    start=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    result={}
    queries={
        'campaigns':('SELECT COUNT(*) FROM scan_campaigns WHERE created_at>=? AND organization_id=?',(start,organization)),
        'discovered':('SELECT COALESCE(SUM(raw_found),0) FROM pipeline_runs WHERE started_at>=? AND organization_id=?',(start,organization)),
        'new_master_leads':('SELECT COUNT(*) FROM prospects WHERE first_seen_at>=? AND organization_id=?',(start,organization)),
        'reports':("SELECT COUNT(*) FROM client_reports WHERE status='READY' AND created_at>=? AND organization_id=?",(start,organization)),
        'emails':("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status='SENT' AND test_mode=0 AND sent_at>=? AND organization_id=?",(start,organization)),
        'worker_runtime_seconds':('SELECT SUM(runtime_seconds) FROM worker_attempts WHERE started_at>=?',(start,))
    }
    for key,(sql,args) in queries.items():result[key]=c.execute(sql,args).fetchone()[0]
    result['analysis_operations']=[dict(r) for r in c.execute('SELECT analyzer,operation,COUNT(*) count FROM analysis_operations WHERE recorded_at>=? GROUP BY analyzer,operation',(start,)).fetchall()]
    return {'days':days,**result,'includes_estimated_costs':False}

@router.get('/health')
def system_health(c=Depends(get_db,scope='function')):
    from app.workflows.health import health
    return health(c)

from app.workflows.configuration import FoundationSettings
@router.get('/settings')
def foundation_settings(c=Depends(get_db,scope='function')):
    from app.workflows.configuration import load
    return load(c).model_dump()

@router.put('/settings')
def edit_foundation_settings(body:FoundationSettings,request:Request,c=Depends(get_db,scope='function')):
    from app.workflows.configuration import save
    from app.api.permissions import require_owner
    require_owner(c,request.state.user_email);save(c,body,request.state.user_email)
    return {'saved':True,'existing_campaign_snapshots_unchanged':True,'automation_activated':False}

@router.post('/emergency/{kind}/pause')
def emergency_pause(kind:Literal['scan','email'],request:Request,c=Depends(get_db,scope='function')):
    from app.api.permissions import require_owner
    require_owner(c,request.state.user_email)
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)')
    field='scan_paused' if kind=='scan' else 'email_paused'
    c.execute('UPDATE automation_controls SET '+field+"=1,pause_reason='OWNER_EMERGENCY_PAUSE',updated_at=? WHERE id=1",(history.now(),))
    return {'paused':kind,'queue_preserved':True,'inbox_sync_preserved':True}
