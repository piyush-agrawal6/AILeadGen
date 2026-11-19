"""Snapshot equivalence, bounded preview sizes, retention and tenant isolation."""
import json,uuid
from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned
from test_radar_read_budgets import Counted
from app.intent_radar import service,models,intelligence
from app.platform.context import workspace_scope


def snapshot_contract(c,org,other,actor):
    stamp=datetime.now(timezone.utc).isoformat();ids=[]
    with workspace_scope(c,actor,org):
        monitor=service.save_monitor(c,models.Monitor(name='Snapshot monitor',configuration=models.Search(keywords=['website'])))
        for i in range(8):
            key=str(uuid.uuid4());ids.append(key)
            c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,org,'Hacker News','snapshot-'+str(i),'https://news.ycombinator.com/item?id='+str(100+i),'Owned discussion '+str(i),'Looking for a website tool.','2026-11-'+str(i+1).zfill(2)+'T00:00:00+00:00',stamp if i!=7 else '2000-01-01T00:00:00+00:00','Tool recommendation',80,json.dumps({'matched_keywords':['website'],'provenance':{'retention_days':1}})))
        for i in (2,3):c.execute('INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?)',(org,monitor['id'],ids[i],stamp))
        service.bookmark(c,ids[2]);intelligence.feedback(c,ids[2],models.Feedback(label='Relevant'))
        for i in (0,2,7):
            c.execute('INSERT INTO intent_opportunities(id,organization_id,signal_id,created_by,created_at,updated_at,notes) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),org,ids[i],actor,stamp,stamp,'Historical review '+str(i)))
        service.alert(c,'snapshot','An owned alert','Original source context',monitor['id'],ids[2]);c.commit()
        q=Counted(c);result=service.overview(q)
        assert len(q.statements)==3
        assert len(result['recent_signals'])==5 and all(item['id']!=ids[7] for item in result['recent_signals'])
        for kind,key in [('signals','recent_signals'),('monitors','monitors'),('opportunities','opportunities'),('alerts','alerts')]:
            expected = service.listing(c,kind,size=5)['items']
            if kind == 'signals':
                assert [{k: item[k] for k in item if k not in ('opportunity_id','opportunity_status','discovery_id','discovery_title','feedback_label','buying_intent','buying_intent_basis','icp_fit','icp_fit_detail','has_analysis','latest_analysis_at','latest_analysis_summary','latest_analysis_mode')} for item in expected] == result[key]
            else:
                assert result[key]==expected
        signal=next(s for s in result['recent_signals'] if s['id']==ids[2])
        assert signal['score']==85 and signal['saved'] and signal['monitors']==[{'id':monitor['id'],'name':monitor['name']}]
        expired=next(o['signal'] for o in result['opportunities'] if o['signal_id']==ids[7])
        assert expired['title']=='Source item unavailable' and expired['excerpt']=='' and expired['score']==0
        from app.intent_radar.overview import previews
        with pytest.raises(HTTPException):previews(c,other)
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,actor,other):
        empty=service.overview(c)
        assert all(empty[k]==[] for k in ('recent_signals','monitors','opportunities','alerts'))
    with pytest.raises(HTTPException):service.overview(c)


def test_overview_snapshot_matches_current_evidence_and_excludes_foreign_workspace(radar):
    c,_,org,other=radar
    # The controlled owner is explicitly enrolled in the second test workspace.
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,'OWNER','ACTIVE',?,?)",(str(uuid.uuid4()),other,'controlled@example.test','2026-01-01','2026-01-01'));c.commit()
    snapshot_contract(c,org,other,'controlled@example.test')
