from app.mail.limits import MAX_PER_HOUR,MAX_PER_DAY,MIN_SPACING_SECONDS
from typing import Literal
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
import json
from app.automation.settings import effective_settings,save_targets
from app.api.dependencies import get_db
from app.database.prospects import now
from app.automation.service import CONTACT_STATES, SALES_STATES
from app.mail.config import mail_settings

router=APIRouter(prefix='/automation',tags=['Automation'])

from app.api.schemas.automation import CustomerSummary

@router.get('/summary',response_model=CustomerSummary)
def summary(request:Request,response:Response,conn=Depends(get_db,scope='function')):
    from app.automation.views import customer_summary
    response.headers['Cache-Control']='private, no-store'
    return customer_summary(conn,request.state.organization_id)

class Controls(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scan_paused:bool
    email_paused:bool

@router.put('/controls')
def controls(body:Controls,conn=Depends(get_db,scope='function')):
    conn.execute('UPDATE automation_controls SET scan_paused=?,email_paused=?,updated_at=? WHERE id=1',(int(body.scan_paused),int(body.email_paused),now()))
    return {'saved':True}

@router.get('/markets')
def markets(page:int=Query(1,ge=1),conn=Depends(get_db,scope='function')):
    return [dict(r) for r in conn.execute('SELECT * FROM scan_markets ORDER BY country,city,vertical LIMIT 100 OFFSET ?',((page-1)*100,)).fetchall()]

@router.post('/markets/{market_id}/{action}')
def market_action(market_id:str,action:Literal['pause','enable','prioritize'],conn=Depends(get_db,scope='function')):
    if action=='prioritize':conn.execute('UPDATE scan_markets SET priority=priority+1,updated_at=? WHERE id=?',(now(),market_id))
    else:conn.execute('UPDATE scan_markets SET enabled=?,updated_at=? WHERE id=?',(int(action=='enable'),now(),market_id))
    return {'saved':True}

@router.get('/master-leads')
def master_leads(search:str=Query('',max_length=200),tab:Literal['all','today','ready','queued','waiting','replied','manual','connected','bounced','meeting','proposal','won','lost','rejected','dnc']='all',
                 contact_state:str=Query('',max_length=40),sales_state:str=Query('',max_length=40),
                 country:str=Query('',max_length=100),city:str=Query('',max_length=100),vertical:str=Query('',max_length=100),
                 business_scale:str=Query('',max_length=40),commercial_fit:Literal['','HIGH','MEDIUM','LOW','UNKNOWN']='',opportunity:Literal['','WEBSITE','SEO','SECURITY']='',
                 email_availability:Literal['','yes','no']='',social_availability:Literal['','yes','no']='',
                 discovered_from:str=Query('',max_length=40),discovered_to:str=Query('',max_length=40),assigned_to:str=Query('',max_length=254),list_id:str=Query('',max_length=36),
                 campaign_id:str=Query('',max_length=36),minimum_score:int=Query(0,ge=0,le=100),sort:Literal['newest','name','score','last_touch']='newest',
                 page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),request:Request=None,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    from app.automation.views import search as find
    if contact_state and contact_state not in CONTACT_STATES:raise HTTPException(422,'Invalid contact state')
    if sales_state and sales_state not in SALES_STATES:raise HTTPException(422,'Invalid sales state')
    filters={k:v for k,v in locals().items() if k not in ('conn','find','page','page_size','tab','request','organization')}
    return find(conn,filters,tab,page,page_size,organization=organization)

class State(BaseModel):
    model_config=ConfigDict(extra='forbid')
    contact_state:str
    sales_state:str

@router.put('/master-leads/{pid}/state')
def state(pid:str,body:State,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    if body.contact_state not in CONTACT_STATES or body.sales_state not in SALES_STATES:raise HTTPException(422,'Invalid lead state')
    previous=conn.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=? AND organization_id=?',(pid,organization)).fetchone()
    if not previous:raise HTTPException(404,'Lead not found')
    if previous['contact_state']=='UNSUBSCRIBED' and body.contact_state!='UNSUBSCRIBED':raise HTTPException(409,'An unsubscribe cannot be removed through lead state editing.')
    if previous['contact_state']=='DO_NOT_CONTACT' and body.contact_state!='DO_NOT_CONTACT':
        from app.api.permissions import require_owner
        require_owner(conn,request.state.user_email)
    from app.sales.service import activity
    conn.execute('UPDATE master_lead_state SET contact_state=?,sales_state=?,updated_at=? WHERE prospect_id=? AND organization_id=?',(body.contact_state,body.sales_state,now(),pid,organization))
    if body.contact_state=='NEEDS_REVIEW':conn.execute("UPDATE master_lead_state SET manual_reason='Owner requested review' WHERE prospect_id=? AND organization_id=?",(pid,organization))
    activity(conn,pid,request.state.user_email,'MASTER_STATE_CHANGED',body.model_dump())
    if body.contact_state in ('DO_NOT_CONTACT','UNSUBSCRIBED') or body.sales_state in ('REJECTED','NOT_INTERESTED','LOST','WON','REPLIED','MEETING','PROPOSAL'):
        conn.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM master_lead_state WHERE organization_id=?)",(pid,organization))
    if body.sales_state in ('CONTACTED','REPLIED','MEETING','PROPOSAL','WON','LOST','NOT_INTERESTED','REJECTED'):
        from app.database.prospects import ProspectRepository
        ProspectRepository(conn).workflow(pid,request.state.user_email,lead_status='NOT_INTERESTED' if body.sales_state=='REJECTED' else body.sales_state,organization=organization)
    if body.contact_state=='DO_NOT_CONTACT':
        from app.database.prospects import ProspectRepository
        ProspectRepository(conn).workflow(pid,request.state.user_email,lead_status='DO_NOT_CONTACT',organization=organization)
    return {'saved':True}

@router.post('/markets/{market_id}/scan-now')
async def scan_now(market_id:str,conn=Depends(get_db,scope='function')):
    market=conn.execute('SELECT * FROM scan_markets WHERE id=?',(market_id,)).fetchone()
    if not market:raise HTTPException(404,'Market not found')
    from app.api.services.scan_manager import scan_manager
    rid=await scan_manager.create_and_start_scan(market=market['city']+', '+market['country'],vertical=market['vertical'],target=mail_settings().daily_qualified_lead_target)
    return {'run_id':rid}

@router.post('/master-leads/{pid}/manual/{action}')
def manual_contact(pid:str,action:Literal['called','social-contacted','connected'],request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    if not conn.execute('SELECT 1 FROM master_lead_state WHERE prospect_id=? AND organization_id=?',(pid,organization)).fetchone():raise HTTPException(404,'Lead not found')
    from app.sales.service import activity,ensure
    ensure(conn,pid)
    activity(conn,pid,request.state.user_email,{'called':'CALL','social-contacted':'SOCIAL_OUTREACH','connected':'CONNECTED_MANUALLY'}[action])
    conn.execute('UPDATE prospect_sales SET last_contact_at=? WHERE prospect_id=? AND organization_id=?',(now(),pid,organization))
    if action=='connected':conn.execute("UPDATE master_lead_state SET contact_state='CONNECTED_MANUALLY',updated_at=? WHERE prospect_id=? AND organization_id=?",(now(),pid,organization))
    conn.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM master_lead_state WHERE organization_id=?)",(pid,organization))
    return {'saved':True}


class Targets(BaseModel):
    model_config=ConfigDict(extra='forbid')
    daily_qualified_lead_target:int=Field(100,ge=1,le=1000)
    daily_email_target:int=Field(100,ge=1,le=500)
    max_hour:int=Field(10,ge=1,le=50)
    max_day:int=Field(100,ge=1,le=500)
    followup_days:int=Field(3,ge=1,le=30)
    automation_timezone:str=Field('Asia/Kolkata',max_length=80)
    @field_validator('automation_timezone')
    @classmethod
    def timezone_valid(cls,value):
        try:ZoneInfo(value)
        except Exception:raise ValueError('Choose an IANA timezone')
        return value

@router.get('/targets')
def targets(conn=Depends(get_db,scope='function')):
    from app.automation.settings import TARGET_FIELDS
    s=effective_settings(conn)
    return {key:getattr(s,key) for key in TARGET_FIELDS}

@router.put('/targets')
def update_targets(body:Targets,request:Request,conn=Depends(get_db,scope='function')):
    s=mail_settings()
    if body.max_hour>s.max_hour:raise HTTPException(422,f'Hourly limit cannot exceed the server ceiling of {s.max_hour}.')
    if body.max_day>s.max_day:raise HTTPException(422,f'Daily limit cannot exceed the server ceiling of {s.max_day}.')
    if body.daily_email_target>body.max_day:raise HTTPException(422,'Daily email target must not exceed the daily sending limit.')
    save_targets(conn,body.model_dump(),request.state.user_email)
    return targets(conn)

@router.get('/markets/page')
def market_page(page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=100),conn=Depends(get_db,scope='function')):
    condition="WHERE LOWER(country) LIKE ? OR LOWER(city) LIKE ? OR LOWER(vertical) LIKE ?"
    args=['%'+search.lower()+'%']*3
    total=conn.execute('SELECT COUNT(*) FROM scan_markets '+condition,args).fetchone()[0]
    rows=conn.execute('SELECT * FROM scan_markets '+condition+' ORDER BY country,city,vertical,id LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':page_size}

class MarketEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    country:str=Field(min_length=1,max_length=100)
    city:str=Field(min_length=1,max_length=100)
    region:str=Field('',max_length=100)
    vertical:str=Field(min_length=1,max_length=80)
    enabled:bool=True
    priority:int=Field(0,ge=-100,le=100)
    cooldown_days:int=Field(7,ge=0,le=365)

@router.put('/markets/{market_id}')
def edit_market(market_id:str,body:MarketEdit,conn=Depends(get_db,scope='function')):
    from app.config.verticals import get_vertical_manager
    # Validate against the same configured discovery verticals, never invent a crawler key.
    if body.vertical not in get_vertical_manager().verticals:raise HTTPException(422,'Unknown discovery vertical')
    if not conn.execute('SELECT 1 FROM scan_markets WHERE id=?',(market_id,)).fetchone():raise HTTPException(404,'Market not found')
    if conn.execute('SELECT 1 FROM scan_markets WHERE country=? AND city=? AND vertical=? AND id<>?',(body.country.strip(),body.city.strip(),body.vertical,market_id)).fetchone():raise HTTPException(409,'Market combination already exists')
    conn.execute('UPDATE scan_markets SET country=?,city=?,region=?,vertical=?,enabled=?,priority=?,cooldown_days=?,updated_at=? WHERE id=?',(body.country.strip(),body.city.strip(),body.region.strip(),body.vertical,int(body.enabled),body.priority,body.cooldown_days,now(),market_id))
    return {'saved':True}

