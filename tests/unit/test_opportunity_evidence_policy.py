"""Request evidence, targeting and exclusions are separate from scores."""
import uuid
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result
from app.intent_radar.opportunity_policy import assess
from app.intent_radar import service,models
from app.platform.context import workspace_scope
from app.database.prospects import now

@pytest.mark.parametrize('text',['What are you working on?','I am not looking for a vendor.','Looking for feedback on our new software platform.','A tutorial comparing software tools','We are hiring software engineers.','We are not buying any new software.'])
def test_general_and_negative_discussions_are_not_automatically_opportunities(text):
    signal={'title':text,'excerpt':'','available':1,'score':100,'evidence':{'matched_keywords':['software']}}
    assert not assess(signal)['eligible']

def test_request_and_customer_target_alignment_are_required_without_score_inflation():
    signal={'title':'Looking for a software development partner','excerpt':'We are comparing providers for our next project.','available':1,'score':45,'evidence':{'matched_keywords':['software']}}
    result=assess(signal)
    assert result['eligible'] and result['intent_quote'] in signal['title']+'\n'+signal['excerpt']
    assert signal['score']==45
    assert not assess({**signal,'evidence':{}})['eligible']
    assert not assess({**signal,'available':0})['eligible']
    assert assess({**signal,'ranking':{'scoring':{'penalties':['Positive feedback adjusted relevance'],'dimensions':{'contradictory_evidence':0}}}})['eligible']

def test_invalid_promotion_is_blocked_and_historical_record_remains_reviewable(radar,monkeypatch):
    from unittest.mock import AsyncMock
    from app.intent_radar import providers
    c,path,org,other=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']))
        signal=c.execute('SELECT id FROM intent_signals WHERE organization_id=?',(org,)).fetchone()[0]
        c.execute("UPDATE intent_signals SET title='What are you working on?',excerpt='General website discussion',category='General discussion',evidence_json='{}' WHERE organization_id=? AND id=?",(org,signal))
        with pytest.raises(HTTPException) as error:service.opportunity(c,signal)
        assert error.value.status_code==409
        assert c.execute('SELECT COUNT(*) FROM intent_opportunities').fetchone()[0]==0
        key=str(uuid.uuid4());stamp=now()
        c.execute('INSERT INTO intent_opportunities(id,organization_id,signal_id,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?)',(key,org,signal,'controlled@example.test',stamp,stamp))
        legacy=service.get(c,'opportunities',key)
        assert not legacy['opportunity_eligibility']['eligible']
        with pytest.raises(HTTPException):service.opportunity(c,key,models.OpportunityUpdate(revision=1,status='Qualified',priority='Medium'))
        assert c.execute('SELECT status FROM intent_opportunities WHERE id=?',(key,)).fetchone()[0]=='New'
        updated=service.opportunity(c,key,models.OpportunityUpdate(revision=1,status='Dismissed',priority='Low'))
        assert updated['status']=='Dismissed'
