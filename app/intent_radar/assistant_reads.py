"""Finite, authorized read routing. No model, tool execution or AI reservation.

Counts describe stored workspace records, not market size, buyers or personal
attribution. Publication-date windows are explicit; first-generation time is not
invented where the signal schema does not retain it.
"""
import json,re,uuid
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from app.growth_intelligence import analytics,models,service
from app.intent_radar import service as radar
from app.database.prospects import now


def route(prompt,previous=None):
    text=' '.join(prompt.casefold().split())
    # Question words alone do not request statistics. "What do these signals
    # imply?" must retain the research path rather than receive a count.
    count=bool(re.search(r'\b(how many|number of|count|total)\b',text))
    direct_question=bool(re.match(r'^(?:please )?(?:what|which|how much|show)\b',text))
    listing=bool(re.fullmatch(r'(?:please )?(?:list|show)(?: me)? (?:my |our |the |current |active |all |workspace |saved )*(?:signals?|conversations?|discussions?|monitors?|opportunities|searches|bookmarks)(?: (?:today|this month|available|last 7 days))?\??',text))
    usage=bool(direct_question and re.search(r'\b(quota|allowance|usage|remaining|left|plan|subscription)\b',text))
    sources=bool(direct_question and re.search(r'\b(source|sources|feeds|connectors)\b',text) and re.search(r'\b(available|enabled|configured|supported)\b',text))
    kind=None
    if count or listing or usage or sources:
        if re.search(r'\b(quota|allowance|usage|remaining|left|plan|subscription)\b',text):kind='usage'
        elif re.search(r'\b(source|sources|feeds|connectors)\b',text) and re.search(r'\b(available|enabled|configured|supported)\b',text):kind='sources'
        elif re.search(r'\b(saved|bookmarks|bookmarked)\b',text):kind='saved'
        elif re.search(r'\b(monitors?|monitoring)\b',text):kind='monitors'
        elif re.search(r'\b(opportunities|opportunity)\b',text):kind='opportunities'
        elif re.search(r'\b(searches|search|discoveries)\b',text):kind='searches'
        elif re.search(r'\b(signals?|conversations?|discussions?)\b',text):kind='signals'
    period='today' if re.search(r'\btoday\b',text) else 'week' if re.search(r'\b(last|past) (7|seven) days\b',text) else 'month' if 'this month' in text else 'all'
    if kind is None and previous and re.fullmatch(r'(?:and |what about |how about )?(?:today|this month|(?:the )?(?:last|past) (?:7|seven) days)\??',text):kind=previous.get('kind')
    return {'kind':kind,'period':period} if kind else None


