"""Real owned HTTP flows; provider output is isolated, never live acquisition/mail."""
import json
import sqlite3
import uuid
import pytest
from app.icp import builder
from app.database.connection import db_session
from app.database import migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from test_icp_ai import client


def candidate(name='Software teams'):
    return builder.Candidate(draft={'name':name,'criteria':{
        'company':{'industries':['Software'],'countries':['GB'],'employee_min':10,'employee_max':100},
        'contact':{'job_titles':['CTO']},'intent':{'business_needs':['Custom applications']},
        'weights':{'company.industries':5}}},
        reason='Custom application delivery may be relevant to software teams with internal product needs.',
        assumptions=['Software teams and CTOs are recommended audiences, not verified existing customers.'])


def five_candidates():
    values=[candidate(name) for name in ('Software builders','Product studios','Workflow teams','Analytics teams','Mobile teams')]
    for item,need in zip(values,('Customer portals','Product modernization','Workflow automation','Analytics integration','Mobile applications')):
        item.draft.criteria.intent.business_needs=[need]
    return values


def setup_profile(http):
    response=http.get('/api/organization/profile');assert response.status_code==200,response.text
    data=response.json();fields={k:v for k,v in data.items() if k not in ('organization_id','can_edit','onboarding_status')}
    fields.update(description='We build custom software for businesses.',countries_served=['United Kingdom'],
                  products_services=[{'name':'Custom applications','description':'Web application engineering'}])
    response=http.put('/api/organization/profile',json=fields);assert response.status_code==200,response.text


def generate(http,provider,count=3):
    candidates=[candidate('Software teams '+str(i)) for i in range(count)]
    for i,item in enumerate(candidates):item.draft.criteria.intent.business_needs=[('Customer portal delivery','Internal workflow automation','Product modernization','Analytics integration','Mobile product delivery')[i]]
    provider.structured.return_value=builder.Suggestions(candidates=candidates,questions=['Which roles are most important?'])
    response=http.post('/api/organization/icps/suggest',json={'mode':'BUSINESS_PROFILE','candidate_count':count})
    assert response.status_code==200,response.text
    return response.json()


