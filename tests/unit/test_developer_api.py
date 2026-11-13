import hashlib,json,uuid
import pytest
from fastapi.testclient import TestClient
from app.api.server import app
from app.config.settings import get_settings
from app.database.connection import db_session
from app.platform.context import workspace_scope
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.database.models import PipelineRun,Business
from app.database.repositories import PipelineRunRepository,BusinessRepository
from app.database.prospects import ProspectRepository
from app.api.organization import create_organization
from app.developer import keys

@pytest.fixture
def developer(tmp_path,monkeypatch):
 settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'developer.db'));monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,foreign@example.test');monkeypatch.setattr(settings,'heysow_developer_api_enabled',True);monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
 with TestClient(app) as http:
  with db_session() as c:
   foreign=create_organization(c,'foreign@example.test','Other company')['organization_id'];c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='LEADGEN'",(foreign,));c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(foreign,))
   with workspace_scope(c,'owner@example.test',INTERNAL):
    run=PipelineRun(market='London',vertical='dentists',target=1);PipelineRunRepository(c).create(run,organization=INTERNAL);b=Business(name='Controlled API company',normalized_name='controlled api company',vertical='dentists',run_id=run.id);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,organization=INTERNAL)
  yield http,settings,b,foreign


def issue(http,scopes,foreign=False):
 response=http.post('/api/organization/developer/keys',json={'name':'Controlled integration','scopes':scopes},headers={'x-le-user':'foreign@example.test'} if foreign else {})
 assert response.status_code==201
 return response.json()


def test_versioned_api_requires_scoped_bearer_and_fixed_workspace_even_in_test_mode(developer):
 http,settings,b,other=developer
 assert http.get('/api/v1/companies').status_code==401
 issued=issue(http,['companies:read']);token=issued['token'];headers={'authorization':'Bearer '+token,'x-le-user':'foreign@example.test'}
 result=http.get('/api/v1/companies',headers=headers);assert result.status_code==200 and result.json()['items'][0]['id']==b.id
 assert result.headers['cache-control']=='private, no-store'
 assert http.get('/api/v1/contacts',headers=headers).status_code==403
 assert http.post('/api/v1/lists',headers={**headers,'Idempotency-Key':str(uuid.uuid4())},json={'name':'Denied'}).status_code==403
 other_key=issue(http,['companies:read'],True);foreign={'authorization':'Bearer '+other_key['token']}
 assert http.get('/api/v1/companies',headers=foreign).json()['items']==[]
 assert http.get('/api/v1/companies/'+str(b.id),headers=foreign).status_code==404
 assert http.get('/api/v1/companies?token=forbidden',headers=headers).status_code==401
 assert http.get('/api/v1/openapi.json',headers=headers).status_code==200
 document=http.get('/api/v1/openapi.json',headers=headers).json();assert all(path.startswith('/v1/') for path in document['paths'])
 assert document['components']['securitySchemes']['WorkspaceKey']['scheme']=='bearer'
 with db_session() as c:
  row=c.execute('SELECT token_hash FROM workspace_api_keys WHERE id=?',(issued['key']['id'],)).fetchone();assert row[0]==hashlib.sha256(token.encode()).hexdigest()
  assert not any(token in str(dict(row)) for row in c.execute('SELECT * FROM workspace_api_keys').fetchall())
 assert 'token_hash' not in http.get('/api/organization/developer/keys').text
 assert http.get('/api/organization/developer/keys').headers['cache-control']=='no-store'


def test_api_key_write_idempotency_rotation_revocation_and_membership_changes(developer):
 http,settings,b,other=developer;issued=issue(http,['companies:read','lists:read','lists:write']);key=issued['key']['id'];headers={'authorization':'Bearer '+issued['token'],'Idempotency-Key':str(uuid.uuid4())}
 first=http.post('/api/v1/lists',headers=headers,json={'name':'Controlled API list'});assert first.status_code==201
 assert http.post('/api/v1/lists',headers=headers,json={'name':'Controlled API list'}).json()['id']==first.json()['id']
 assert http.post('/api/v1/lists',headers=headers,json={'name':'Changed content'}).status_code==409
 assert http.post('/api/v1/lists',headers=headers,json={'name':'Forged organization','organization_id':other}).status_code==422
 rotated=http.post('/api/organization/developer/keys/'+key+'/rotate');assert rotated.status_code==200
 assert http.get('/api/v1/companies',headers=headers).status_code==401
 new=rotated.json();headers={'authorization':'Bearer '+new['token']};assert http.get('/api/v1/companies',headers=headers).status_code==200
 assert http.delete('/api/organization/developer/keys/'+new['key']['id']).status_code==200
 assert http.get('/api/v1/companies',headers=headers).status_code==401
 member_key=issue(http,['companies:read']);headers={'authorization':'Bearer '+member_key['token']}
 with db_session() as c:c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=? AND user_id=?",(INTERNAL,'owner@example.test'))
 assert http.get('/api/v1/companies',headers=headers).status_code==403


def test_api_limits_expiry_module_gate_and_cross_workspace_administration(developer,monkeypatch):
 http,settings,b,other=developer;issued=issue(http,['companies:read']);headers={'authorization':'Bearer '+issued['token']}
 monkeypatch.setattr(settings,'developer_key_requests_per_minute',1)
 assert http.get('/api/v1/companies',headers=headers).status_code==200
 rejected=http.get('/api/v1/companies',headers=headers);assert rejected.status_code==429 and 1<=int(rejected.headers['retry-after'])<=60
 assert http.delete('/api/organization/developer/keys/'+issued['key']['id'],headers={'x-le-user':'foreign@example.test'}).status_code==404
 with db_session() as c:c.execute("UPDATE workspace_api_keys SET expires_at='2000-01-01' WHERE id=?",(issued['key']['id'],))
 assert http.get('/api/v1/companies',headers=headers).status_code==401
 monkeypatch.setattr(settings,'heysow_developer_api_enabled',False)
 assert http.get('/api/v1/companies',headers=headers).status_code==503
 assert http.post('/api/organization/developer/keys',json={'name':'Disabled','scopes':['companies:read']}).status_code==503
