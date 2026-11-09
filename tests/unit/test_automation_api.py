from test_phase4_api import client4
from app.database.connection import db_session
from app.automation.service import reconcile


def test_master_views_targets_market_pages_and_bulk(client4):
    client,ids=client4
    with db_session() as c:reconcile(c)
    r=client.get('/api/automation/master-leads?tab=today&page_size=1').json()
    assert r['total']==2 and len(r['items'])==1 and r['counts']['all']==2
    pid=r['items'][0]['prospect_id']
    assert client.get('/api/automation/master-leads?email_availability=no').json()['total']==0
    p=client.get('/api/automation/markets/page?page=2&page_size=25').json()
    assert p['total']==304 and len(p['items'])==25
    market=p['items'][0]
    body={key:market[key] for key in ('country','city','vertical','priority','cooldown_days')};body.update(region='',enabled=False)
    assert client.put('/api/automation/markets/'+market['id'],json=body).status_code==200
    settings={'daily_qualified_lead_target':3,'daily_email_target':2,'max_hour':2,'max_day':5,'followup_days':3,'automation_timezone':'Asia/Kolkata'}
    assert client.put('/api/automation/targets',json=settings).status_code==200
    assert client.get('/api/automation/targets').json()['daily_qualified_lead_target']==3
    assert client.put('/api/automation/targets',json={**settings,'max_hour':51}).status_code==422
    r=client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'sales','sales_state':'PROPOSAL'})
    assert r.status_code==200
    assert client.get('/api/automation/master-leads?tab=proposal').json()['total']==1
    r=client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'export'})
    assert r.status_code==200 and 'Company,City,Country' in r.text and 'Hotel' in r.text
    assert client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'dnc'}).status_code==200
    assert client.get('/api/automation/master-leads?tab=dnc').json()['total']==1
    assert client.get('/api/automation/email-history').status_code==200


def test_bulk_list_assignment_followup_and_settings_preservation(client4):
    client,_=client4
    with db_session() as c:reconcile(c)
    pid=client.get('/api/automation/master-leads').json()['items'][0]['prospect_id']
    list_id=client.post('/api/sales/lists',json={'name':'Controlled list'}).json()['id']
    assert client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'list','list_id':list_id}).status_code==200
    assert client.get('/api/automation/master-leads?list_id='+list_id).json()['total']==1
    assert client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'assign','assigned_to':None}).status_code==200
    assert client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'assign','assigned_to':'unapproved@example.com'}).status_code==422
    assert client.post('/api/automation/master-leads/bulk',json={'prospect_ids':[pid],'action':'followup','due_at':'2026-11-10T10:00:00+00:00'}).status_code==200
    assert client.get('/api/automation/master-leads').json()['items'][0].get('next_followup') or client.get('/api/automation/master-leads').json()['items'][1].get('next_followup')
    settings=client.get('/api/settings').json()
    client.put('/api/automation/targets',json={'daily_qualified_lead_target':4,'daily_email_target':2,'max_hour':2,'max_day':5,'followup_days':3,'automation_timezone':'Asia/Kolkata'})
    assert client.put('/api/settings',json=settings).status_code==200
    assert client.get('/api/automation/targets').json()['daily_qualified_lead_target']==4
