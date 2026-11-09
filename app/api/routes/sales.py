import json,uuid
from datetime import datetime,timezone
from typing import Literal,Annotated
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from fastapi import APIRouter,Depends,HTTPException,Request,Query
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.api.dependencies import get_db
from app.api.routes.workflow import require_prospect,Status
from app.database.prospects import ProspectRepository,now
from app.config.settings import get_settings
from app.sales.service import activity,dossier,schedule,member,suppressed

router=APIRouter(prefix='/sales',tags=['Sales workspace'])
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
def utc_date(value):
    if value is None:return value
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    if date.tzinfo is None:raise ValueError('An explicit timezone is required')
    return date.astimezone(timezone.utc).isoformat()
class Followup(Strict):
    due_at:str=Field(max_length=60)
    note:str=Field(default='',max_length=2000)
    assigned_to:str|None=Field(default=None,max_length=254)
    _date=field_validator('due_at')(utc_date)
class FollowupUpdate(Strict):
    due_at:str|None=Field(default=None,max_length=60)
    status:Literal['COMPLETED','CANCELED']|None=None
    _date=field_validator('due_at')(utc_date)
from app.sales.collections import Named
class Filters(Strict):
    search:str=Field(default='',max_length=200)
    country:str=Field(default='',max_length=100)
    city:str=Field(default='',max_length=100)
    vertical:str=Field(default='',max_length=100)
    opportunity:Literal['','WEBSITE','SEO','SECURITY']=''
    primary:Literal['','WEBSITE','SEO','SECURITY']=''
    contactability:Literal['','HIGH','MEDIUM','LOW']=''
    commercial_fit:Literal['','HIGH','MEDIUM','LOW','UNKNOWN']=''
    business_scale:str=Field(default='',max_length=120)
    status:str=Field(default='',max_length=30)
    assigned_to:str=Field(default='',max_length=254)
    min_website:int=Field(default=0,ge=0,le=100)
    min_seo:int=Field(default=0,ge=0,le=100)
    min_security:int=Field(default=0,ge=0,le=100)
    campaign:str=Field(default='',max_length=36)
    results:Literal['all','new','previous']='all'
    sort_by:Literal['website','seo','security','newest','name','commercial_fit']='website'
    sort_dir:Literal['asc','desc']='desc'
    list_id:str=Field(default='',max_length=36)
    run_id:int|None=Field(default=None,ge=1)
    @field_validator('business_scale')
    @classmethod
    def scales(cls,value):
        if value and any(v not in ('LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL','ENTERPRISE','KNOWN_CHAIN') for v in value.split(',')):raise ValueError('Invalid business size')
        return value
    @field_validator('status')
    @classmethod
    def statuses(cls,value):
        from app.database.phase4_schema import STATUSES
        if value and value not in STATUSES:raise ValueError('Invalid status')
        return value
class View(Strict):
    name:str=Field(min_length=1,max_length=100)
    filters:Filters
class Deal(Strict):
    service_interest:Literal['WEBSITE','SEO','AEO_GEO','SECURITY','COMBINED','OTHER']|None=None
    estimated_value:float|None=Field(default=None,ge=0,le=1e9,allow_inf_nan=False)
    proposal_value:float|None=Field(default=None,ge=0,le=1e9,allow_inf_nan=False)
    currency:str=Field(default='GBP',pattern='^[A-Z]{3}$')
    meeting_at:str|None=Field(default=None,max_length=60)
    proposal_at:str|None=Field(default=None,max_length=60)
    close_at:str|None=Field(default=None,max_length=60)
    loss_reason:str|None=Field(default=None,max_length=1000)
    @field_validator('meeting_at','proposal_at','close_at')
    @classmethod
    def dates(cls,value):
        if value:
            date=datetime.fromisoformat(value.replace('Z','+00:00'))
            if date.tzinfo is None:raise ValueError('Timezone required')
            return date.astimezone(timezone.utc).isoformat()
        return value
class Bulk(Strict):
    lead_ids:list[int]=Field(min_length=1,max_length=100)
    action:Literal['status','assign','list','followup','pdf']
    status:Status|None=None
    assigned_to:str|None=None
    list_id:str|None=None
    due_at:str|None=None

def assignment(value):
    if value and value not in get_settings().allowed_emails:raise HTTPException(422,'Choose an approved team member.')

