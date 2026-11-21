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

def attach_opportunity_policy(item):
    from app.intent_radar.opportunity_policy import assess
    item['opportunity_eligibility']=assess(item)
    return item

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
        if not item['available']:item['score']=0;item['ranking']={'basis':'Public source evidence is unavailable; no current relevance claim.'};attach_opportunity_policy(item);continue
        item['score']=row['adjusted_score'];item['ranking']=json.loads(row['explanation']) if row['explanation'] else {'version':'DETERMINISTIC_V3','basis':'Keyword evidence + bounded active workspace feedback'}
    for item in items:attach_opportunity_policy(item)
    return items

def ranked_signal(c,item):
    return ranked_signals(c,[item])[0]

def audit(c, action, key, details=None):
    ctx = context(c)
    c.execute(
        'INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()), ctx.actor, 'INTENT_RADAR_' + action, key, 'SUCCESS', json.dumps(details or {}), ctx.organization_id, now()),
    )

def decode(row):
    item = dict(row)
    for field in ('configuration', 'evidence', 'tags', 'schedule'):
        if field + '_json' in item: item[field] = json.loads(item.pop(field + '_json'))
    item.pop('fingerprint', None)
    return item

HIGH_INTENT_SQL = (
    "("
    "status <> 'Dismissed' AND category <> 'Market / technology intelligence' AND ("
    "EXISTS(SELECT 1 FROM intent_rankings hr WHERE hr.organization_id=intent_signals.organization_id AND hr.signal_id=intent_signals.id "
    "AND (hr.explanation_json LIKE '%\"intent_strength\": \"Explicit evidence\"%' OR hr.explanation_json LIKE '%\"intent_strength\":\"Explicit evidence\"%') "
    "AND hr.explanation_json NOT LIKE '%\"excluded\": [\"%' AND hr.explanation_json NOT LIKE '%\"excluded\":[\"%') "
    "OR ("
    "category IN ('Recommendation request','Product comparison','Alternative search','Tool / service evaluation','Purchase consideration') "
    "AND (evidence_json LIKE '%\"intent_phrase\": \"%' OR evidence_json LIKE '%\"intent_phrase\":\"%') "
    "AND (evidence_json LIKE '%\"penalties\": []%' OR evidence_json LIKE '%\"penalties\":[]%' OR evidence_json NOT LIKE '%\"penalties\"%')"
    ")"
    "))"
)

def _extract_buying_intent_and_icp(item, latest_analysis=None):
    """Derive truthful buying-intent and ICP-fit summaries without fabricating unassessed values."""
    if latest_analysis:
        structured = latest_analysis.get('structured')
        if not structured and latest_analysis.get('interpretation'):
            from app.intent_radar import intelligence
            try:
                interp = intelligence.Interpretation.model_validate(latest_analysis['interpretation'])
                structured = intelligence.structured_summary(item, interp, latest_analysis.get('scoring') or {}, latest_analysis.get('icp'))
            except Exception:
                structured = None
        if structured and structured.get('buying_intent'):
            icp_label = structured.get('icp_fit') or 'Unassessed — no ICP selected'
            icp_tier = 'Unassessed'
            if icp_label.startswith('Aligned'):
                icp_tier = 'Match'
            elif icp_label.startswith('Partial mismatch'):
                icp_tier = 'Mismatch'
            elif latest_analysis.get('icp') and 'Possible' in icp_label:
                icp_tier = 'Possible'
            return {
                'buying_intent': structured['buying_intent'],
                'buying_intent_basis': 'ai_assessed',
                'icp_fit': icp_tier,
                'icp_fit_detail': icp_label,
                'has_analysis': True,
                'latest_analysis_at': latest_analysis.get('analysis_at'),
                'latest_analysis_summary': structured.get('summary'),
                'latest_analysis_mode': latest_analysis.get('mode'),
            }
    return {
        'buying_intent': None,
        'buying_intent_basis': 'unassessed',
        'icp_fit': 'Unassessed',
        'icp_fit_detail': 'Not assessed — run Analyze Signal with an ICP to evaluate fit.',
        'has_analysis': False,
        'latest_analysis_at': None,
        'latest_analysis_summary': None,
        'latest_analysis_mode': None,
    }


def _hydrate_signal_metadata(c, org: str, items: list[dict], actor: str | None = None):
    if not items:
        return items
    ids = [i['id'] for i in items]
    marks = ','.join('?' for _ in ids)
    links: dict[str, list[dict]] = {key: [] for key in ids}
    for r in c.execute(
        'SELECT x.signal_id,m.id,m.name FROM intent_monitor_signals x '
        'JOIN intent_monitors m ON m.id=x.monitor_id AND m.organization_id=x.organization_id '
        'WHERE x.organization_id=? AND x.signal_id IN (' + marks + ')',
        [org, *ids],
    ).fetchall():
        links[r['signal_id']].append({'id': r['id'], 'name': r['name']})

    saved_ids = {
        r[0]
        for r in c.execute(
            'SELECT signal_id FROM intent_saved_signals WHERE organization_id=? AND signal_id IN (' + marks + ')',
            [org, *ids],
        ).fetchall()
    }

    opps: dict[str, dict] = {}
    for r in c.execute(
        'SELECT signal_id,id,status,priority FROM intent_opportunities WHERE organization_id=? AND signal_id IN (' + marks + ')',
        [org, *ids],
    ).fetchall():
        opps[r['signal_id']] = {'id': r['id'], 'status': r['status'], 'priority': r['priority']}

    latest_analyses: dict[str, dict] = {}
    for r in c.execute(
        'SELECT signal_id,analysis_json,created_at FROM intent_analyses '
        'WHERE organization_id=? AND signal_id IN (' + marks + ') ORDER BY created_at DESC',
        [org, *ids],
    ).fetchall():
        sid = r['signal_id']
        if sid not in latest_analyses:
            try:
                latest_analyses[sid] = json.loads(r['analysis_json'])
            except Exception:
                pass

    actor_feedback: dict[str, dict] = {}
    if actor:
        for r in c.execute(
            'SELECT signal_id,label,note,active,updated_at FROM intent_feedback '
            'WHERE organization_id=? AND actor=? AND signal_id IN (' + marks + ')',
            [org, actor, *ids],
        ).fetchall():
            if r['active']:
                actor_feedback[r['signal_id']] = {'label': r['label'], 'note': r['note'], 'updated_at': r['updated_at']}

    discovery_ids = list(dict.fromkeys(
        str(i.get('evidence', {}).get('discovery_id'))
        for i in items
        if i.get('evidence', {}).get('discovery_id')
    ))
    discovery_titles: dict[str, str] = {}
    if discovery_ids:
        dmarks = ','.join('?' for _ in discovery_ids)
        try:
            for r in c.execute(
                'SELECT discovery_id,title FROM intent_discovery_runs_meta '
                'WHERE organization_id=? AND discovery_id IN (' + dmarks + ')',
                [org, *discovery_ids],
            ).fetchall():
                if r['title']:
                    discovery_titles[r['discovery_id']] = r['title']
        except Exception:
            pass

    for item in items:
        sid = item['id']
        item['monitors'] = links[sid]
        item['saved'] = sid in saved_ids
        opp = opps.get(sid)
        item['opportunity_id'] = opp['id'] if opp else None
        item['opportunity_status'] = opp['status'] if opp else None
        disc_id = item.get('evidence', {}).get('discovery_id')
        item['discovery_id'] = str(disc_id) if disc_id else None
        item['discovery_title'] = discovery_titles.get(str(disc_id)) if disc_id else None
        fb = actor_feedback.get(sid)
        item['feedback_label'] = fb['label'] if fb else None
        item.update(_extract_buying_intent_and_icp(item, latest_analyses.get(sid)))
    return items


