"""One bounded preview snapshot; caller has just verified this workspace.

No permission result is cached. Every query is restricted to the organization
resolved by the enclosing public overview operation, on its same transaction.
"""
import json
from fastapi import HTTPException
from app.database.prospects import now

SIGNAL_COLUMNS='id organization_id source source_record_id source_url title excerpt observed_at retrieved_at category score evidence_json status notes available revision'.split()
MONITOR_COLUMNS='id organization_id created_by name description goal configuration_json status request_id fingerprint revision last_checked last_job_id created_at updated_at schedule_json next_run_at'.split()
OPPORTUNITY_COLUMNS='id organization_id signal_id status priority notes next_action assigned_to revision created_by created_at updated_at'.split()
ALERT_COLUMNS='id organization_id monitor_id signal_id event_key title description read_at created_at'.split()


def previews(c,organization_id):
    from app.platform.context import organization
    from app.intent_radar.service import decode,expired,rank_expression,retention_predicate,attach_opportunity_policy
    org=organization(organization_id)
    postgres=getattr(c,'backend',None)=='postgres'
    def array(query,columns):
        aggregate="COALESCE(json_agg(records),'[]'::json)" if postgres else "COALESCE(json_group_array(json_object("+','.join("'"+key+"',"+key for key in columns)+")),'[]')"
        return '(SELECT '+aggregate+' FROM ('+query+') records)'
    days="CAST(CAST(configuration_json AS JSONB)->>'source_retention_days' AS INTEGER)" if postgres else "CAST(json_extract(configuration_json,'$.source_retention_days') AS INTEGER)"
    explanation="(SELECT r.explanation_json FROM intent_rankings r WHERE r.organization_id=s.organization_id AND r.signal_id=s.id AND (r.icp_id IS NULL OR EXISTS(SELECT 1 FROM ideal_customer_profiles i WHERE i.organization_id=r.organization_id AND i.id=r.icp_id AND i.revision=r.icp_revision)) AND NOT EXISTS(SELECT 1 FROM organization_profiles p WHERE p.organization_id=r.organization_id AND p.updated_at>r.updated_at))"
    result=dict(c.execute('''WITH policy AS (SELECT COALESCE((SELECT '''+days+''' FROM intent_preferences WHERE organization_id=?),30) days),
        recent AS (SELECT s.id FROM intent_signals s,policy WHERE s.organization_id=? AND s.available=1 AND '''+retention_predicate(c,'policy.days','s')+''' ORDER BY s.observed_at DESC,s.id LIMIT 5),
        opportunities AS (SELECT * FROM intent_opportunities WHERE organization_id=? ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,(SELECT '''+rank_expression('s')+''' FROM intent_signals s WHERE s.id=intent_opportunities.signal_id AND s.organization_id=intent_opportunities.organization_id) DESC,created_at DESC,id LIMIT 5),
        needed AS (SELECT id FROM recent UNION SELECT signal_id FROM opportunities)
        SELECT (SELECT days FROM policy) retention_days,
        '''+array('SELECT * FROM recent',('id',))+''' recent,
        '''+array('SELECT * FROM opportunities',OPPORTUNITY_COLUMNS)+''' opportunities,
        '''+array('SELECT s.*,'+rank_expression('s')+' adjusted_score,'+explanation+' rank_explanation FROM intent_signals s WHERE s.organization_id=? AND s.id IN (SELECT id FROM needed)',[*SIGNAL_COLUMNS,'adjusted_score','rank_explanation'])+''' signals,
        '''+array('SELECT * FROM intent_monitors WHERE organization_id=? ORDER BY created_at DESC,id LIMIT 5',MONITOR_COLUMNS)+''' monitors,
        '''+array("SELECT * FROM intent_alerts WHERE organization_id=? AND (description NOT LIKE '__pb_notif__:%' OR monitor_id IS NOT NULL OR signal_id IS NOT NULL) ORDER BY created_at DESC,id LIMIT 5",ALERT_COLUMNS)+''' alerts,
        '''+array('SELECT x.signal_id,m.id,m.name FROM intent_monitor_signals x JOIN intent_monitors m ON m.id=x.monitor_id AND m.organization_id=x.organization_id WHERE x.organization_id=? AND x.signal_id IN (SELECT id FROM needed)',('signal_id','id','name'))+''' links,
        '''+array('SELECT signal_id FROM intent_saved_signals WHERE organization_id=? AND signal_id IN (SELECT id FROM needed)',('signal_id',))+''' saved''',
        (org,org,now(),org,org,org,org,org,org)).fetchone())
    for key in ('recent','opportunities','signals','monitors','alerts','links'):
        if isinstance(result[key],str):result[key]=json.loads(result[key])
    # The final array is named separately so drivers never infer a SQL expression
    # as a mapping key. (All values are driver-bound; identifiers are fixed.)
    saved_raw=result.pop('saved')
    saved={row['signal_id'] for row in (json.loads(saved_raw) if isinstance(saved_raw,str) else saved_raw)}
    links={}
    for link in result['links']:links.setdefault(link['signal_id'],[]).append({'id':link['id'],'name':link['name']})
    signals={}
    for row in result['signals']:
        item=decode(row);score=item.pop('adjusted_score');explanation=item.pop('rank_explanation')
        item['keyword_score']=item['score']
        if not item['available'] or expired(item,result['retention_days']):
            item.update(available=0,title='Source item unavailable',excerpt='',evidence={},score=0,ranking={'basis':'Public source evidence is unavailable; no current relevance claim.'})
        else:
            item['score']=score;item['ranking']=json.loads(explanation) if isinstance(explanation,str) and explanation else explanation or {'version':'DETERMINISTIC_V3','basis':'Keyword evidence + bounded active workspace feedback'}
        attach_opportunity_policy(item);signals[item['id']]=item
    recent=[]
    for row in result['recent']:
        if row['id'] not in signals:raise HTTPException(404,'Signal not found in this workspace.')
        item=dict(signals[row['id']]);item['monitors']=links.get(item['id'],[]);item['saved']=item['id'] in saved;recent.append(item)
    opportunities=[]
    for row in result['opportunities']:
        item=decode(row);signal=signals.get(item['signal_id'])
        if signal is None:raise HTTPException(404,'Signal not found in this workspace.')
        item.update(score=signal['score'],ranking=signal['ranking'],signal=signal,opportunity_eligibility=signal['opportunity_eligibility']);opportunities.append(item)
    from app.notifications.center import _decode_alert_row
    decoded_alerts = []
    for r in result['alerts']:
        item = decode(r)
        if str(item.get('description') or '').startswith('__pb_notif__:'):
            dec = _decode_alert_row(item)
            item['description'] = dec['description']
        decoded_alerts.append(item)
    return {'recent_signals':recent,'monitors':[decode(r) for r in result['monitors']],'opportunities':opportunities,'alerts':decoded_alerts}