@router.get('/email-history')
def email_history(request:Request,page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100),conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    # Calculate recipient events separately so multiple opens/clicks never inflate sends.
    zone=ZoneInfo(effective_settings(conn).automation_timezone)
    from datetime import timedelta
    days={}
    for r in conn.execute("SELECT created_at,status FROM email_messages WHERE direction='OUTBOUND' AND created_at>=? AND organization_id=?",((datetime.now(timezone.utc)-timedelta(days=366)).isoformat(),organization)).fetchall():
        day=datetime.fromisoformat(r['created_at']).astimezone(zone).date().isoformat()
        bucket=days.setdefault(day,{'day':day,'sent':0,'failed':0,'pending':0,'bounced':0,'replied':0,'unsubscribed':0,'queued':0})
        bucket['sent' if r['status']=='SENT' else 'failed' if r['status']=='FAILED' else 'pending']+=1
    for r in conn.execute('SELECT q.queued_at FROM automation_email_queue q JOIN master_lead_state m ON m.prospect_id=q.prospect_id AND m.organization_id=?',(organization,)).fetchall():
        day=datetime.fromisoformat(r['queued_at']).astimezone(zone).date().isoformat();days.setdefault(day,{'day':day,'sent':0,'failed':0,'pending':0,'bounced':0,'replied':0,'unsubscribed':0,'queued':0})['queued']+=1
    seen=set()
    for r in conn.execute("SELECT e.message_id,e.event_type,e.occurred_at FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.event_type IN ('BOUNCED_HARD','BOUNCED_SOFT','REPLIED_VERIFIED','UNSUBSCRIBED') AND e.occurred_at>=? AND m.organization_id=?",((datetime.now(timezone.utc)-timedelta(days=366)).isoformat(),organization)).fetchall():
        day=datetime.fromisoformat(r['occurred_at']).astimezone(zone).date().isoformat();kind='bounced' if r['event_type'].startswith('BOUNCED') else 'replied' if r['event_type']=='REPLIED_VERIFIED' else 'unsubscribed'
        key=(day,kind,r['message_id'])
        if key in seen:continue
        seen.add(key);days.setdefault(day,{'day':day,'sent':0,'failed':0,'pending':0,'bounced':0,'replied':0,'unsubscribed':0,'queued':0})[kind]+=1
    rows=sorted(days.values(),key=lambda r:r['day'],reverse=True)
    return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows),'page':page,'page_size':page_size,'timezone':str(zone)}

