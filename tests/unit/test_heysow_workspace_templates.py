import sqlite3,json
import pytest
from fastapi import HTTPException
from app.mail.workspace_templates import render_template,quality
from app.api.routes.mail import save_template,Template

@pytest.fixture
def workspace_db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 c.executescript('''CREATE TABLE schema_migrations(version INTEGER);INSERT INTO schema_migrations VALUES(16);
 CREATE TABLE organizations(id TEXT PRIMARY KEY,name TEXT,status TEXT DEFAULT 'ACTIVE');
 CREATE TABLE organization_memberships(organization_id TEXT,user_id TEXT,role TEXT,status TEXT);
 CREATE TABLE organization_profiles(organization_id TEXT,display_name TEXT,contact_email TEXT);
 CREATE TABLE organization_settings(id INTEGER PRIMARY KEY,organization_id TEXT,configuration_json TEXT);
 CREATE TABLE pipeline_runs(id INTEGER PRIMARY KEY,organization_id TEXT);
 CREATE TABLE businesses(id INTEGER PRIMARY KEY,run_id INTEGER,name TEXT,website TEXT,city TEXT,vertical TEXT);
 CREATE TABLE prospects(id TEXT PRIMARY KEY,organization_id TEXT);
 CREATE TABLE email_templates(id TEXT PRIMARY KEY,name TEXT,category TEXT,vertical TEXT,subject TEXT,body_text TEXT,enabled INTEGER,updated_at TEXT,organization_id TEXT);
 INSERT INTO organizations(id,name) VALUES('a','Example Engineering'),('b','Another Company');
 INSERT INTO organization_memberships VALUES('a','owner-a','OWNER','ACTIVE'),('b','owner-b','OWNER','ACTIVE');
 INSERT INTO pipeline_runs VALUES(1,'a'),(2,'b');
 INSERT INTO businesses VALUES(1,1,'Customer One',NULL,'Bristol','dentists');
 INSERT INTO prospects VALUES('p1','a'),('p2','b');''')
 c.execute('INSERT INTO organization_settings VALUES(1,?,?)',('a',json.dumps({'outreach':{'signature':'Example Engineering\nhello@example.test'}})))
 yield c;c.close()

def test_workspace_copy_needs_no_audit_or_pdf_and_uses_own_signature(workspace_db):
 c=workspace_db
 t=Template(name='Introduction',category='General',subject='Hello {{company_name}}',body_text='Hi {{business_name}}, we help teams keep their software reliable and make practical improvements. Reply if this is relevant.\n\n{{signature}}')
 save_template(c,'custom',t,'a')
 from app.platform.context import workspace_scope
 with workspace_scope(c,'owner-a','a'):result=render_template(c,1,'custom')
 assert result['rendered_subject']=='Hello Customer One' and 'Example Engineering' in result['rendered_body']
 assert 'PlaneByte' not in result['rendered_body'] and result['outreach_strategy']=='WORKSPACE'
 assert quality(c,'p1',{'template_id':'custom','subject':result['rendered_subject'],'body_text':result['rendered_body']})==[]
 assert quality(c,'p2',{'template_id':'custom','subject':'Hi','body_text':'Words '*15})

def test_template_update_cannot_take_over_another_workspace_record(workspace_db):
 c=workspace_db;t=Template(name='Mine',category='General',subject='Hello',body_text='An ordinary message to review before sending.')
 save_template(c,'same-id',t,'a')
 with pytest.raises(HTTPException) as error:save_template(c,'same-id',t,'b')
 assert error.value.status_code==404
 assert c.execute('SELECT organization_id FROM email_templates WHERE id=?',('same-id',)).fetchone()[0]=='a'