@router.get('/leads/{lead_id}')
def lead_sales(lead_id:int,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);return dossier(conn,pid,organization=organization)

@router.patch('/leads/{lead_id}')
def update_deal(lead_id:int,body:Deal,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);from app.sales.service import ensure;ensure(conn,pid,organization)
    values=body.model_dump(exclude_unset=True)
    if values:conn.execute('UPDATE prospect_sales SET '+','.join(k+'=?' for k in values)+' WHERE prospect_id=? AND organization_id=?',[*values.values(),pid,organization])
    if values.get('meeting_at'):activity(conn,pid,request.state.user_email,'MEETING_SCHEDULED',{'meeting_at':values['meeting_at']},organization=organization)
    if values.get('proposal_at') or values.get('proposal_value') is not None:activity(conn,pid,request.state.user_email,'PROPOSAL_SET',values,organization=organization)
    return dossier(conn,pid,organization=organization)

@router.post('/leads/{lead_id}/followups',status_code=201)
def add_followup(lead_id:int,body:Followup,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);assignment(body.assigned_to)
    return {'id':schedule(conn,pid,request.state.user_email,body.due_at,body.note,body.assigned_to,organization=organization)}

@router.patch('/leads/{lead_id}/followups/{followup_id}')
def change_followup(lead_id:int,followup_id:str,body:FollowupUpdate,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization)
    if not conn.execute('SELECT 1 FROM followups WHERE id=? AND prospect_id=? AND organization_id=?',(followup_id,pid,organization)).fetchone():raise HTTPException(404,'Follow-up not found.')
    if body.due_at:
        if suppressed(conn,pid,organization):raise HTTPException(409,'This prospect is marked Do Not Contact.')
        value=datetime.fromisoformat(body.due_at.replace('Z','+00:00'))
        if value.tzinfo is None:raise HTTPException(422,'Timezone required.')
        conn.execute("UPDATE followups SET due_at=?,status='OPEN',completed_at=NULL WHERE id=? AND organization_id=?",(value.astimezone(timezone.utc).isoformat(),followup_id,organization));activity(conn,pid,request.state.user_email,'FOLLOW_UP_CREATED',{'rescheduled':followup_id,'due_at':body.due_at},organization=organization)
    if body.status:
        conn.execute('UPDATE followups SET status=?,completed_at=? WHERE id=? AND organization_id=?',(body.status,now(),followup_id,organization));activity(conn,pid,request.state.user_email,'FOLLOW_UP_COMPLETED',{'id':followup_id,'status':body.status},organization=organization)
    return dossier(conn,pid,organization=organization)

@router.post('/leads/{lead_id}/unsuppress')
def unsuppress(lead_id:int,request:Request,confirmation:str=Query(...,pattern='^ALLOW CONTACT$'),conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);conn.execute('UPDATE prospect_sales SET suppressed_at=NULL,suppression_source=NULL WHERE prospect_id=? AND organization_id=?',(pid,organization));ProspectRepository(conn).workflow(pid,request.state.user_email,lead_status='NEW',organization=organization);activity(conn,pid,request.state.user_email,'SUPPRESSION_CLEARED',organization=organization);return dossier(conn,pid,organization=organization)

@router.get('/lists')
def lists(request:Request,page:int|None=Query(None,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=200),archived:bool=False,conn=Depends(get_db,scope='function')):
    from app.sales.collections import listing
    result=listing(conn,search,page or 1,page_size if page else 100,archived)
    return result if page else result['items']
@router.post('/lists',status_code=201)
def add_list(body:Named,request:Request,conn=Depends(get_db,scope='function')):
    from app.sales.collections import save
    return save(conn,body)
@router.delete('/lists/{list_id}')
def remove_list(list_id:str,request:Request,conn=Depends(get_db,scope='function')):
    from app.sales.collections import get,archive
    archive(conn,list_id,get(conn,list_id)['revision']);return {'archived':True,'history_retained':True}
@router.get('/lists/{list_id}')
def list_detail(list_id:str,page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),conn=Depends(get_db,scope='function')):
    from app.sales.collections import detail
    return detail(conn,list_id,page,page_size)
@router.put('/lists/{list_id}')
def edit_list(list_id:str,body:Named,conn=Depends(get_db,scope='function')):
    from app.sales.collections import save
    return save(conn,body,list_id)
