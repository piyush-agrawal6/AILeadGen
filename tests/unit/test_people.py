import uuid,asyncio
import pytest
from fastapi import HTTPException
from test_prospecting_only import owned,batch,company
from app.database.repositories import BusinessRepository
from app.database.prospects import ProspectRepository,now
from app.platform.context import workspace_scope
from app.people import service

def seed(c,org):
 cid,run=batch(c,org);b=company(run);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,cid,organization=org);c.commit();return b

def test_contacts_are_owned_separate_multiple_people_with_notes_lists_and_revisions(owned):
 c,path,org,other=owned
 with workspace_scope(c,'controlled@example.test',org):
  b=seed(c,org);body=service.Person(name='Avery Example',role='CTO',department='Engineering',work_email='avery@controlled.example',source_url='https://controlled.example/team',evidence='Avery Example, CTO')
  a=service.save(c,b.id,body);second=service.save(c,b.id,service.Person(name='Morgan Example',role='Founder'))
  assert a['id']!=second['id'] and service.listing(c,business_id=b.id)['total']==2
  assert a['recipient_delivery_verified'] is False and a['evidence']['employment_verified'] is False
  assert service.save(c,b.id,body)['id']==a['id']
  assert service.save(c,b.id,body.model_copy(update={'request_id':uuid.uuid4()}))['id']==a['id']
  assert service.listing(c,job_role='CTO',page_size=1)['items'][0]['role']=='CTO'
  updated=service.save(c,b.id,body.model_copy(update={'revision':1,'role':'Engineering lead'}),a['id']);assert updated['revision']==2
  with pytest.raises(HTTPException):service.save(c,b.id,body.model_copy(update={'revision':1}),a['id'])
  assert service.note(c,a['id'],'Owner reviewed this public source')['notes'][0]['body'].startswith('Owner reviewed')
  lid=str(uuid.uuid4());c.execute('INSERT INTO lead_lists(id,name,created_by,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?)',(lid,'Engineering','controlled@example.test',now(),now(),org))
  assert service.membership(c,a['id'],lid)['lists'][0]['id']==lid
  assert service.membership(c,a['id'],lid,False)['lists']==[]
  assert service.archive(c,a['id'],2)['archived_at'] and service.listing(c)['total']==1
  assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
  for table in ('email_messages','client_reports'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  assert service.listing(c)['total']==0
  for call in (lambda:service.get(c,a['id']),lambda:service.note(c,a['id'],'Foreign'),lambda:service.company(c,b.id),lambda:service.membership(c,a['id'],lid)):
   with pytest.raises(HTTPException) as denied:call()
   assert denied.value.status_code==404
 with pytest.raises(HTTPException):service.listing(c)

def test_contact_public_urls_and_emails_are_validated_and_viewers_cannot_write(owned):
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):b=seed(c,org)
 for body in ({'name':'Person','source_url':'http://127.0.0.1/private'},{'name':'Person','work_email':'malformed'}):
  with pytest.raises(ValueError):service.Person(**body)
 c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(org,));c.commit()
 with workspace_scope(c,'controlled@example.test',org):
  with pytest.raises(HTTPException) as denied:service.save(c,b.id,service.Person(name='Denied contact'))
  assert denied.value.status_code==403


def test_people_upgrade_and_restore_preserve_imports_and_contact_safety(tmp_path,monkeypatch):
 import sqlite3
 from app.database import migrations
 from app.database.connection import get_connection
 from app.api.organization import create_organization
 from app.database.models import PipelineRun,Business
 from app.database.repositories import PipelineRunRepository
 latest=migrations.MIGRATIONS;source=get_connection(tmp_path/'before.db')
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:29]);migrations.run_migrations(source);org=create_organization(source,'owner@example.test','Preserved company')['organization_id']
 with workspace_scope(source,'owner@example.test',org):
  run=PipelineRun(market='London',vertical='hospitality',target=1);PipelineRunRepository(source).create(run,organization=org)
  b=Business(name='Historical company',normalized_name='historical company',vertical='hospitality',run_id=run.id);BusinessRepository(source).insert(b);pid=ProspectRepository(source).observe(b,organization=org)
  source.execute('INSERT INTO contact_people(id,prospect_id,name,source_url,created_at,created_by,organization_id) VALUES(?,?,?,?,?,?,?)',('legacy-person',pid,'Existing Person','import://owner','2026-11-06','owner@example.test',org))
 source.commit();original=dict(source.execute('SELECT * FROM contact_people').fetchone());backup=sqlite3.connect(tmp_path/'rollback.db');source.backup(backup)
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:31]);assert migrations.run_migrations(source)==2;assert migrations.run_migrations(source)==0
 migrated=dict(source.execute('SELECT * FROM contact_people').fetchone());assert {key:migrated[key] for key in original}==original and migrated['verification_state']=='UNKNOWN'
 assert source.execute('PRAGMA foreign_key_check').fetchall()==[]
 restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored);assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==29;assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 source.close();backup.close();restored.close()