def _signal_activity(c, org: str, item: dict) -> list[dict]:
    key = item['id']
    events: list[dict] = []
    prov = (item.get('evidence') or {}).get('provenance') or {}
    fetch_method = prov.get('fetch_method') or 'public_source'
    events.append({
        'kind': 'collected',
        'title': f"Collected from {item.get('source', 'public source')}",
        'detail': f"Via {str(fetch_method).replace('_', ' ')}" + (f" · {prov.get('repo')}" if prov.get('repo') else ''),
        'actor': None,
        'at': item.get('retrieved_at') or item.get('observed_at'),
    })
    saved_row = c.execute(
        'SELECT saved_by,saved_at,collection FROM intent_saved_signals WHERE organization_id=? AND signal_id=?',
        (org, key),
    ).fetchone()
    if saved_row:
        events.append({
            'kind': 'saved',
            'title': 'Saved to research bookmarks',
            'detail': f"Collection: {saved_row['collection'] or 'Inbox'}",
            'actor': saved_row['saved_by'],
            'at': saved_row['saved_at'],
        })
    for r in c.execute(
        'SELECT created_at,analysis_json FROM intent_analyses WHERE organization_id=? AND signal_id=? ORDER BY created_at DESC LIMIT 5',
        (org, key),
    ).fetchall():
        try:
            data = json.loads(r['analysis_json'])
            mode = data.get('mode') or 'Analysis'
            model = data.get('model') or ''
            events.append({
                'kind': 'analysis',
                'title': f"AI analysis completed ({mode})",
                'detail': model or 'Evidence-grounded evaluation',
                'actor': None,
                'at': r['created_at'],
            })
        except Exception:
            pass
    for r in c.execute(
        'SELECT actor,label,note,active,updated_at FROM intent_feedback WHERE organization_id=? AND signal_id=? ORDER BY updated_at DESC LIMIT 10',
        (org, key),
    ).fetchall():
        events.append({
            'kind': 'feedback',
            'title': f"Reviewer feedback: {r['label']}" + ('' if r['active'] else ' (disabled)'),
            'detail': r['note'] or '',
            'actor': r['actor'],
            'at': r['updated_at'],
        })
    opp_row = c.execute(
        'SELECT id,status,priority,created_by,created_at FROM intent_opportunities WHERE organization_id=? AND signal_id=?',
        (org, key),
    ).fetchone()
    if opp_row:
        events.append({
            'kind': 'opportunity',
            'title': f"Linked opportunity ({opp_row['status']}, {opp_row['priority']} priority)",
            'detail': opp_row['id'],
            'actor': opp_row['created_by'],
            'at': opp_row['created_at'],
        })
    has_saved_row = bool(saved_row)
    has_feedback_rows = any(e['kind'] == 'feedback' for e in events)
    for r in c.execute(
        "SELECT actor,action,details_json,created_at FROM audit_log WHERE organization_id=? AND entity=? AND action LIKE 'INTENT_RADAR_%' ORDER BY created_at DESC LIMIT 15",
        (org, key),
    ).fetchall():
        act = r['action']
        if act == 'INTENT_RADAR_BOOKMARK_UPDATED' and has_saved_row:
            continue
        if act == 'INTENT_RADAR_FEEDBACK_UPDATED' and has_feedback_rows:
            continue
        label_map = {
            'INTENT_RADAR_SIGNAL_REVIEWED': 'Signal reviewed',
            'INTENT_RADAR_BOOKMARK_UPDATED': 'Bookmark updated',
            'INTENT_RADAR_FEEDBACK_UPDATED': 'Feedback updated',
            'INTENT_RADAR_SOURCE_CONTENT_WITHDRAWN': 'Source content withdrawn',
        }
        if act in label_map:
            detail_str = ''
            title_str = label_map[act]
            if r['details_json']:
                try:
                    d = json.loads(r['details_json'])
                    if d.get('status'):
                        title_str = f"Status set to {d['status']}"
                    if d.get('notes_updated'):
                        detail_str = 'Review notes updated'
                except Exception:
                    pass
            events.append({
                'kind': 'audit',
                'title': title_str,
                'detail': detail_str,
                'actor': r['actor'],
                'at': r['created_at'],
            })
    events.sort(key=lambda e: str(e.get('at') or ''), reverse=True)
    return events[:30]


def get(c, kind, key):
    ctx = context(c)
    org = ctx.organization_id
    table = TABLES[kind]
    row = c.execute(f'SELECT * FROM {table} WHERE organization_id=? AND id=?', (org, key)).fetchone()
    if not row: raise HTTPException(404, 'Intent Radar record not found.')
    item = decode(row)
    if kind == 'signals':
        if expired(item,preferences(c)['source_retention_days']):
            item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
        ranked_signal(c,item)
        _hydrate_signal_metadata(c, org, [item], actor=ctx.actor)
        attach_opportunity_policy(item)
        item['activity'] = _signal_activity(c, org, item)
    if kind=='opportunities':
        signal=get(c,'signals',item['signal_id'])
        item['score']=signal['score']
        item['ranking']=signal.get('ranking')
        item['opportunity_eligibility']=signal.get('opportunity_eligibility')
        item['signal']=signal
    if kind=='monitors':
        item['signals_count']=c.execute('SELECT COUNT(*) FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?',(org,key)).fetchone()[0]
    return item