class ListRevision(Strict):revision:int=Field(ge=1)
@router.post('/lists/{list_id}/archive')
def archive_list(list_id:str,body:ListRevision,conn=Depends(get_db,scope='function')):
    from app.sales.collections import archive
    return archive(conn,list_id,body.revision)
class ListCompanies(Strict):
    business_ids:list[Annotated[int,Field(ge=1,le=9223372036854775807)]]=Field(min_length=1,max_length=100)
@router.post('/lists/{list_id}/companies')
def add_companies(list_id:str,body:ListCompanies,conn=Depends(get_db,scope='function')):
    from app.sales.collections import change_members
    return change_members(conn,list_id,body.business_ids)
@router.delete('/lists/{list_id}/companies/{business_id}')
def remove_company(list_id:str,business_id:int,conn=Depends(get_db,scope='function')):
    from app.sales.collections import change_members
    return change_members(conn,list_id,[business_id],True)
@router.get('/lists/{list_id}/export.csv')
def export_list(list_id:str,conn=Depends(get_db,scope='function')):
    from app.sales.collections import detail
    from fastapi.responses import Response
    import csv,io
    data=detail(conn,list_id,1,100)
    if data['company_count']+data['contact_count']>5000:raise HTTPException(413,'This export exceeds the 5,000-record download budget. Export a smaller list.')
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['type','name','title','website','country','city','status'])
    safe=lambda value: "'"+str(value) if str(value).lstrip().startswith(('=','+','-','@','\t','\r')) else str(value)
    rows=detail(conn,list_id,1,5000)
    if rows['company_count']+rows['contact_count']>5000:raise HTTPException(413,'This export exceeds the 5,000-record download budget. Export a smaller list.')
    if len(rows['companies'])!=rows['company_count'] or len(rows['contacts'])!=rows['contact_count']:
        raise HTTPException(409,'Some selected records are unavailable. Review the list before exporting.')
    for item in rows['companies']:writer.writerow([safe(value or '') for value in ['company',item['name'],'',item['website'],item['country'],item['city'],item['lead_status']]])
    for item in rows['contacts']:writer.writerow([safe(value or '') for value in ['contact',item['name'],item['role'],'','','',item['verification_state']]])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="company-contact-list.csv"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
@router.post('/leads/{lead_id}/lists/{list_id}')
def add_member(lead_id:int,list_id:str,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);member(conn,pid,list_id,request.state.user_email,organization=organization);return {'saved':True}
@router.delete('/leads/{lead_id}/lists/{list_id}')
def remove_member(lead_id:int,list_id:str,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization);member(conn,pid,list_id,request.state.user_email,True,organization=organization);return {'saved':True}
@router.get('/views')
def views(request:Request,conn=Depends(get_db,scope='function')):return [{**dict(r),'filters':json.loads(r['filters_json'])} for r in conn.execute('SELECT * FROM saved_views WHERE organization_id=? ORDER BY name',(request.state.organization_id,)).fetchall()]
@router.post('/views',status_code=201)
def add_view(body:View,request:Request,conn=Depends(get_db,scope='function')):
    key=str(uuid.uuid4());conn.execute('INSERT INTO saved_views(id,name,filters_json,created_by,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?,?)',(key,body.name.strip(),json.dumps(body.filters.model_dump()),request.state.user_email,now(),now(),request.state.organization_id));return {'id':key}
@router.delete('/views/{view_id}')
def remove_view(view_id:str,request:Request,conn=Depends(get_db,scope='function')):conn.execute('DELETE FROM saved_views WHERE id=? AND organization_id=?',(view_id,request.state.organization_id));return {'deleted':True}