class MasterBulk(BaseModel):
    model_config=ConfigDict(extra='forbid')
    prospect_ids:list[str]=Field(min_length=1,max_length=100)
    action:Literal['sales','assign','dnc','list','followup','export','manual']
    sales_state:str|None=None
    assigned_to:str|None=Field(None,max_length=254)
    list_id:str|None=Field(None,max_length=36)
    due_at:str|None=Field(None,max_length=60)

@router.post('/master-leads/bulk')
def master_bulk(body:MasterBulk,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    from app.database.prospects import ProspectRepository
    from app.sales.service import member,schedule,activity
    from app.api.routes.sales import assignment,utc_date
    from fastapi.responses import Response
    ids=list(dict.fromkeys(body.prospect_ids));assignment(body.assigned_to)
    for pid in ids:
        if not conn.execute('SELECT 1 FROM master_lead_state WHERE prospect_id=? AND organization_id=?',(pid,organization)).fetchone():raise HTTPException(404,'Master Lead not found')
    if body.action=='sales' and body.sales_state not in SALES_STATES:raise HTTPException(422,'Choose a sales state')
    if body.action=='list' and (not body.list_id or not conn.execute('SELECT 1 FROM lead_lists WHERE id=? AND organization_id=?',(body.list_id,organization)).fetchone()):raise HTTPException(422,'Choose an existing list')
    if body.action=='followup':
        if not body.due_at:raise HTTPException(422,'Choose a follow-up date')
        try:utc_date(body.due_at)
        except Exception:raise HTTPException(422,'Choose a date with an explicit timezone')
    if body.action=='export':
        import csv,io
        output=io.StringIO();writer=csv.writer(output);writer.writerow(['Company','City','Country','Website','Email','Phone','Contact state','Sales state'])
        for pid in ids:
            r=conn.execute('SELECT b.name,b.city,b.country,b.website,b.public_email,b.phone,m.contact_state,m.sales_state FROM master_lead_state m JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id) WHERE m.prospect_id=? AND m.organization_id=?',(pid,organization)).fetchone()
            writer.writerow(["'"+str(v) if str(v or '').startswith(('=','+','-','@')) else v for v in dict(r).values()])
        return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="master-leads.csv"','Cache-Control':'no-store'})
    for pid in ids:
        if body.action=='sales':
            previous=conn.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=? AND organization_id=?',(pid,organization)).fetchone()[0]
            state(pid,State(contact_state=previous,sales_state=body.sales_state),request,conn)
        elif body.action=='manual':
            conn.execute("UPDATE master_lead_state SET contact_state='MANUAL_CONTACT_REQUIRED',manual_reason='Owner requested manual contact',updated_at=? WHERE prospect_id=? AND organization_id=?",(now(),pid,organization))
            conn.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM master_lead_state WHERE organization_id=?)",(pid,organization))
        elif body.action=='dnc':
            previous=conn.execute('SELECT sales_state FROM master_lead_state WHERE prospect_id=? AND organization_id=?',(pid,organization)).fetchone()[0]
            state(pid,State(contact_state='DO_NOT_CONTACT',sales_state=previous),request,conn)
        elif body.action=='assign':ProspectRepository(conn).workflow(pid,request.state.user_email,assigned_to=body.assigned_to,organization=organization)
        elif body.action=='list':member(conn,pid,body.list_id,request.state.user_email)
        elif body.action=='followup':schedule(conn,pid,request.state.user_email,body.due_at,assigned_to=body.assigned_to)
    return {'updated':len(ids)}

@router.get('/identity-review')
def identity_review(request:Request,page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    where=" FROM businesses b JOIN prospects p ON p.id=b.prospect_id AND p.organization_id=? WHERE b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED'"
    total=conn.execute('SELECT COUNT(*)'+where,(organization,)).fetchone()[0]
    rows=conn.execute('SELECT b.id,b.name,b.domain,b.city,b.country,b.run_id,b.rejection_reason'+where+' ORDER BY b.id DESC LIMIT ? OFFSET ?',(organization,page_size,(page-1)*page_size)).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':page_size}
