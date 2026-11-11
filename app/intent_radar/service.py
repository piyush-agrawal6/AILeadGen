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
        if expired(item):
            item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
        item['monitors'] = [dict(r) for r in c.execute('SELECT m.id,m.name FROM intent_monitors m JOIN intent_monitor_signals x ON x.monitor_id=m.id AND x.organization_id=m.organization_id WHERE x.organization_id=? AND x.signal_id=?', (org, key)).fetchall()]
        item['saved'] = bool(c.execute('SELECT 1 FROM intent_saved_signals WHERE organization_id=? AND signal_id=?', (org, key)).fetchone())
    return item

def expired(signal):
    policy=signal.get('evidence',{}).get('provenance',{})
    days=policy.get('retention_days')
    if not isinstance(days,int):return False
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(signal['retrieved_at'])).total_seconds()>days*86400
    except (ValueError,KeyError,TypeError):return True

def expire_content(c):
    org=context(c,True).organization_id;count=0
    for row in c.execute('SELECT * FROM intent_signals WHERE organization_id=? AND available=1 ORDER BY retrieved_at LIMIT 1000',(org,)).fetchall():
        signal=decode(row)
        if not expired(signal):continue
        changed=c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json='{}',revision=revision+1 WHERE id=? AND organization_id=? AND retrieved_at=?",(signal['id'],org,signal['retrieved_at'])).rowcount
        if changed:
            c.execute('DELETE FROM intent_analyses WHERE organization_id=? AND signal_id=?',(org,signal['id']));count+=1
            c.execute("UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND signal_id=?",(org,signal['id']))
    for row in c.execute('SELECT fingerprint,result_json FROM intent_source_cache WHERE organization_id=? LIMIT 1000',(org,)).fetchall():
        data=json.loads(row['result_json']);items=data if isinstance(data,list) else data.get('items',[])
        remaining=[x for x in items if not expired({'retrieved_at':x.get('retrieved_at'),'evidence':{'provenance':x.get('provenance',{})}})]
        if len(remaining)!=len(items):
            if isinstance(data,list):data=remaining
            else:data['items']=remaining;data.pop('etag',None);data.pop('last_modified',None)
            c.execute('UPDATE intent_source_cache SET result_json=? WHERE organization_id=? AND fingerprint=?',(json.dumps(data),org,row['fingerprint']))
    return {'expired_source_items':count,'customer_notes_preserved':True}

def listing(c, kind, *, page=1, size=25, search='', status='', category='', source='', min_score=0, monitor_id='', saved='', from_date='', to_date='', sort='newest'):
    org = context(c).organization_id
    where, args = 'organization_id=?', [org]
    if search:
        field = 'name' if kind == 'monitors' else 'title' if kind in ('signals','alerts') else 'notes'
        where += f' AND LOWER({field}) LIKE ?'; args.append('%' + search.casefold() + '%')
    if status and kind != 'alerts': where += ' AND status=?'; args.append(status)
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

def save_monitor(c, body, key=None):
    ctx = context(c, True)
    config = body.configuration.model_dump(mode='json')
    from app.intent_radar.connectors import validate
    validate(c,body.configuration)
    encoded = json.dumps(config, sort_keys=True)
    fingerprint = hashlib.sha256(json.dumps([body.name,body.description,body.goal,config,body.status],sort_keys=True).encode()).hexdigest()
    lock(c)
    if key:
        old = get(c,'monitors',key)
        if old['status']=='Archived' and body.status!='Archived' and c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived'",(ctx.organization_id,)).fetchone()[0]>=get_settings().intent_radar_monitor_limit:raise HTTPException(429,'Monitor limit reached; archive an unused monitor before restoring this one.')
        if body.revision != old['revision']: raise HTTPException(409, 'Monitor changed. Reload before editing.')
        changed = c.execute('UPDATE intent_monitors SET name=?,description=?,goal=?,configuration_json=?,status=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?', (body.name,body.description,body.goal,encoded,body.status,now(),key,ctx.organization_id,body.revision)).rowcount
        if not changed: raise HTTPException(409,'Monitor changed. Reload before editing.')
    else:
        old = c.execute('SELECT id,fingerprint FROM intent_monitors WHERE organization_id=? AND request_id=?',(ctx.organization_id,str(body.request_id))).fetchone()
        if old:
            if old['fingerprint'] != fingerprint: raise HTTPException(409,'Request ID belongs to different monitor content.')
            return get(c,'monitors',old['id'])
        if c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived'",(ctx.organization_id,)).fetchone()[0] >= get_settings().intent_radar_monitor_limit: raise HTTPException(429,'Monitor limit reached; archive an unused monitor.')
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

def saved(c):
    org = context(c).organization_id
    return {'items':[decode(r) for r in c.execute('SELECT * FROM intent_saved_signals WHERE organization_id=? ORDER BY saved_at DESC LIMIT 500',(org,)).fetchall()]}

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
    count=lambda table,where='',args=():c.execute(f'SELECT COUNT(*) FROM {table} WHERE organization_id=?'+where,(org,*args)).fetchone()[0]
    return {'new_signals':count('intent_signals'," AND status='New' AND available=1"),'reviewed_signals':count('intent_signals'," AND status='Reviewed'"),'high_relevance':count('intent_signals',' AND score>=85 AND available=1'),
            'active_monitors':count('intent_monitors'," AND status='Active'"),'saved_opportunities':count('intent_opportunities'," AND status='Saved'"),'unread_alerts':count('intent_alerts',' AND read_at IS NULL'),
            'trends':[dict(r) for r in c.execute('SELECT SUBSTR(observed_at,1,10) day,COUNT(*) volume FROM intent_signals WHERE organization_id=? AND available=1 GROUP BY SUBSTR(observed_at,1,10) ORDER BY day DESC LIMIT 14',(org,)).fetchall()],
             'recent_signals':listing(c,'signals',size=5)['items'],'monitors':listing(c,'monitors',size=5)['items'],'opportunities':listing(c,'opportunities',size=5)['items'],'alerts':listing(c,'alerts',size=5)['items']}

def remove_source(c,key):
    """Withdraw public content while preserving customer annotations and history."""
    ctx=context(c,True,True);signal=get(c,'signals',key);lock(c)
    c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json=?,revision=revision+1 WHERE id=? AND organization_id=?",(json.dumps({'removed_by_policy':True}),key,ctx.organization_id))
    c.execute('DELETE FROM intent_analyses WHERE signal_id=? AND organization_id=?',(key,ctx.organization_id))
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
