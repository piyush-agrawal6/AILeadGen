"""Owned domain reads/mutations. Every public operation rechecks the platform grant."""
import hashlib, json, uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.workflows.service import lock
from app.intent_radar.permissions import context, availability
from app.intent_radar import models

TABLES = {'monitors': 'intent_monitors', 'signals': 'intent_signals', 'opportunities': 'intent_opportunities', 'alerts': 'intent_alerts', 'discoveries': 'intent_discoveries'}

def rank_expression(alias='intent_signals'):
    if alias not in ('intent_signals','s'):raise ValueError('Internal rank alias required.')
    base=f"COALESCE((SELECT r.score FROM intent_rankings r WHERE r.organization_id={alias}.organization_id AND r.signal_id={alias}.id AND (r.icp_id IS NULL OR EXISTS(SELECT 1 FROM ideal_customer_profiles i WHERE i.organization_id=r.organization_id AND i.id=r.icp_id AND i.revision=r.icp_revision)) AND NOT EXISTS(SELECT 1 FROM organization_profiles p WHERE p.organization_id=r.organization_id AND p.updated_at>r.updated_at)),{alias}.score)"
    delta=f"COALESCE((SELECT CASE WHEN SUM(CASE WHEN f.label='Relevant' THEN 5 WHEN f.label IN ('Not relevant','Not a target customer','Too old','Duplicate','Incorrect AI summary') THEN -10 ELSE 0 END)>10 THEN 10 WHEN SUM(CASE WHEN f.label='Relevant' THEN 5 WHEN f.label IN ('Not relevant','Not a target customer','Too old','Duplicate','Incorrect AI summary') THEN -10 ELSE 0 END)<-20 THEN -20 ELSE SUM(CASE WHEN f.label='Relevant' THEN 5 WHEN f.label IN ('Not relevant','Not a target customer','Too old','Duplicate','Incorrect AI summary') THEN -10 ELSE 0 END) END FROM intent_feedback f WHERE f.organization_id={alias}.organization_id AND f.signal_id={alias}.id AND f.active=1),0)"
    value=f'({base}+{delta})'
    return f'CASE WHEN {value}>100 THEN 100 WHEN {value}<0 THEN 0 ELSE {value} END'

def ranked_signals(c,items):
    if not items:return items
    org=context(c).organization_id
    if len(items)>100 or any(item['organization_id']!=org for item in items):raise HTTPException(404,'Signal batch is outside this workspace.')
    marks=','.join('?' for _ in items)
    rows=c.execute("SELECT s.id,"+rank_expression('s')+" adjusted_score,(SELECT r.explanation_json FROM intent_rankings r WHERE r.organization_id=s.organization_id AND r.signal_id=s.id AND (r.icp_id IS NULL OR EXISTS(SELECT 1 FROM ideal_customer_profiles i WHERE i.organization_id=r.organization_id AND i.id=r.icp_id AND i.revision=r.icp_revision)) AND NOT EXISTS(SELECT 1 FROM organization_profiles p WHERE p.organization_id=r.organization_id AND p.updated_at>r.updated_at)) explanation FROM intent_signals s WHERE s.organization_id=? AND s.id IN ("+marks+")",[org,*[item['id'] for item in items]]).fetchall()
    ranks={r['id']:r for r in rows}
    for item in items:
        item['keyword_score']=item['score'];row=ranks.get(item['id'])
        if not row:raise HTTPException(404,'Signal not found in this workspace.')
        if not item['available']:item['score']=0;item['ranking']={'basis':'Public source evidence is unavailable; no current relevance claim.'};continue
        item['score']=row['adjusted_score'];item['ranking']=json.loads(row['explanation']) if row['explanation'] else {'version':'DETERMINISTIC_V3','basis':'Keyword evidence + bounded active workspace feedback'}
    return items

def ranked_signal(c,item):
    return ranked_signals(c,[item])[0]

def audit(c, action, key):
    ctx = context(c)
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)', (str(uuid.uuid4()), ctx.actor, 'INTENT_RADAR_' + action, key, 'SUCCESS', ctx.organization_id, now()))

def decode(row):
    item = dict(row)
    for field in ('configuration', 'evidence', 'tags', 'schedule'):
        if field + '_json' in item: item[field] = json.loads(item.pop(field + '_json'))
    item.pop('fingerprint', None)
    return item