def answer(c,ctx,intent):
    org=ctx.organization_id;stamp=datetime.now(timezone.utc);kind=intent['kind'];period=intent['period']
    start=stamp.replace(hour=0,minute=0,second=0,microsecond=0) if period=='today' else stamp-timedelta(days=7) if period=='week' else stamp.replace(day=1,hour=0,minute=0,second=0,microsecond=0) if period=='month' else None
    window={'today':'today (UTC)','week':'the last seven days','month':'this calendar month (UTC)','all':'all stored history'}[period]
    caveats=['Current workspace only. These figures describe stored records, not market size or verified buyers.']
    href='/intent-radar';facts={};text=''
    if kind=='signals':
        pref=c.execute('SELECT configuration_json FROM intent_preferences WHERE organization_id=?',(org,)).fetchone()
        days=json.loads(pref[0]).get('source_retention_days',30) if pref else 30
        retention,args=radar.retention_sql(c,days)
        where='organization_id=?';params=[org]
        if start:where+=' AND observed_at>=? AND observed_at<=?';params.extend([start.isoformat(),stamp.isoformat()])
        row=c.execute('SELECT COUNT(*) stored,COALESCE(SUM(CASE WHEN available=1 AND '+retention+' THEN 1 ELSE 0 END),0) current FROM intent_signals WHERE '+where,[*args,*params]).fetchone()
        facts={'stored_conversations':row['stored'],'currently_available':row['current'],'window':window,'date_basis':'original publication date' if start else 'all stored records'}
        text=f"Your workspace contains {row['stored']} collected conversation records for {window}; {row['current']} currently have available source evidence within retention."
        href='/intent-radar/signals'
        if start:caveats.append('This window uses original publication dates. A per-user first-generated timestamp is not recorded; it is not inferred from the last refresh.')
    elif kind=='monitors':
        rows=c.execute('SELECT status,COUNT(*) n FROM intent_monitors WHERE organization_id=? GROUP BY status',(org,)).fetchall();facts={r['status']:r['n'] for r in rows}
        text=f"Your workspace has {facts.get('Active',0)} active, {facts.get('Paused',0)} paused, {facts.get('Draft',0)} draft and {facts.get('Archived',0)} archived monitors."
        href='/intent-radar/monitors';caveats.append('Monitor states are current, not a historical count of past activations.')
    elif kind in ('saved','opportunities','searches'):
        table,column,label,href={'saved':('intent_saved_signals','saved_at','saved signal bookmarks','/intent-radar/saved'),'opportunities':('intent_opportunities','created_at','opportunity records','/intent-radar/opportunities'),'searches':('intent_discoveries','created_at','requested searches','/intent-radar/discover')}[kind]
        where='organization_id=?';args=[org]
        if start:where+=' AND '+column+'>=? AND '+column+'<=?';args.extend([start.isoformat(),stamp.isoformat()])
        n=c.execute('SELECT COUNT(*) FROM '+table+' WHERE '+where,args).fetchone()[0];facts={'count':n,'window':window}
        text=f'Your workspace has {n} {label} for {window}.'
        if kind=='opportunities':caveats.append('Stored opportunity records are not a verified count of qualified buyers.')
        if kind=='searches':caveats.append('Requested searches include scheduled checks and unsuccessful requests; they are not successful-result counts.')
        if kind=='saved':caveats.append('Bookmarks remain saved when source excerpts expire or are withdrawn.')
    elif kind=='sources':
        from app.intent_radar.connectors import catalog
        facts={'sources':[{'name':s['name'],'status':s['state'],'reason':s.get('permission',s.get('coverage',''))} for s in catalog(c)]}
        text='Current source configuration: '+'; '.join(s['name']+': '+s['status'] for s in facts['sources'])+'.'
        href='/intent-radar/integrations';caveats.append('Configured availability does not prove a recent successful fetch or publisher permission for another endpoint.')
    elif kind=='usage':
        from app.billing.overview import overview
        data=overview(c);facts={'access':data['access']['kind'],'allowances':data['usage']}
        lines=[data['access']['kind']+' access.']
        lines.extend(f"{r['label']}: {r['used']} of {r['limit']}, {r['remaining']} remaining" for r in data['usage'][:4])
        text=' '.join(lines)+'.';href='/billing'
        caveats.append('Daily operator safety limits and verified monthly paid allowances are separate. Reserved tokens are not provider-billed tokens.')
    else:raise ValueError('Unsupported deterministic workspace read.')
    label='Workspace '+kind+' snapshot';reference={'id':'workspace:read','label':label,'url':href,'text':text,'observed_at':stamp.isoformat()}
    return {'blocks':[{'kind':'Evidence','text':text,'citations':[{'reference':reference['id'],'quote':text[:400]}]}],'references':[reference],
      'followups':['How many signals are available?','How many active monitors do I have?','What is my remaining usage?'],
      'limitations':caveats+['Snapshot at '+stamp.isoformat()+'. No AI operation or token capacity was consumed.']},facts


def start(c,body):
    from app.intent_radar import assistant
    # A read answer may persist only its creator's private conversation. It does
    # not change shared workspace resources, entitlement or provider capacity.
    ctx=analytics.access(c);intent=route(body.prompt)
    if not intent and body.thread_id:
        root=assistant.owned_thread(c,str(body.thread_id))
        previous=c.execute('SELECT snapshot_json FROM growth_research WHERE organization_id=? AND created_by=? AND '+assistant.thread_expression(c)+"=? AND status='COMPLETE' ORDER BY created_at DESC,id DESC LIMIT 1",(ctx.organization_id,ctx.actor,root['id'])).fetchone()
        intent=route(body.prompt,json.loads(previous[0]).get('workspace_read') if previous else None)
    if not intent:return None
    key=str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id+':growth:'+str(body.request_id)))
    request=assistant.normalize_request(c,models.Start(kind='RESEARCH',title='Assistant · '+body.prompt[:90],question=body.prompt,request_id=body.request_id,assistant=models.AssistantContext(thread_id=body.thread_id,page=body.page,signal_ids=body.signal_ids)),key)
    encoded=json.dumps(request.model_dump(mode='json'),sort_keys=True)
    from app.workflows.service import lock
    lock(c);analytics.access(c)
    old=c.execute('SELECT created_by,scope_json FROM growth_research WHERE organization_id=? AND id=?',(ctx.organization_id,key)).fetchone()
    if old:
        if old['created_by']!=ctx.actor:raise HTTPException(404,'Assistant conversation not found.')
        if old['scope_json']!=encoded:raise HTTPException(409,'Request ID belongs to a different question.')
        return service.detail(c,key)
    output,facts=answer(c,ctx,intent);stamp=now()
    snapshot={'evidence':[],'workspace_read':intent,'facts':facts,'observed_at':stamp}
    value={'assistant':output,'mode':'Workspace data — no AI used','themes':[],'findings':[],'limitations':output['limitations'],'executive_summary':'Authorized deterministic workspace snapshot.'}
    c.execute("INSERT INTO growth_research(id,organization_id,created_by,kind,question,title,scope_json,snapshot_json,output_json,input_hash,request_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,'COMPLETE',?,?)",(key,ctx.organization_id,ctx.actor,'RESEARCH',request.question,request.title,encoded,json.dumps(snapshot),json.dumps(value),service.fingerprint(encoded),str(body.request_id),stamp,stamp))
    return service.detail(c,key)