@router.post('/bulk')
def bulk(body:Bulk,request:Request,conn=Depends(get_db,scope='function')):
    actor=request.state.user_email;organization=request.state.organization_id;assignment(body.assigned_to);seen=set();results=[]
    for bid in dict.fromkeys(body.lead_ids):
        pid=require_prospect(conn,bid,actor,organization=organization)
        if pid in seen:continue
        seen.add(pid)
        if body.action=='status':
            if not body.status:raise HTTPException(422,'Choose a status.')
            ProspectRepository(conn).workflow(pid,actor,lead_status=body.status,organization=organization)
        elif body.action=='assign':ProspectRepository(conn).workflow(pid,actor,assigned_to=body.assigned_to,organization=organization)
        elif body.action=='list':member(conn,pid,body.list_id,actor,organization=organization)
        elif body.action=='followup':
            if not body.due_at:raise HTTPException(422,'Choose a follow-up date.')
            schedule(conn,pid,actor,body.due_at,assigned_to=body.assigned_to,organization=organization)
        else:
            from app.reports.service import create_report
            results.append(create_report(conn,bid,pid,actor,organization=organization))
    conn.commit()
    if body.action=='pdf':
        from app.reports.service import launch_reports
        launch_reports()
    return {'updated':len(seen),'reports':results}

@router.get('/outreach')
def outreach(request:Request,queue:Literal['ready','today','overdue','waiting','replied','meeting','proposal','won','lost','not_interested','do_not_contact']='ready',tz:str=Query('Asia/Kolkata',max_length=80),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    try:zone=ZoneInfo(tz)
    except ZoneInfoNotFoundError:raise HTTPException(422,'Choose a valid timezone.')
    from datetime import timedelta
    local=datetime.now(zone);start=local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat();end=(local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc).isoformat()
    base="""WITH latest AS (SELECT MAX(id) AS id FROM businesses GROUP BY prospect_id)
     SELECT b.id,b.name,b.website,b.city,b.country,b.vertical,b.phone,b.public_email,b.prospect_id,p.lead_status,p.assigned_to,
     o.website_opportunity_score,o.seo_opportunity_score,o.security_opportunity_score,o.primary_opportunity,i.commercial_fit,
     s.last_contact_at,s.unread_replies,(SELECT MIN(due_at) FROM followups f WHERE f.prospect_id=p.id AND f.status='OPEN') AS next_followup,
     (SELECT id FROM client_reports r WHERE r.prospect_id=p.id AND r.status='READY' ORDER BY version DESC LIMIT 1) AS ready_report_id
     FROM businesses b JOIN latest l ON l.id=b.id JOIN prospects p ON p.id=b.prospect_id
     LEFT JOIN opportunity_scores o ON o.business_id=b.id LEFT JOIN business_intelligence i ON i.business_id=b.id LEFT JOIN prospect_sales s ON s.prospect_id=p.id AND s.organization_id=? """
    safe="p.lead_status<>'DO_NOT_CONTACT' AND s.suppressed_at IS NULL"
    due="EXISTS(SELECT 1 FROM followups f WHERE f.prospect_id=p.id AND f.status='OPEN' AND "
    rules={'ready':("p.lead_status='READY_TO_CONTACT'",[]),'today':(due+'f.due_at>=? AND f.due_at<?)',[start,end]),'overdue':(due+'f.due_at<?)',[now()]),'waiting':("p.lead_status IN ('CONTACTED','FOLLOW_UP')",[]),'replied':("p.lead_status='REPLIED'",[]),'meeting':("p.lead_status='MEETING'",[]),'proposal':("p.lead_status='PROPOSAL'",[]),'won':("p.lead_status='WON'",[]),'lost':("p.lead_status='LOST'",[]),'not_interested':("p.lead_status='NOT_INTERESTED'",[]),'do_not_contact':("(p.lead_status='DO_NOT_CONTACT' OR s.suppressed_at IS NOT NULL)",[])}
    def query_for(key):
        clause,args=rules[key];head=('('+clause+')' if key=='do_not_contact' else safe+' AND ('+clause+')');return base+' WHERE p.organization_id=? AND '+head,[organization,organization]+args
    counts={}
    for key in rules:
        sql,args=query_for(key);counts[key]=conn.execute('SELECT COUNT(*) FROM ('+sql+') q',args).fetchone()[0]
    sql,args=query_for(queue);items=[dict(r) for r in conn.execute(sql+' ORDER BY COALESCE(s.unread_replies,0) DESC,b.id DESC LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size]).fetchall()]
    from app.mail import tracking
    if tracking.available(conn):
        for item in items:item['engagement']=tracking.lead_summary(conn,item['prospect_id'])
    return {'items':items,'counts':counts,'total':counts[queue],'page':page,'page_size':page_size,'total_pages':max(1,(counts[queue]+page_size-1)//page_size)}