def get(c, kind, key):
    org = context(c).organization_id
    table = TABLES[kind]
    row = c.execute(f'SELECT * FROM {table} WHERE organization_id=? AND id=?', (org, key)).fetchone()
    if not row: raise HTTPException(404, 'Intent Radar record not found.')
    item = decode(row)
    if kind == 'signals':
        if expired(item,preferences(c)['source_retention_days']):
            item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
        item['monitors'] = [dict(r) for r in c.execute('SELECT m.id,m.name FROM intent_monitors m JOIN intent_monitor_signals x ON x.monitor_id=m.id AND x.organization_id=m.organization_id WHERE x.organization_id=? AND x.signal_id=?', (org, key)).fetchall()]
        item['saved'] = bool(c.execute('SELECT 1 FROM intent_saved_signals WHERE organization_id=? AND signal_id=?', (org, key)).fetchone())
        ranked_signal(c,item)
    if kind=='opportunities':
        signal=get(c,'signals',item['signal_id']);item['score']=signal['score'];item['ranking']=signal['ranking']
    return item

def expired(signal,retention_days=30):
    policy=signal.get('evidence',{}).get('provenance',{})
    days=policy.get('retention_days')
    days=min(days,retention_days) if type(days) is int and days>0 else retention_days
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(signal['retrieved_at'])).total_seconds()>days*86400
    except (ValueError,KeyError,TypeError):return True

def retention_sql(c,days,alias='intent_signals'):
    policy=("CAST("+alias+".evidence_json AS JSONB)->'provenance'->>'retention_days'" if getattr(c,'backend','sqlite')=='postgres' else "json_extract("+alias+".evidence_json,'$.provenance.retention_days')")
    policy='CAST(('+policy+') AS INTEGER)'
    effective='CASE WHEN '+policy+' BETWEEN 1 AND ? THEN '+policy+' ELSE ? END'
    if getattr(c,'backend','sqlite')=='postgres':
        predicate='(CAST('+alias+'.retrieved_at AS TIMESTAMPTZ) + ('+effective+") * INTERVAL '1 day') > CAST(? AS TIMESTAMPTZ)"
    else:predicate='julianday('+alias+'.retrieved_at) + ('+effective+') > julianday(?)'
    return predicate,[days,days,now()]

def expire_content(c):
    from app.intent_radar.permissions import persistence_context
    org=persistence_context(c,manager=True).organization_id;count=0
    retention_days=preferences(c)['source_retention_days']
    cursor=c.execute('SELECT signal_after,cache_after FROM intent_retention_cursors WHERE organization_id=?',(org,)).fetchone()
    after=cursor['signal_after'] if cursor else '';cache_after=cursor['cache_after'] if cursor else ''
    rows=c.execute('SELECT * FROM intent_signals WHERE organization_id=? AND available=1 AND id>? ORDER BY id LIMIT 1000',(org,after)).fetchall()
    for row in rows:
        signal=decode(row)
        if not expired(signal,retention_days):continue
        changed=c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json='{}',revision=revision+1 WHERE id=? AND organization_id=? AND retrieved_at=?",(signal['id'],org,signal['retrieved_at'])).rowcount
        if changed:
            c.execute('DELETE FROM intent_analyses WHERE organization_id=? AND signal_id=?',(org,signal['id']));count+=1
            c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id=?',(org,signal['id']))
            c.execute("UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND signal_id=?",(org,signal['id']))
    caches=c.execute('SELECT fingerprint,result_json FROM intent_source_cache WHERE organization_id=? AND fingerprint>? ORDER BY fingerprint LIMIT 1000',(org,cache_after)).fetchall()
    for row in caches:
        data=json.loads(row['result_json']);items=data if isinstance(data,list) else data.get('items',[])
        remaining=[x for x in items if not expired({'retrieved_at':x.get('retrieved_at'),'evidence':{'provenance':x.get('provenance',{})}},retention_days)]
        if len(remaining)!=len(items):
            if isinstance(data,list):data=remaining
            else:data['items']=remaining;data.pop('etag',None);data.pop('last_modified',None)
            c.execute('UPDATE intent_source_cache SET result_json=? WHERE organization_id=? AND fingerprint=?',(json.dumps(data),org,row['fingerprint']))
    c.execute('INSERT INTO intent_retention_cursors(organization_id,signal_after,cache_after,updated_at) VALUES(?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET signal_after=excluded.signal_after,cache_after=excluded.cache_after,updated_at=excluded.updated_at',(org,rows[-1]['id'] if len(rows)==1000 else '',caches[-1]['fingerprint'] if len(caches)==1000 else '',now()))
    return {'expired_source_items':count,'customer_notes_preserved':True,'scanned':len(rows),'more_signal_batches':len(rows)==1000}

