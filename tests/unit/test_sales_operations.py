import uuid,sqlite3
import pytest
from fastapi import HTTPException
from test_people import owned,seed
from app.platform.context import workspace_scope
from app.sales import collections,tasks
from app.people import service as people
from app.database import migrations


def test_lists_keep_company_contact_history_and_archive_instead_of_deleting(owned):
 c,path,org,other=owned
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);body=collections.Named(name='Controlled company list',description='Reviewed companies');first=collections.save(c,body)
  assert collections.save(c,body)['id']==first['id'];key=first['id']
  assert collections.change_members(c,key,[b.id])['updated']==1
  person=people.save(c,b.id,people.Person(name='Avery Example'));people.membership(c,person['id'],key)
  data=collections.detail(c,key);assert data['company_count']==1 and data['contact_count']==1 and data['companies'][0]['id']==b.id
  assert collections.listing(c)['items'][0]['member_count']==1
  collections.save(c,collections.Named(name='Renamed list',revision=data['revision']),key)
  with pytest.raises(HTTPException):collections.save(c,collections.Named(name='Stale',revision=data['revision']),key)
  archive=collections.archive(c,key,collections.get(c,key)['revision']);assert archive['archived_at']
  assert collections.listing(c)['total']==0 and collections.listing(c,archived=True)['total']==1
  assert collections.detail(c,key)['company_count']==1 and people.get(c,person['id'])['lists'][0]['archived_at']
  with pytest.raises(HTTPException):collections.change_members(c,key,[b.id])
  with pytest.raises(HTTPException):people.membership(c,person['id'],key)
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  assert collections.listing(c)['total']==0
  with pytest.raises(HTTPException):collections.detail(c,key)
  with pytest.raises(HTTPException):collections.change_members(c,key,[b.id])
 with pytest.raises(HTTPException):collections.listing(c)


def test_sales_tasks_are_owned_revisioned_and_cannot_bypass_suppression(owned):
 from app.database.prospects import ProspectRepository
 c,path,org,other=owned
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);person=people.save(c,b.id,people.Person(name='Avery Example'));body=tasks.Task(business_id=b.id,title='Review company evidence',task_type='RESEARCH',due_at='2026-12-01T09:00:00+00:00',contact_id=person['id'],assigned_to='controlled@example.test')
  task=tasks.create(c,body);assert tasks.create(c,body)['id']==task['id'];assert tasks.listing(c)['items'][0]['company_name']==b.name
  assert tasks.update(c,task['id'],1,'COMPLETED')['status']=='COMPLETED'
  with pytest.raises(HTTPException):tasks.update(c,task['id'],1,'OPEN')
  assert tasks.update(c,task['id'],2,'OPEN')['revision']==3
  ProspectRepository(c).workflow(person['prospect_id'],'controlled@example.test',lead_status='DO_NOT_CONTACT',organization=org)
  assert tasks.create(c,body.model_copy(update={'request_id':uuid.uuid4(),'title':'Internal DNC review'}))['status']=='OPEN'
  with pytest.raises(HTTPException):tasks.create(c,body.model_copy(update={'request_id':uuid.uuid4(),'task_type':'FOLLOW_UP'}))
  with pytest.raises(HTTPException):tasks.create(c,body.model_copy(update={'assigned_to':'foreign@example.test','request_id':uuid.uuid4()}))
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  assert tasks.listing(c)['total']==0
  with pytest.raises(HTTPException):tasks.get(c,task['id'])
  with pytest.raises(HTTPException):tasks.update(c,task['id'],3,'COMPLETED')
 c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(org,));c.commit()
 with workspace_scope(c,'controlled@example.test',org):
  with pytest.raises(HTTPException):tasks.create(c,body)
  with pytest.raises(HTTPException):tasks.update(c,task['id'],3,'COMPLETED')


def test_sales_operations_upgrade_is_additive_and_restores_snapshot(tmp_path,monkeypatch):
 c=sqlite3.connect(tmp_path/'source.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');latest=migrations.MIGRATIONS;monkeypatch.setattr(migrations,'MIGRATIONS',latest[:32]);migrations.run_migrations(c);c.commit()
 tables=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_migrations'").fetchall()];old={t:[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()] for t in tables};backup=sqlite3.connect(tmp_path/'snapshot.db');c.backup(backup)
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:33]);assert migrations.run_migrations(c)==1 and migrations.run_migrations(c)==0
 for table,rows in old.items():
  after=[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()]
  assert [{key:row[key] for key in rows[0]} for row in after]==rows if rows else not after
 assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
 restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored);assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==32;assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 c.close();backup.close();restored.close()


def test_sales_lists_tasks_http_and_safe_export_are_connected(tmp_path,monkeypatch):
 from fastapi.testclient import TestClient
 from app.api.server import app
 from app.config.settings import get_settings
 from app.database.connection import db_session
 from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as org
 from app.database.models import PipelineRun,Business
 from app.database.repositories import PipelineRunRepository,BusinessRepository
 from app.database.prospects import ProspectRepository
 from app.api.organization import create_organization
 settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'sales-api.db'));monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,foreign@example.test');monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
 with TestClient(app) as http:
  with db_session() as c:
   foreign=create_organization(c,'foreign@example.test','Other company')['organization_id']
   c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(foreign,))
   with workspace_scope(c,'owner@example.test',org):
    run=PipelineRun(market='London',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=org);b=Business(name='=Controlled company',normalized_name='controlled company',vertical='dentists',run_id=run.id);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=org)
  response=http.post('/api/sales/lists',json={'name':'Controlled list'});assert response.status_code==201;key=response.json()['id']
  assert http.post('/api/sales/lists/'+key+'/companies',json={'business_ids':[b.id]}).status_code==200
  assert http.get('/api/sales/lists?page=1').json()['items'][0]['member_count']==1
  export=http.get('/api/sales/lists/'+key+'/export.csv');assert export.status_code==200 and "'=Controlled company" in export.text
  assert export.headers['cache-control']=='private, no-store'
  assert http.get('/api/sales/lists/'+key,headers={'x-le-user':'foreign@example.test'}).status_code==404
  assert http.get('/api/sales/lists/'+key+'/export.csv',headers={'x-le-user':'foreign@example.test'}).status_code==404
  task=http.post('/api/sales/tasks',json={'business_id':b.id,'title':'Review controlled source','task_type':'REVIEW','due_at':'2026-12-01T09:00:00Z'});assert task.status_code==201,task.text
  tid=task.json()['id'];assert http.get('/api/sales/tasks').json()['items'][0]['id']==tid
  assert http.patch('/api/sales/tasks/'+tid,json={'revision':1,'status':'COMPLETED'}).json()['status']=='COMPLETED'
  assert http.get('/api/sales/tasks/'+tid,headers={'x-le-user':'foreign@example.test'}).status_code==404
  assert http.delete('/api/sales/lists/'+key).json()['history_retained']
  assert http.get('/api/sales/lists').json()==[]
  assert http.get('/api/sales/lists/'+key).json()['company_count']==1