def expired(signal,retention_days=30):
    policy=signal.get('evidence',{}).get('provenance',{})
    days=policy.get('retention_days')
    days=min(days,retention_days) if type(days) is int and days>0 else retention_days
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(signal['retrieved_at'])).total_seconds()>days*86400
    except (ValueError,KeyError,TypeError):return True

def retention_sql(c,days,alias='intent_signals'):
    return retention_predicate(c,'?',alias),[days,days,now()]

def retention_predicate(c,days_expression,alias='intent_signals'):
    if days_expression not in ('?','policy.days') or alias not in ('intent_signals','s'):raise ValueError('Internal retention expression required.')
    policy=("CAST("+alias+".evidence_json AS JSONB)->'provenance'->>'retention_days'" if getattr(c,'backend','sqlite')=='postgres' else "json_extract("+alias+".evidence_json,'$.provenance.retention_days')")
    policy='CAST(('+policy+') AS INTEGER)'
    effective='CASE WHEN '+policy+' BETWEEN 1 AND '+days_expression+' THEN '+policy+' ELSE '+days_expression+' END'
    if getattr(c,'backend','sqlite')=='postgres':
        predicate='(CAST('+alias+'.retrieved_at AS TIMESTAMPTZ) + ('+effective+") * INTERVAL '1 day') > CAST(? AS TIMESTAMPTZ)"
    else:predicate='julianday('+alias+'.retrieved_at) + ('+effective+') > julianday(?)'
    return predicate

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
            from app.notifications import center
            center.redact_signal_alerts(c, org, signal['id'])
    caches=c.execute('SELECT fingerprint,result_json FROM intent_source_cache WHERE organization_id=? AND fingerprint>? ORDER BY fingerprint LIMIT 1000',(org,cache_after)).fetchall()
    for row in caches:
        data=json.loads(row['result_json']);items=data if isinstance(data,list) else data.get('items',[])
        remaining=[x for x in items if not expired({'retrieved_at':x.get('retrieved_at'),'evidence':{'provenance':x.get('provenance',{})}},retention_days)]
        if len(remaining)!=len(items):
            if isinstance(data,list):data=remaining
            else:data['items']=remaining;data.pop('etag',None);data.pop('last_modified',None)
            c.execute('UPDATE intent_source_cache SET result_json=? WHERE organization_id=? AND fingerprint=?',(json.dumps(data),org,row['fingerprint']))
    c.execute('INSERT INTO intent_retention_cursors(organization_id,signal_after,cache_after,updated_at) VALUES(?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET signal_after=excluded.signal_after,cache_after=excluded.cache_after,updated_at=excluded.updated_at',(org,rows[-1]['id'] if len(rows)==1000 else '',caches[-1]['fingerprint'] if len(caches)==1000 else '',now()))
    try:
        c.execute('DELETE FROM intent_stream_matches WHERE organization_id=? AND expires_at<=?',(org,now()))
        c.execute("DELETE FROM intent_provider_cache WHERE expires_at<=? AND state!='FETCHING' AND (scope='public' OR scope LIKE ?)",(now(),'workspace:'+org+'%'))
    except Exception:
        pass
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
    if kind == 'monitors':
        rows = c.execute(
            f'SELECT m.*, (SELECT COUNT(*) FROM intent_monitor_signals s WHERE s.organization_id=m.organization_id AND s.monitor_id=m.id) AS signals_count '
            f'FROM {TABLES[kind]} m WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?',
            [*args, size, (page-1)*size]
        ).fetchall()
        return {'items': [decode(r) for r in rows], 'total': total, 'page': page, 'page_size': size}
    rows = c.execute(f'SELECT * FROM {TABLES[kind]} WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?', [*args,size,(page-1)*size]).fetchall()
    return {'items': [get(c,kind,r['id']) for r in rows], 'total': total, 'page':page, 'page_size':size}