def _listing(c, kind, *, page=1, size=25, search='', status='', category='', source='', min_score=0, monitor_id='', saved='', from_date='', to_date='', sort='newest'):
    org = context(c).organization_id
    if not 1<=page<=10000 or not 1<=size<=100:raise HTTPException(422,'Bounded pagination required.')
    where, args = 'organization_id=?', [org]
    if search:
        field = 'name' if kind == 'monitors' else 'title' if kind in ('signals','alerts') else 'notes'
        where += f' AND LOWER({field}) LIKE ?'; args.append('%' + search.casefold() + '%')
    if kind=='monitors' and status=='Current':where+=" AND status<>'Archived'"
    elif status and kind != 'alerts': where += ' AND status=?'; args.append(status)
    if kind == 'signals':
        where += ' AND available=1 AND score>=?'; args.append(min_score)
        for field, value in (('category',category),('source',source)):
            if value: where += f' AND {field}=?'; args.append(value)
        if monitor_id:
            get(c, 'monitors', monitor_id)
            where += ' AND id IN (SELECT signal_id FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?)'; args.extend([org,monitor_id])
        if saved: where += (' AND ' if saved == 'saved' else ' AND NOT ') + 'EXISTS(SELECT 1 FROM intent_saved_signals s WHERE s.organization_id=intent_signals.organization_id AND s.signal_id=intent_signals.id)'
        if from_date: where += ' AND observed_at>=?'; args.append(from_date)
        if to_date: where += ' AND observed_at<?'; args.append(to_date + 'T23:59:59.999999+00:00')
        feedback_weight="CASE WHEN f.label='Relevant' THEN 5 WHEN f.label IN ('Not relevant','Not a target customer','Too old','Duplicate','Incorrect AI summary') THEN -10 ELSE 0 END"
        adjusted=f"(score + COALESCE((SELECT CASE WHEN SUM({feedback_weight})>10 THEN 10 WHEN SUM({feedback_weight})<-20 THEN -20 ELSE SUM({feedback_weight}) END FROM intent_feedback f WHERE f.organization_id=intent_signals.organization_id AND f.signal_id=intent_signals.id AND f.active=1),0)) DESC,id"
        order = {'score':adjusted, 'title':'title,id', 'newest':'observed_at DESC,id'}[sort]
    elif kind=='opportunities':order="CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, (SELECT s.score FROM intent_signals s WHERE s.id=intent_opportunities.signal_id AND s.organization_id=intent_opportunities.organization_id) DESC,created_at DESC,id"
    else: order = 'created_at DESC,id'
    total = c.execute(f'SELECT COUNT(*) FROM {TABLES[kind]} WHERE {where}', args).fetchone()[0]
    rows = c.execute(f'SELECT id FROM {TABLES[kind]} WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?', [*args,size,(page-1)*size]).fetchall()
    return {'items': [get(c,kind,r[0]) for r in rows], 'total': total, 'page':page, 'page_size':size}