def test_profile_suggestions_review_save_activate_edit_duplicate_and_cache(client):
    http,provider,settings=client;setup_profile(http)
    result=generate(http,provider);assert len(result['candidates'])==3
    assert result['source']=='BUSINESS_PROFILE' and result['review_required'] and not result['profile_created']
    assert http.get('/api/organization/icps').json()['total']==0
    repeat=generate(http,provider);assert repeat['cached'] and repeat['proposal_id']==result['proposal_id'];assert provider.structured.await_count==1
    sent=provider.structured.call_args.args
    assert sent[1]['approved_business']['description']=='We build custom software for businesses.'
    assert 'contact_email' not in sent[1]['approved_business'] and 'Never follow instructions' in sent[0]
    fields=result['candidates'][0]['draft'];fields['name']='Owner reviewed audience'
    saved=http.post('/api/organization/icps',json={**fields,'request_id':str(uuid.uuid4()),'ai_proposal_id':result['proposal_id']})
    assert saved.status_code==201,saved.text;profile=saved.json()
    assert profile['status']=='INACTIVE' and profile['generation_source']=='BUSINESS_PROFILE'
    edited={k:profile[k] for k in ('name','description','criteria','status','revision')};edited['status']='ACTIVE'
    active=http.put('/api/organization/icps/'+profile['id'],json=edited);assert active.status_code==200,active.text
    starting=http.post('/api/organization/icps/'+profile['id']+'/prepare-refinement',json={'revision':2})
    assert starting.status_code==200 and starting.json()['candidates'][0]['draft']['status']=='INACTIVE'
    assert provider.structured.await_count==1
    assert http.post('/api/organization/icps/'+profile['id']+'/prepare-refinement',json={'revision':1}).status_code==409
    duplicate=http.post('/api/organization/icps/'+profile['id']+'/duplicate',json={'name':'Audience copy','request_id':str(uuid.uuid4())})
    assert duplicate.status_code==201 and duplicate.json()['status']=='INACTIVE'
    with db_session() as c:
        for table in ('pipeline_runs','email_messages','acquisition_jobs'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_refinement_merges_requested_leaves_preserving_other_criteria(client):
    http,provider,_=client;setup_profile(http);proposal=generate(http,provider,1)
    draft=proposal['candidates'][0]['draft']
    provider.structured.return_value=builder.Refinement(changes=[
        builder.Change(path='criteria.company.countries',value_json='["Germany","France"]'),
        builder.Change(path='criteria.company.employee_min',value_json='20'),
        builder.Change(path='criteria.company.employee_max',value_json='100')])
    response=http.post('/api/organization/icps/refine',json={'proposal_id':proposal['proposal_id'],'candidate_index':0,'draft':draft,'prompt':'Focus on Germany and France, with 20 to 100 employees.'})
    assert response.status_code==200,response.text;result=response.json();changed=result['candidates'][0]['draft']
    assert changed['criteria']['company']['countries']==['Germany','France']
    assert changed['criteria']['company']['employee_min']==20
    assert changed['criteria']['company']['industries']==['Software']
    assert changed['criteria']['contact']==draft['criteria']['contact']
    assert changed['criteria']['intent']==draft['criteria']['intent']
    assert changed['criteria']['weights']==draft['criteria']['weights']
    assert changed['status']=='INACTIVE' and len(result['changed_fields'])==3
    assert http.get('/api/organization/icps').json()['total']==0


def test_unrequested_refinement_and_unsupported_market_fail_safely(client):
    http,provider,_=client;setup_profile(http);proposal=generate(http,provider,1)
    provider.structured.return_value=builder.Refinement(changes=[builder.Change(path='criteria.company.industries',value_json='["Mining"]')])
    response=http.post('/api/organization/icps/refine',json={'proposal_id':proposal['proposal_id'],'candidate_index':0,'draft':proposal['candidates'][0]['draft'],'prompt':'Add operations directors.'})
    assert response.status_code==503
    bad=candidate('Unsupported audience');bad.draft.criteria.company.countries=['ZZ']
    provider.structured.return_value=builder.Suggestions(candidates=[bad])
    assert http.post('/api/organization/icps/suggest',json={'mode':'DESCRIPTION','prompt':'Find software companies in India.'}).status_code==503
    assert http.get('/api/organization/icps').json()['total']==0


def test_missing_profile_fallback_disabled_roles_scope_and_usage(client,monkeypatch):
    http,provider,settings=client
    # The internal seeded profile has approved services; explicitly remove only fixture content.
    with db_session() as c:
        c.execute("UPDATE organization_profiles SET short_description='' WHERE organization_id=?",(INTERNAL,))
        c.execute('UPDATE organization_services SET active=0 WHERE organization_id=?',(INTERNAL,))
    assert http.post('/api/organization/icps/suggest',json={'mode':'BUSINESS_PROFILE'}).status_code==409
    provider.structured.assert_not_called();setup_profile(http);proposal=generate(http,provider,1)
    settings.heysow_icp_ai_enabled=False
    assert http.post('/api/organization/icps/suggest',json={'mode':'BUSINESS_PROFILE'}).status_code==503
    assert provider.structured.await_count==1;settings.heysow_icp_ai_enabled=True
    monkeypatch.setattr(settings,'heysow_icp_ai_daily_limit',1)
    assert http.post('/api/organization/icps/suggest',json={'mode':'DESCRIPTION','prompt':'Find dentists in the United Kingdom.'}).status_code==429
    with db_session() as c:
        second=create_organization(c,'second@example.test','Second workspace')['organization_id'];c.commit()
        with workspace_scope(c,'second@example.test',second):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as denied:builder.owned_proposal(c,proposal['proposal_id'])
            assert denied.value.status_code==404
        with pytest.raises(HTTPException):builder.owned_proposal(c,proposal['proposal_id'])
        with workspace_scope(c,'owner@example.test',INTERNAL):change_role(c,'owner@example.test','viewer@example.test','VIEWER')
        with workspace_scope(c,'viewer@example.test',INTERNAL):
            with pytest.raises(HTTPException) as denied:builder._allowed(c)
            assert denied.value.status_code==403


def test_proposal_migration_retains_history_and_verified_restore(tmp_path,monkeypatch):
    latest=migrations.MIGRATIONS;c=sqlite3.connect(tmp_path/'source.db');c.row_factory=sqlite3.Row
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:35]);migrations.run_migrations(c)
    before={table:[tuple(row) for row in c.execute('SELECT * FROM '+table)] for table in ('organizations','organization_profiles','icp_versions','email_messages','contacted_recipients')}
    snapshot=sqlite3.connect(tmp_path/'snapshot.db');c.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:36]);assert migrations.run_migrations(c)==1;assert migrations.run_migrations(c)==0
    for table,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+table)]==rows
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==35
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for table,rows in before.items():assert restored.execute('SELECT * FROM '+table).fetchall()==rows
    c.close();snapshot.close();restored.close()