def listing(c,kind,**filters):
    if kind not in ('signals','opportunities','alerts'):return _listing(c,kind,**filters)
    ctx=context(c);org=ctx.organization_id;page=filters.get('page',1);size=filters.get('size',25)
    if not 1<=page<=10000 or not 1<=size<=100:raise HTTPException(422,'Bounded pagination required.')
    where=['organization_id=?'];args=[org];sort=filters.get('sort','newest')
    view_counts = None
    status_counts = None
    if kind == 'opportunities':
        if filters.get('status') and filters['status'] not in ('', 'all', 'All'):
            where.append('status=?'); args.append(filters['status'])
        if filters.get('priority'):
            where.append('priority=?'); args.append(filters['priority'])
        if filters.get('assigned_to'):
            if filters['assigned_to'] == 'unassigned':
                where.append("(assigned_to IS NULL OR assigned_to='')")
            else:
                where.append('LOWER(assigned_to)=?'); args.append(filters['assigned_to'].strip().lower())
        if filters.get('source'):
            where.append('signal_id IN (SELECT id FROM intent_signals WHERE organization_id=? AND source=?)')
            args.extend([org, filters['source']])
        if filters.get('search'):
            qtext = '%'+filters['search'].casefold()+'%'
            where.append("(LOWER(notes) LIKE ? OR LOWER(next_action) LIKE ? OR LOWER(COALESCE(assigned_to,'')) LIKE ? OR signal_id IN (SELECT id FROM intent_signals WHERE organization_id=? AND (LOWER(title) LIKE ? OR LOWER(excerpt) LIKE ? OR LOWER(source) LIKE ?)))")
            args.extend([qtext, qtext, qtext, org, qtext, qtext, qtext])
        feedback_rank = "(SELECT " + rank_expression('s') + " FROM intent_signals s WHERE s.id=intent_opportunities.signal_id AND s.organization_id=intent_opportunities.organization_id) DESC"
        order_map = {
            'newest': f"CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, {feedback_rank}, created_at DESC, id",
            'oldest': 'created_at ASC, id',
            'updated': 'updated_at DESC, id',
            'priority': f"CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, {feedback_rank}, updated_at DESC, id",
        }
        order = order_map.get(sort, f"CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, {feedback_rank}, created_at DESC, id")
        sc_row = c.execute(
            "SELECT COUNT(*) AS all_count,"
            "COALESCE(SUM(CASE WHEN status='New' THEN 1 ELSE 0 END),0) AS new_count,"
            "COALESCE(SUM(CASE WHEN status='Reviewing' THEN 1 ELSE 0 END),0) AS reviewing_count,"
            "COALESCE(SUM(CASE WHEN status='Qualified' THEN 1 ELSE 0 END),0) AS qualified_count,"
            "COALESCE(SUM(CASE WHEN status='Saved' THEN 1 ELSE 0 END),0) AS saved_count,"
            "COALESCE(SUM(CASE WHEN status='Dismissed' THEN 1 ELSE 0 END),0) AS dismissed_count "
            "FROM intent_opportunities WHERE organization_id=?",
            (org,),
        ).fetchone()
        status_counts = {
            'all': int(sc_row['all_count'] or 0),
            'new': int(sc_row['new_count'] or 0),
            'reviewing': int(sc_row['reviewing_count'] or 0),
            'qualified': int(sc_row['qualified_count'] or 0),
            'saved': int(sc_row['saved_count'] or 0),
            'dismissed': int(sc_row['dismissed_count'] or 0),
        }
    elif filters.get('search'):
        qtext = '%'+filters['search'].casefold()+'%'
        if kind == 'signals':
            where.append('(LOWER(title) LIKE ? OR LOWER(excerpt) LIKE ? OR LOWER(source) LIKE ?)')
            args.extend([qtext, qtext, qtext])
        else:
            field='title' if kind=='alerts' else 'notes'
            where.append('LOWER('+field+') LIKE ?');args.append(qtext)
    if filters.get('status') and kind not in ('alerts', 'opportunities'):
        where.append('status=?');args.append(filters['status'])
    if kind=='signals':
        retention_days = preferences(c)['source_retention_days']
        retention,retention_args=retention_sql(c,retention_days)
        where+=['available=1',rank_expression()+'>=?'];args.append(filters.get('min_score',0))
        where.append(retention);args.extend(retention_args)

        view = filters.get('view') or ''
        if view == 'needs_review':
            where.append("status IN ('New','Needs Review','In Review')")
        elif view == 'high_intent':
            where.append(HIGH_INTENT_SQL)
        elif view == 'saved':
            where.append('EXISTS(SELECT 1 FROM intent_saved_signals s WHERE s.organization_id=intent_signals.organization_id AND s.signal_id=intent_signals.id)')
        elif view == 'qualified':
            where.append("status='Qualified'")
        elif view == 'dismissed':
            where.append("status='Dismissed'")

        if filters.get('category'):
            where.append('category=?'); args.append(filters['category'])
        if filters.get('source'):
            src_val = str(filters['source'])
            src_aliases = {
                'Atom Feeds': ('Atom', 'Atom Feeds'),
                'Atom': ('Atom', 'Atom Feeds'),
                'RSS Feeds': ('RSS', 'RSS Feeds', 'RSS / Atom'),
                'RSS': ('RSS', 'RSS Feeds', 'RSS / Atom'),
                'Discourse Communities': ('Discourse', 'Approved Discourse', 'Discourse Communities'),
                'Discourse': ('Discourse', 'Approved Discourse', 'Discourse Communities'),
            }
            if src_val in src_aliases:
                vals = src_aliases[src_val]
                where.append('source IN (' + ','.join('?' for _ in vals) + ')')
                args.extend(vals)
            else:
                where.append('source=?'); args.append(src_val)
        if filters.get('monitor_id'):
            get(c,'monitors',filters['monitor_id']);where.append('id IN (SELECT signal_id FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?)');args.extend([org,filters['monitor_id']])
        if filters.get('discovery_id'):
            did = str(filters['discovery_id'])
            where.append('(evidence_json LIKE ? OR evidence_json LIKE ?)')
            args.extend([f'%"discovery_id": "{did}"%', f'%"discovery_id":"{did}"%'])
        if filters.get('saved'):
            where.append(('NOT ' if filters['saved']=='unsaved' else '')+'EXISTS(SELECT 1 FROM intent_saved_signals s WHERE s.organization_id=intent_signals.organization_id AND s.signal_id=intent_signals.id)')
        buying_intent = filters.get('buying_intent') or ''
        if buying_intent == 'unassessed':
            where.append('NOT EXISTS(SELECT 1 FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id)')
        elif buying_intent == 'explicit':
            where.append("EXISTS(SELECT 1 FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id AND (a.analysis_json LIKE '%\"buying_intent\": \"Explicit commercial intent\"%' OR a.analysis_json LIKE '%\"intent_strength\": \"Explicit evidence\"%'))")
        elif buying_intent == 'possible':
            where.append("EXISTS(SELECT 1 FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id AND a.analysis_json LIKE '%\"buying_intent\": \"Possible commercial intent\"%')")
        elif buying_intent == 'none':
            where.append("EXISTS(SELECT 1 FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id AND (a.analysis_json LIKE '%\"buying_intent\": \"No demonstrated commercial intent\"%' OR a.analysis_json LIKE '%\"intent_strength\": \"Contradictory / non-buying\"%'))")
        elif buying_intent == 'insufficient':
            where.append("EXISTS(SELECT 1 FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id AND a.analysis_json LIKE '%\"buying_intent\": \"Insufficient evidence\"%')")
        icp_fit = filters.get('icp_fit') or ''
        if icp_fit == 'unassessed':
            where.append('NOT EXISTS(SELECT 1 FROM intent_rankings r WHERE r.organization_id=intent_signals.organization_id AND r.signal_id=intent_signals.id AND r.icp_id IS NOT NULL)')
        elif icp_fit == 'match':
            where.append("EXISTS(SELECT 1 FROM intent_rankings r WHERE r.organization_id=intent_signals.organization_id AND r.signal_id=intent_signals.id AND r.icp_id IS NOT NULL AND (r.explanation_json LIKE '%\"status\": \"MATCH\"%' OR r.explanation_json LIKE '%Problem/service wording matches target%'))")
        elif icp_fit == 'possible':
            where.append("EXISTS(SELECT 1 FROM intent_rankings r WHERE r.organization_id=intent_signals.organization_id AND r.signal_id=intent_signals.id AND r.icp_id IS NOT NULL AND r.explanation_json LIKE '%Possible service alignment%')")
        elif icp_fit == 'mismatch':
            where.append("EXISTS(SELECT 1 FROM intent_rankings r WHERE r.organization_id=intent_signals.organization_id AND r.signal_id=intent_signals.id AND r.icp_id IS NOT NULL AND r.explanation_json LIKE '%\"status\": \"MISMATCH\"%')")
        for field,operator,end in [('from_date','>=',''),('to_date','<','T23:59:59.999999+00:00')]:
            if filters.get(field):where.append('observed_at'+operator+'?');args.append(filters[field]+end)
        order_map = {
            'score': rank_expression()+' DESC,id DESC',
            'score_asc': rank_expression()+' ASC,id ASC',
            'title': 'LOWER(title) ASC,id ASC',
            'newest': 'observed_at DESC,id DESC',
            'oldest': 'observed_at ASC,id ASC',
        }
        order = order_map.get(sort, 'observed_at DESC,id DESC')
        vc_row = c.execute(
            "SELECT COUNT(*) AS all_count,"
            "COALESCE(SUM(CASE WHEN status IN ('New','Needs Review','In Review') THEN 1 ELSE 0 END),0) AS needs_review_count,"
            "COALESCE(SUM(CASE WHEN " + HIGH_INTENT_SQL + " THEN 1 ELSE 0 END),0) AS high_intent_count,"
            "COALESCE(SUM(CASE WHEN EXISTS(SELECT 1 FROM intent_saved_signals ss WHERE ss.organization_id=intent_signals.organization_id AND ss.signal_id=intent_signals.id) THEN 1 ELSE 0 END),0) AS saved_count,"
            "COALESCE(SUM(CASE WHEN status='Qualified' THEN 1 ELSE 0 END),0) AS qualified_count,"
            "COALESCE(SUM(CASE WHEN status='Dismissed' THEN 1 ELSE 0 END),0) AS dismissed_count "
            "FROM intent_signals WHERE organization_id=? AND available=1 AND " + retention,
            [org, *retention_args],
        ).fetchone()
        view_counts = {
            'all': int(vc_row['all_count'] or 0),
            'needs_review': int(vc_row['needs_review_count'] or 0),
            'high_intent': int(vc_row['high_intent_count'] or 0),
            'saved': int(vc_row['saved_count'] or 0),
            'qualified': int(vc_row['qualified_count'] or 0),
            'dismissed': int(vc_row['dismissed_count'] or 0),
        }
    elif kind=='opportunities':
        pass
    else:
        where.append("(description NOT LIKE '__pb_notif__:%' OR monitor_id IS NOT NULL)")
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
            if not signal:
                signal={'id': item['signal_id'], 'title': 'Source item unavailable', 'source': 'Public source', 'score': 0, 'category': 'Uncertain', 'excerpt': '', 'evidence': {}, 'observed_at': item.get('created_at', now()), 'opportunity_eligibility': {'eligible': False, 'reasons': ['Source evidence unavailable.']}}
            item['score']=signal['score'];item['ranking']=signal.get('ranking');item['signal']=signal;item['opportunity_eligibility']=signal.get('opportunity_eligibility')
    elif kind!='signals':
        from app.notifications.center import _decode_alert_row
        items=[]
        for r in rows:
            item=decode(r)
            if kind=='alerts' and str(item.get('description') or '').startswith('__pb_notif__:'):
                item['description']=_decode_alert_row(item)['description']
            items.append(item)
    else:
        items=[]
        retention_days=preferences(c)['source_retention_days']
        # Bounds are strict; rows contain actual records, not fabricated result cards.
        for row in rows:
            item=decode(row)
            if expired(item,retention_days):item.update(available=0,title='Source item unavailable',excerpt='',evidence={})
            items.append(item)
        ranked_signals(c,items)
        _hydrate_signal_metadata(c, org, items, actor=ctx.actor)
        for item in items:
            attach_opportunity_policy(item)
    result = {'items':items,'total':total,'page':page,'page_size':size,'has_more':(page*size)<total}
    if view_counts is not None:
        result['view_counts'] = view_counts
    if status_counts is not None:
        result['status_counts'] = status_counts
    return result

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
        if body.status=='Active' and old['status']!='Active':
            from app.billing.commercial_usage import capacity as commercial_capacity
            active_count=c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active'",(ctx.organization_id,)).fetchone()[0]
            commercial_capacity(c,ctx.organization_id,'monitors',active_count)
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
        if body.status=='Active':
            from app.billing.commercial_usage import capacity as commercial_capacity
            active_count=c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active'",(ctx.organization_id,)).fetchone()[0]
            commercial_capacity(c,ctx.organization_id,'monitors',active_count)
        key = str(uuid.uuid4())
        c.execute('INSERT INTO intent_monitors(id,organization_id,created_by,name,description,goal,configuration_json,status,request_id,fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,ctx.organization_id,ctx.actor,body.name,body.description,body.goal,encoded,body.status,str(body.request_id),fingerprint,now(),now()))
    audit(c,'MONITOR_SAVED',key)
    return get(c,'monitors',key)

def delete_monitor(c, key):
    ctx = context(c, True)
    old = get(c, 'monitors', key)
    c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id IN (SELECT signal_id FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?)', (ctx.organization_id, ctx.organization_id, key))
    c.execute('DELETE FROM intent_monitor_signals WHERE organization_id=? AND monitor_id=?', (ctx.organization_id, key))
    c.execute('DELETE FROM intent_monitors WHERE id=? AND organization_id=?', (key, ctx.organization_id))
    audit(c, 'MONITOR_DELETED', key)
    return {'id': key, 'deleted': True}

def _limits_meta(c, org: str, saved_calls: int, saved_tokens: int) -> dict:
    from datetime import datetime, timedelta, timezone
    s = get_settings()
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    next_reset = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()
    row = c.execute(
        'SELECT COALESCE(calls,0) calls, COALESCE(reserved_tokens,0) tokens FROM intent_analysis_usage WHERE organization_id=? AND day=?',
        (org, today),
    ).fetchone()
    calls_used = int(row['calls']) if row else 0
    tokens_used = int(row['tokens']) if row else 0
    platform_calls = int(s.intent_radar_ai_daily_calls)
    platform_tokens = int(s.intent_radar_ai_daily_tokens)
    plan_ai_limit = None
    plan_ai_used = None
    plan_ai_remaining = None
    try:
        from app.billing.overview import overview
        ov = overview(c)
        for item in ov.get('usage', []):
            if item.get('dimension') == 'plan_ai_calls':
                plan_ai_limit = item.get('limit')
                plan_ai_used = item.get('used')
                plan_ai_remaining = item.get('remaining')
                break
    except Exception:
        pass
    return {
        'platform_daily_call_limit': platform_calls,
        'platform_daily_token_limit': platform_tokens,
        'effective_daily_call_limit': min(platform_calls, int(saved_calls)),
        'effective_daily_token_limit': min(platform_tokens, int(saved_tokens)),
        'calls_used_today': calls_used,
        'tokens_used_today': tokens_used,
        'reset_at_utc': next_reset,
        'plan_monthly_ai_calls_limit': plan_ai_limit,
        'plan_monthly_ai_calls_used': plan_ai_used,
        'plan_monthly_ai_calls_remaining': plan_ai_remaining,
    }

def preferences(c, body=None, *, _verified_context=None):
    ctx = _verified_context or context(c, body is not None, body is not None)
    old = c.execute('SELECT * FROM intent_preferences WHERE organization_id=?',(ctx.organization_id,)).fetchone()
    if body is None:
        raw = json.loads(old['configuration_json']) if old and old['configuration_json'] else {}
        allowed_keys = set(models.Preferences.model_fields.keys()) - {'revision'}
        clean_saved = {k: v for k, v in raw.items() if k in allowed_keys}
        merged = {**models.Preferences().model_dump(), **clean_saved, 'revision': old['revision'] if old else 0}
        merged['limits_meta'] = _limits_meta(
            c,
            ctx.organization_id,
            merged.get('analysis_daily_call_limit', 3),
            merged.get('analysis_daily_token_limit', 60000),
        )
        return merged
    s = get_settings()
    if body.analysis_daily_call_limit > s.intent_radar_ai_daily_calls:
        raise HTTPException(422, f'Daily AI analysis limit cannot exceed the workspace safety ceiling ({s.intent_radar_ai_daily_calls}/day).')
    if body.analysis_daily_token_limit > s.intent_radar_ai_daily_tokens:
        raise HTTPException(422, f'Daily AI token cap cannot exceed the workspace safety ceiling ({s.intent_radar_ai_daily_tokens:,} tokens/day).')
    if body.default_icp_id:
        from app.icp.service import get as get_icp
        get_icp(c,str(body.default_icp_id))
    lock(c)
    old = c.execute('SELECT * FROM intent_preferences WHERE organization_id=?',(ctx.organization_id,)).fetchone()
    if body.revision != (old['revision'] if old else 0): raise HTTPException(409,'Preferences changed; reload first.')
    prev_doc = json.loads(old['configuration_json']) if old and old['configuration_json'] else {}
    merged_doc = body.model_dump(mode='json',exclude={'revision'})
    if 'user_notification_preferences' in prev_doc:
        merged_doc['user_notification_preferences'] = prev_doc['user_notification_preferences']
    c.execute('INSERT INTO intent_preferences(organization_id,configuration_json,updated_at) VALUES(?,?,?) ON CONFLICT(organization_id) DO UPDATE SET configuration_json=excluded.configuration_json,updated_at=excluded.updated_at,revision=intent_preferences.revision+1',(ctx.organization_id,json.dumps(merged_doc),now()))
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
    audit(c,'BOOKMARK_UPDATED',key)
    return get(c,'signals',key)

def review(c,key,body):
    org = context(c,True).organization_id; old=get(c,'signals',key)
    if not c.execute('UPDATE intent_signals SET status=?,notes=COALESCE(?,notes),revision=revision+1 WHERE id=? AND organization_id=? AND revision=?',(body.status,body.notes,key,org,body.revision)).rowcount: raise HTTPException(409,'Signal changed; reload before saving.')
    if body.status == 'Saved': bookmark(c,key)
    emit_review_change(c,key,old['status'],body.status,body.revision+1)
    audit(c,'SIGNAL_REVIEWED',key,{'status':body.status,'notes_updated':body.notes is not None})
    return get(c,'signals',key)


def emit_review_change(c,key,old,new,revision):
    if old==new:return
    from app.webhooks.service import emit
    emit(c,'radar.signal.qualified' if new=='Qualified' else 'radar.signal.status_changed',key+':review:'+str(revision),{'signal_id':key})

def bulk_action(c, body):
    """Fast batched bulk signal action avoiding N*60 per-signal query fan-out and proxy timeouts."""
    ctx = context(c, True)
    org = ctx.organization_id
    keys = list(dict.fromkeys(map(str, body.ids)))
    if not keys:
        return {'updated': 0, 'already_existed': 0, 'skipped': [], 'total_requested': 0, 'action': body.action}

    marks = ','.join('?' for _ in keys)
    rows = c.execute(
        f'SELECT * FROM intent_signals WHERE organization_id=? AND id IN ({marks})',
        [org, *keys],
    ).fetchall()
    by_id = {str(r['id']): decode(r) for r in rows}
    missing = [k for k in keys if k not in by_id]
    if missing:
        raise HTTPException(404, 'Intent Radar record not found.')

    stamp = now()
    updated = 0
    already_existed = 0
    skipped: list[dict] = []

    if body.action == 'save':
        for key in keys:
            c.execute(
                'INSERT INTO intent_saved_signals(organization_id,signal_id,saved_by,saved_at) VALUES(?,?,?,?) '
                'ON CONFLICT(organization_id,signal_id) DO NOTHING',
                (org, key, ctx.actor, stamp),
            )
            updated += 1
        audit(c, 'BOOKMARK_BULK', f'bulk:{len(keys)}', {'action': 'save', 'count': updated})
        return {'updated': updated, 'already_existed': 0, 'skipped': [], 'total_requested': len(keys), 'action': body.action}

    if body.action == 'unsave':
        c.execute(
            f'DELETE FROM intent_saved_signals WHERE organization_id=? AND signal_id IN ({marks})',
            [org, *keys],
        )
        c.execute(
            f"UPDATE intent_signals SET status='Reviewed',revision=revision+1 WHERE organization_id=? AND status='Saved' AND id IN ({marks})",
            [org, *keys],
        )
        updated = len(keys)
        audit(c, 'BOOKMARK_BULK', f'bulk:{len(keys)}', {'action': 'unsave', 'count': updated})
        return {'updated': updated, 'already_existed': 0, 'skipped': [], 'total_requested': len(keys), 'action': body.action}

    if body.action in ('review', 'qualify', 'dismiss', 'unqualify', 'needs_review'):
        status_map = {
            'review': 'Reviewed',
            'qualify': 'Qualified',
            'dismiss': 'Dismissed',
            'unqualify': 'Needs Review',
            'needs_review': 'Needs Review',
        }
        target_status = status_map[body.action]
        c.execute(
            f'UPDATE intent_signals SET status=?,revision=revision+1 WHERE organization_id=? AND id IN ({marks})',
            [target_status, org, *keys],
        )
        updated = len(keys)
        audit(c, 'SIGNAL_BULK_REVIEWED', f'bulk:{len(keys)}', {'status': target_status, 'count': updated})
        for key in keys:emit_review_change(c,key,by_id[key]['status'],target_status,by_id[key]['revision']+1)
        return {'updated': updated, 'already_existed': 0, 'skipped': [], 'total_requested': len(keys), 'action': body.action}

    if body.action == 'opportunity':
        # Hydrate all selected signals in one batch so eligibility sees buying_intent + status
        items = [by_id[k] for k in keys]
        retention_days = preferences(c)['source_retention_days']
        for item in items:
            if expired(item, retention_days):
                item.update(available=0, title='Source item unavailable', excerpt='', evidence={})
        ranked_signals(c, items)
        _hydrate_signal_metadata(c, org, items, actor=ctx.actor)
        for item in items:
            attach_opportunity_policy(item)

        existing_opps = {
            str(r['signal_id']): str(r['id'])
            for r in c.execute(
                f'SELECT signal_id, id FROM intent_opportunities WHERE organization_id=? AND signal_id IN ({marks})',
                [org, *keys],
            ).fetchall()
        }

        lock(c)
        from app.billing.usage import reserve as reserve_usage
        for item in items:
            sid = item['id']
            if sid in existing_opps:
                already_existed += 1
                continue
            elig = item.get('opportunity_eligibility') or {}
            if not elig.get('eligible'):
                reason = (elig.get('reasons') or ['Not yet qualified or missing explicit buying-intent evidence.'])[0]
                skipped.append({'id': sid, 'title': item.get('title', '')[:80], 'reason': reason})
                continue
            opp_id = str(uuid.uuid5(uuid.NAMESPACE_URL, org + ':intent-opportunity:' + sid))
            reserve_usage(c, {'opportunities': 1}, opp_id)
            inserted=c.execute(
                'INSERT INTO intent_opportunities(id,organization_id,signal_id,priority,notes,next_action,created_by,created_at,updated_at) '
                'VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,signal_id) DO NOTHING',
                (opp_id, org, sid, 'High' if item.get('score', 0) >= 75 else 'Medium', '', 'Review context', ctx.actor, stamp, stamp),
            ).rowcount
            if inserted:
                from app.webhooks.service import emit
                emit(c,'radar.opportunity.created',opp_id,{'opportunity_id':opp_id})
            c.execute(
                "UPDATE intent_signals SET status='Reviewed',revision=revision+1 WHERE id=? AND organization_id=? AND status IN ('New','Needs Review','In Review')",
                (sid, org),
            )
            updated += 1
        audit(c, 'OPPORTUNITY_BULK_CREATED', f'bulk:{len(keys)}', {'updated': updated, 'already_existed': already_existed, 'skipped': len(skipped)})
        return {
            'updated': updated,
            'already_existed': already_existed,
            'skipped': skipped,
            'total_requested': len(keys),
            'action': body.action,
        }

    raise HTTPException(422, f'Unsupported bulk action: {body.action}')

def opportunity(c,key,body=None,create_body=None):
    ctx = context(c,True); lock(c)
    if body:
        old = get(c,'opportunities',key)
        if body.status=='Qualified' and not old['opportunity_eligibility']['eligible']:raise HTTPException(409,'This record needs explicit intent and targeting evidence before it can be marked qualified. Save or review its source instead.')
        if body.assigned_to:
            from app.api.organization import membership_role
            if not membership_role(c,body.assigned_to,ctx.organization_id): raise HTTPException(404,'Assignee is not an active workspace member.')
        if not c.execute('UPDATE intent_opportunities SET status=?,priority=?,notes=?,next_action=?,assigned_to=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.status,body.priority,body.notes,body.next_action,body.assigned_to,now(),key,ctx.organization_id,body.revision)).rowcount: raise HTTPException(409,'Opportunity changed; reload before saving.')
        if old['status']!=body.status:
            from app.webhooks.service import emit
            emit(c,'radar.opportunity.status_changed',key+':'+str(body.revision+1),{'opportunity_id':key})
    else:
        signal=get(c,'signals',key)
        signal_id = key
        existing = c.execute('SELECT id FROM intent_opportunities WHERE organization_id=? AND signal_id=?', (ctx.organization_id, signal_id)).fetchone()
        if existing:
            res = get(c, 'opportunities', existing['id'])
            res['already_existed'] = True
            return res
        if not signal['opportunity_eligibility']['eligible']:raise HTTPException(409,'This discussion does not yet have sufficient intent and targeting evidence for an opportunity. Save the signal or review its evidence first.')
        key = str(uuid.uuid5(uuid.NAMESPACE_URL,ctx.organization_id + ':intent-opportunity:' + signal_id))
        from app.billing.usage import reserve
        reserve(c,{'opportunities':1},key)
        priority = create_body.priority if create_body else 'Medium'
        notes = create_body.notes if create_body else ''
        next_action = create_body.next_action if create_body else 'Review context'
        c.execute(
            'INSERT INTO intent_opportunities(id,organization_id,signal_id,priority,notes,next_action,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,signal_id) DO NOTHING',
            (key,ctx.organization_id,signal_id,priority,notes,next_action,ctx.actor,now(),now()),
        )
        # Preserve Qualified review history; only advance unreviewed statuses to Reviewed.
        from app.webhooks.service import emit
        emit(c,'radar.opportunity.created',key,{'opportunity_id':key})
        c.execute(
            "UPDATE intent_signals SET status='Reviewed',revision=revision+1 WHERE id=? AND organization_id=? AND status IN ('New','Needs Review','In Review')",
            (signal_id,ctx.organization_id),
        )
        try:
            from app.notifications import center
            center.emit(c,ctx.organization_id,category='opportunities',event_type='OPPORTUNITY_CREATED',title=f"Opportunity created: {signal['title'][:90]}",description=f"Priority: {priority}. Next action: {next_action}",priority='high' if priority=='High' else 'normal',resource_url='/intent-radar/opportunities',dedupe_key=f"opp-created:{key}",signal_id=signal_id,recipient_email=ctx.actor)
        except Exception:
            pass
    audit(c,'OPPORTUNITY_UPDATED',key)
    res = get(c,'opportunities',key)
    if not body:
        res['already_existed'] = False
    return res

def delete_opportunity(c, key):
    ctx = context(c, True)
    lock(c)
    old = get(c, 'opportunities', key)
    c.execute('DELETE FROM intent_opportunities WHERE id=? AND organization_id=?', (key, ctx.organization_id))
    audit(c, 'OPPORTUNITY_DELETED', key, {'signal_id': old['signal_id'], 'priority': old['priority']})
    return {'deleted': True, 'id': key}

def mark_alert(c,key,read):
    org=context(c,True).organization_id; get(c,'alerts',key)
    c.execute('UPDATE intent_alerts SET read_at=? WHERE id=? AND organization_id=?',(now() if read else None,key,org))
    # Acknowledge the corresponding shared notification for this actor only.
    c.execute('UPDATE workspace_notifications SET read_at=? WHERE organization_id=? AND user_id=? AND entity_id=?',(now() if read else None,org,context(c).actor,key))
    return get(c,'alerts',key)

def alert(c,event_key,title,description,monitor_id=None,signal_id=None,actor=None):
    org=context(c).organization_id; key=str(uuid.uuid5(uuid.NAMESPACE_URL,org+':intent-alert:'+event_key))
    changed=c.execute('INSERT INTO intent_alerts(id,organization_id,monitor_id,signal_id,event_key,title,description,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,event_key) DO NOTHING',(key,org,monitor_id,signal_id,event_key,title,description,now())).rowcount
    if changed and actor and monitor_id:
        c.execute('INSERT INTO workspace_notifications(id,organization_id,user_id,kind,entity_id,created_at) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),org,actor,'INTENT_RADAR',key,now()))

def overview(c,*,include_previews=True):
    org=context(c).organization_id
    postgres=getattr(c,'backend',None)=='postgres'
    days="CAST(CAST(configuration_json AS JSONB)->>'source_retention_days' AS INTEGER)" if postgres else "CAST(json_extract(configuration_json,'$.source_retention_days') AS INTEGER)"
    retention=retention_predicate(c,'policy.days')
    def array(query,columns):
        aggregate="COALESCE(json_agg(records),'[]'::json)" if postgres else "COALESCE(json_group_array(json_object("+','.join("'"+key+"',"+key for key in columns)+")),'[]')"
        return '(SELECT '+aggregate+' FROM ('+query+') records)'
    trends=array('SELECT SUBSTR(observed_at,1,10) AS day,COUNT(*) volume FROM intent_signals WHERE organization_id=? AND available=1 GROUP BY SUBSTR(observed_at,1,10) ORDER BY day DESC LIMIT 14',('day','volume'))
    jobs=array("SELECT status,COUNT(*) count FROM intelligence_jobs WHERE organization_id=? AND kind='INTENT_DISCOVER' GROUP BY status",('status','count'))
    stamp=now()
    result=dict(c.execute("""WITH policy AS (SELECT COALESCE((SELECT """+days+""" FROM intent_preferences WHERE organization_id=?),30) days) SELECT
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND status='New' AND available=1 AND """+retention+""" ) new_signals,
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND status='Reviewed') reviewed_signals,
        (SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND """+rank_expression()+""">=85 AND available=1 AND """+retention+""") high_relevance,
        (SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active') active_monitors,
        (SELECT COUNT(*) FROM intent_opportunities WHERE organization_id=? AND status NOT IN ('Archived','Dismissed')) saved_opportunities,
        (SELECT COUNT(*) FROM intent_alerts WHERE organization_id=? AND read_at IS NULL AND (description NOT LIKE '__pb_notif__:%' OR monitor_id IS NOT NULL OR signal_id IS NOT NULL)) unread_alerts,
        """+trends+' trends,'+jobs+" jobs,(SELECT MAX(last_tick_at) FROM intent_worker_health WHERE state='READY') heartbeat FROM policy",
        (org,org,stamp,org,org,stamp,org,org,org,org,org)).fetchone())
    for key in ('trends','jobs'):
        if isinstance(result[key],str):result[key]=json.loads(result[key])
    grouped=result.pop('jobs');heartbeat=result.pop('heartbeat')
    from datetime import timedelta
    result.update(operations={'jobs_by_status':grouped,'backlog':sum(r['count'] for r in grouped if r['status']=='QUEUED'),'scheduler_heartbeat_at':heartbeat,'scheduler_heartbeat_fresh':bool(heartbeat and heartbeat>(datetime.now(timezone.utc)-timedelta(seconds=180)).isoformat()),'worker_status_basis':'Running job records indicate leased work; scheduler heartbeat is not Cloud Run worker health.','sources':[]},as_of=stamp,preview_state='included' if include_previews else 'not requested')
    if include_previews:
        from app.intent_radar.overview import previews
        result.update(previews(c,org))
    return result

def remove_source(c,key):
    """Withdraw public content while preserving customer annotations and history."""
    ctx=context(c,True,True);signal=get(c,'signals',key);lock(c)
    c.execute("UPDATE intent_signals SET available=0,title='Source item unavailable',excerpt='',evidence_json=?,revision=revision+1 WHERE id=? AND organization_id=?",(json.dumps({'removed_by_policy':True}),key,ctx.organization_id))
    c.execute('DELETE FROM intent_analyses WHERE signal_id=? AND organization_id=?',(key,ctx.organization_id))
    c.execute('DELETE FROM intent_rankings WHERE signal_id=? AND organization_id=?',(key,ctx.organization_id))
    from app.notifications import center
    center.redact_signal_alerts(c, ctx.organization_id, key)
    for row in c.execute('SELECT fingerprint,result_json FROM intent_source_cache WHERE organization_id=? LIMIT 1000',(ctx.organization_id,)).fetchall():
        data=json.loads(row['result_json']);items=data if isinstance(data,list) else data.get('items',[])
        remaining=[x for x in items if x.get('source_url')!=signal['source_url']]
        if len(remaining)!=len(items):
            if isinstance(data,list):data=remaining
            else:data['items']=remaining
            c.execute('UPDATE intent_source_cache SET result_json=? WHERE organization_id=? AND fingerprint=?',(json.dumps(data),ctx.organization_id,row['fingerprint']))
    audit(c,'SOURCE_CONTENT_WITHDRAWN',key)
    return get(c,'signals',key)