def listing(c,kind,**filters):
    if kind not in ('signals','opportunities','alerts'):return _listing(c,kind,**filters)
    org=context(c).organization_id;page=filters.get('page',1);size=filters.get('size',25)
    if not 1<=page<=10000 or not 1<=size<=100:raise HTTPException(422,'Bounded pagination required.')
    where=['organization_id=?'];args=[org];sort=filters.get('sort','newest')
    if filters.get('search'):
        field='title' if kind in ('signals','alerts') else 'notes'
        where.append('LOWER('+field+') LIKE ?');args.append('%'+filters['search'].casefold()+'%')
    if filters.get('status') and kind!='alerts':where.append('status=?');args.append(filters['status'])
    if kind=='signals':
        where+=['available=1',rank_expression()+'>=?'];args.append(filters.get('min_score',0))
        retention,retention_args=retention_sql(c,preferences(c)['source_retention_days']);where.append(retention);args.extend(retention_args)
        for field in ('category','source'):
            if filters.get(field):where.append(field+'=?');args.append(filters[field])
        if filters.get('monitor_id'):
            get(c,'monitors',filters['monitor_id']);where.append('id IN (SELECT signal_id FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?)');args.extend([org,filters['monitor_id']])
        if filters.get('saved'):
            where.append(('NOT ' if filters['saved']=='unsaved' else '')+'EXISTS(SELECT 1 FROM intent_saved_signals s WHERE s.organization_id=intent_signals.organization_id AND s.signal_id=intent_signals.id)')
        for field,operator,end in [('from_date','>=',''),('to_date','<','T23:59:59.999999+00:00')]:
            if filters.get(field):where.append('observed_at'+operator+'?');args.append(filters[field]+end)
        order={'score':rank_expression()+' DESC,id','title':'title,id','newest':'observed_at DESC,id'}[sort]
    elif kind=='opportunities':
        order="CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,(SELECT "+rank_expression('s')+" FROM intent_signals s WHERE s.id=intent_opportunities.signal_id AND s.organization_id=intent_opportunities.organization_id) DESC,created_at DESC,id"
    else:
        if filters.get('read_state')=='Unread':where.append('read_at IS NULL')
        if filters.get('read_state')=='Read':where.append('read_at IS NOT NULL')
        if filters.get('alert_kind')=='Source issues':where.append('event_key LIKE ?');args.append('source-failure:%')
        if filters.get('alert_kind')=='Monitor activity':where.append('event_key NOT LIKE ?');args.append('source-failure:%')
        order='created_at DESC,id'
    sql=' AND '.join(where);total=c.execute('SELECT COUNT(*) FROM '+TABLES[kind]+' WHERE '+sql,args).fetchone()[0]
    rows=c.execute('SELECT * FROM '+TABLES[kind]+' WHERE '+sql+' ORDER BY '+order+' LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()
    if kind=='opportunities':
        items=[decode(r) for r in rows];signal_ids=list(dict.fromkeys(item['signal_id'] for item in items));signals={}
        if signal_ids:
            marks=','.join('?' for _ in signal_ids);days=preferences(c)['source_retention_days']
            signal_items=[decode(r) for r in c.execute('SELECT * FROM intent_signals WHERE organization_id=? AND id IN ('+marks+')',[org,*signal_ids]).fetchall()]
            for item in signal_items:
                if expired(item,days):item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
            signals={item['id']:item for item in ranked_signals(c,signal_items)}
        for item in items:
            signal=signals.get(item['signal_id'])
            if not signal:raise HTTPException(404,'Signal not found in this workspace.')
            item['score']=signal['score'];item['ranking']=signal['ranking'];item['signal']=signal
    elif kind!='signals':items=[decode(r) for r in rows]
    else:
        items=[]
        retention_days=preferences(c)['source_retention_days']
        # Bounds are strict; rows contain actual records, not fabricated result cards.
        for row in rows:
            item=decode(row)
            if expired(item,retention_days):item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
            items.append(item)
        ranked_signals(c,items)
        ids=[i['id'] for i in items]
        links={key:[] for key in ids};saved_ids=set()
        if ids:
            marks=','.join('?' for _ in ids)
            for r in c.execute('SELECT x.signal_id,m.id,m.name FROM intent_monitor_signals x JOIN intent_monitors m ON m.id=x.monitor_id AND m.organization_id=x.organization_id WHERE x.organization_id=? AND x.signal_id IN ('+marks+')',[org,*ids]).fetchall():links[r['signal_id']].append({'id':r['id'],'name':r['name']})
            saved_ids={r[0] for r in c.execute('SELECT signal_id FROM intent_saved_signals WHERE organization_id=? AND signal_id IN ('+marks+')',[org,*ids]).fetchall()}
        for item in items:item['monitors']=links[item['id']];item['saved']=item['id'] in saved_ids
    return {'items':items,'total':total,'page':page,'page_size':size}

def save_monitor(c, body, key=None):
    ctx = context(c, True)
    config = body.configuration.model_dump(mode='json')
    from app.intent_radar.connectors import validate
    validate(c,body.configuration)
    encoded = json.dumps(config, sort_keys=True)
    fingerprint = hashlib.sha256(json.dumps([body.name,body.description,body.goal,config,body.status],sort_keys=True).encode()).hexdigest()
    lock(c)
    from app.billing.usage import capacity
    count=c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived'",(ctx.organization_id,)).fetchone()[0]
    if key:
        old = get(c,'monitors',key)
        if old['status']=='Archived' and body.status!='Archived':capacity(c,'monitors',count)
        if old['status']=='Archived' and body.status!='Archived' and c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived'",(ctx.organization_id,)).fetchone()[0]>=get_settings().intent_radar_monitor_limit:raise HTTPException(429,'Monitor limit reached; archive an unused monitor before restoring this one.')
        if body.revision != old['revision']: raise HTTPException(409, 'Monitor changed. Reload before editing.')
        changed = c.execute('UPDATE intent_monitors SET name=?,description=?,goal=?,configuration_json=?,status=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?', (body.name,body.description,body.goal,encoded,body.status,now(),key,ctx.organization_id,body.revision)).rowcount
        if not changed: raise HTTPException(409,'Monitor changed. Reload before editing.')
        c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id IN (SELECT signal_id FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?)',(ctx.organization_id,ctx.organization_id,key))
    else:
        old = c.execute('SELECT id,fingerprint FROM intent_monitors WHERE organization_id=? AND request_id=?',(ctx.organization_id,str(body.request_id))).fetchone()
        if old:
            if old['fingerprint'] != fingerprint: raise HTTPException(409,'Request ID belongs to different monitor content.')
            return get(c,'monitors',old['id'])
        if c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived'",(ctx.organization_id,)).fetchone()[0] >= get_settings().intent_radar_monitor_limit: raise HTTPException(429,'Monitor limit reached; archive an unused monitor.')
        capacity(c,'monitors',count)
        key = str(uuid.uuid4())
        c.execute('INSERT INTO intent_monitors(id,organization_id,created_by,name,description,goal,configuration_json,status,request_id,fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,ctx.organization_id,ctx.actor,body.name,body.description,body.goal,encoded,body.status,str(body.request_id),fingerprint,now(),now()))
    audit(c,'MONITOR_SAVED',key)
    return get(c,'monitors',key)

def preferences(c, body=None):
    ctx = context(c, body is not None, body is not None)
    old = c.execute('SELECT * FROM intent_preferences WHERE organization_id=?',(ctx.organization_id,)).fetchone()
    if body is None: return {**models.Preferences().model_dump(), **(json.loads(old['configuration_json']) if old else {}), 'revision': old['revision'] if old else 0}
    if body.default_icp_id:
        from app.icp.service import get as get_icp
        get_icp(c,str(body.default_icp_id))
    lock(c)
    old = c.execute('SELECT * FROM intent_preferences WHERE organization_id=?',(ctx.organization_id,)).fetchone()
    if body.revision != (old['revision'] if old else 0): raise HTTPException(409,'Preferences changed; reload first.')
    c.execute('INSERT INTO intent_preferences(organization_id,configuration_json,updated_at) VALUES(?,?,?) ON CONFLICT(organization_id) DO UPDATE SET configuration_json=excluded.configuration_json,updated_at=excluded.updated_at,revision=intent_preferences.revision+1',(ctx.organization_id,json.dumps(body.model_dump(mode='json',exclude={'revision'})),now()))
    audit(c,'PREFERENCES_SAVED',ctx.organization_id)
    return preferences(c)

def saved(c,*,page=1,size=25,search='',collection='',sort='newest'):
    org = context(c).organization_id
    where='organization_id=?';args=[org]
    if collection:where+=' AND collection=?';args.append(collection)
    if search:where+=' AND (LOWER(notes) LIKE ? OR LOWER(collection) LIKE ? OR LOWER(tags_json) LIKE ?)';args.extend(['%'+search.casefold()+'%']*3)
    if not 1<=page<=10000 or not 1<=size<=100:raise HTTPException(422,'Bounded saved pagination required.')
    total=c.execute('SELECT COUNT(*) FROM intent_saved_signals WHERE '+where,args).fetchone()[0]
    orders={'newest':'saved_at DESC,signal_id','oldest':'saved_at,signal_id','collection':'collection,signal_id'}
    if sort not in orders:raise HTTPException(422,'Unsupported saved sort.')
    collections=[r[0] for r in c.execute('SELECT DISTINCT collection FROM intent_saved_signals WHERE organization_id=? ORDER BY collection LIMIT 100',(org,)).fetchall()]
    items=[decode(r) for r in c.execute('SELECT * FROM intent_saved_signals WHERE '+where+' ORDER BY '+orders[sort]+' LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()]
    ids=[item['signal_id'] for item in items]
    if ids:
        days=preferences(c)['source_retention_days']
        signals=[decode(r) for r in c.execute('SELECT * FROM intent_signals WHERE organization_id=? AND id IN ('+','.join('?' for _ in ids)+')',[org,*ids]).fetchall()]
        for signal in signals:
            if not signal['available'] or expired(signal,days):signal.update(available=0,title='Source item unavailable',excerpt='',evidence={})
        by_id={signal['id']:signal for signal in ranked_signals(c,signals)}
        for item in items:
            if item['signal_id'] not in by_id:raise HTTPException(404,'Saved source not found in this workspace.')
            item['signal']=by_id[item['signal_id']]
    return {'items':items,'page':page,'page_size':size,'total':total,'collections':collections}

def bookmark(c, key, body=None, remove=False):
    ctx = context(c,True); get(c,'signals',key); lock(c)
    if remove:
        c.execute('DELETE FROM intent_saved_signals WHERE organization_id=? AND signal_id=?',(ctx.organization_id,key))
        c.execute("UPDATE intent_signals SET status='Reviewed',revision=revision+1 WHERE id=? AND organization_id=? AND status='Saved'",(key,ctx.organization_id))
    elif body:
        if not c.execute('UPDATE intent_saved_signals SET collection=?,tags_json=?,notes=?,revision=revision+1 WHERE organization_id=? AND signal_id=? AND revision=?',(body.collection,json.dumps(body.tags),body.notes,ctx.organization_id,key,body.revision)).rowcount: raise HTTPException(409,'Saved signal changed; reload first.')
    else:
        c.execute('INSERT INTO intent_saved_signals(organization_id,signal_id,saved_by,saved_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,signal_id) DO NOTHING',(ctx.organization_id,key,ctx.actor,now()))
        c.execute("UPDATE intent_signals SET status='Saved',revision=revision+1 WHERE id=? AND organization_id=? AND status<>'Saved'",(key,ctx.organization_id))
    audit(c,'BOOKMARK_UPDATED',key)
    return get(c,'signals',key)

def review(c,key,body):
    org = context(c,True).organization_id; get(c,'signals',key)
    if not c.execute('UPDATE intent_signals SET status=?,notes=COALESCE(?,notes),revision=revision+1 WHERE id=? AND organization_id=? AND revision=?',(body.status,body.notes,key,org,body.revision)).rowcount: raise HTTPException(409,'Signal changed; reload before saving.')
    if body.status == 'Saved': bookmark(c,key)
    audit(c,'SIGNAL_REVIEWED',key)
    return get(c,'signals',key)

def opportunity(c,key,body=None):
    ctx = context(c,True); lock(c)
    if body:
        old = get(c,'opportunities',key)
        if body.assigned_to:
            from app.api.organization import membership_role
            if not membership_role(c,body.assigned_to,ctx.organization_id): raise HTTPException(404,'Assignee is not an active workspace member.')
        if not c.execute('UPDATE intent_opportunities SET status=?,priority=?,notes=?,next_action=?,assigned_to=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.status,body.priority,body.notes,body.next_action,body.assigned_to,now(),key,ctx.organization_id,body.revision)).rowcount: raise HTTPException(409,'Opportunity changed; reload before saving.')
    else:
        get(c,'signals',key)
        signal_id = key; key = str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id + ':intent-opportunity:' + signal_id))
        from app.billing.usage import reserve
        reserve(c,{'opportunities':1},key)
        c.execute('INSERT INTO intent_opportunities(id,organization_id,signal_id,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,signal_id) DO NOTHING',(key,ctx.organization_id,signal_id,ctx.actor,now(),now()))
        c.execute("UPDATE intent_signals SET status='Reviewed',revision=revision+1 WHERE id=? AND organization_id=? AND status<>'Reviewed'",(signal_id,ctx.organization_id))
    audit(c,'OPPORTUNITY_UPDATED',key)
    return get(c,'opportunities',key)

def mark_alert(c,key,read):
    org=context(c,True).organization_id; get(c,'alerts',key)
    c.execute('UPDATE intent_alerts SET read_at=? WHERE id=? AND organization_id=?',(now() if read else None,key,org))
    # Acknowledge the corresponding shared notification for this actor only.
    c.execute('UPDATE workspace_notifications SET read_at=? WHERE organization_id=? AND user_id=? AND entity_id=?',(now() if read else None,org,context(c).actor,key))
    return get(c,'alerts',key)

def alert(c,event_key,title,description,monitor_id=None,signal_id=None,actor=None):
    org=context(c).organization_id; key=str(uuid.uuid5(uuid.NAMESPACE_URL,org+':intent-alert:'+event_key))
    changed=c.execute('INSERT INTO intent_alerts(id,organization_id,monitor_id,signal_id,event_key,title,description,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,event_key) DO NOTHING',(key,org,monitor_id,signal_id,event_key,title,description,now())).rowcount
    if changed and actor:
        c.execute('INSERT INTO workspace_notifications(id,organization_id,user_id,kind,entity_id,created_at) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),org,actor,'INTENT_RADAR',key,now()))

def overview(c):
    org=context(c).organization_id
    from app.intent_radar.operations import overview as operational_overview
    retention,retention_args=retention_sql(c,preferences(c)['source_retention_days'])
    counts=dict(c.execute("""SELECT
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND status='New' AND available=1 AND """+retention+""" ) new_signals,
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND status='Reviewed') reviewed_signals,
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND """+rank_expression()+""">=85 AND available=1 AND """+retention+""") high_relevance,
        (SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active') active_monitors,
        (SELECT COUNT(*) FROM intent_opportunities WHERE organization_id=? AND status='Saved') saved_opportunities,
        (SELECT COUNT(*) FROM intent_alerts WHERE organization_id=? AND read_at IS NULL) unread_alerts""",
        (org,*retention_args,org,org,*retention_args,org,org,org)).fetchone())
    return {**counts,'operations':operational_overview(c,include_sources=False),
            'trends':[dict(r) for r in c.execute('SELECT SUBSTR(observed_at,1,10) AS "day",COUNT(*) volume FROM intent_signals WHERE organization_id=? AND available=1 GROUP BY SUBSTR(observed_at,1,10) ORDER BY "day" DESC LIMIT 14',(org,)).fetchall()],
             'recent_signals':listing(c,'signals',size=5)['items'],'monitors':listing(c,'monitors',size=5)['items'],'opportunities':listing(c,'opportunities',size=5)['items'],'alerts':listing(c,'alerts',size=5)['items']}

def remove_source(c,key):
    """Withdraw public content while preserving customer annotations and history."""
    ctx=context(c,True,True);signal=get(c,'signals',key);lock(c)
    c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json=?,revision=revision+1 WHERE id=? AND organization_id=?",(json.dumps({'removed_by_policy':True}),key,ctx.organization_id))
    c.execute('DELETE FROM intent_analyses WHERE signal_id=? AND organization_id=?',(key,ctx.organization_id))
    c.execute('DELETE FROM intent_rankings WHERE signal_id=? AND organization_id=?',(key,ctx.organization_id))
    c.execute("UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND signal_id=?",(ctx.organization_id,key))
    for row in c.execute('SELECT fingerprint,result_json FROM intent_source_cache WHERE organization_id=? LIMIT 1000',(ctx.organization_id,)).fetchall():
        data=json.loads(row['result_json']);items=data if isinstance(data,list) else data.get('items',[])
        remaining=[x for x in items if x.get('source_url')!=signal['source_url']]
        if len(remaining)!=len(items):
            if isinstance(data,list):data=remaining
            else:data['items']=remaining
            c.execute('UPDATE intent_source_cache SET result_json=? WHERE organization_id=? AND fingerprint=?',(json.dumps(data),ctx.organization_id,row['fingerprint']))
    audit(c,'SOURCE_CONTENT_WITHDRAWN',key)
    return get(c,'signals',key)
