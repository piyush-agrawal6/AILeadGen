import sqlite3
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate

@pytest.fixture
def companies():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
 owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
 other=create_organization(c,'second@example.test','Second workspace')['organization_id']
 yield c,owner,other
 c.close()

def test_profile_preserves_unrelated_data_and_rejects_stale_updates(companies):
 c,owner,other=companies
 with workspace_scope(c,owner,INTERNAL):
  before=read_profile(c)
  body=CompanyUpdate(**{k:v for k,v in before.items() if k not in ('organization_id','can_edit','onboarding_status')})
  body.name='Controlled Engineering';body.website='https://controlled.example.com';body.countries_served=['United Kingdom']
  result=save_profile(c,body)
  assert result['name']=='Controlled Engineering' and result['version']!=before['version']
  assert result['onboarding_status']=='COMPLETED'
  assert c.execute('SELECT COUNT(*) FROM organization_services WHERE organization_id=?',(INTERNAL,)).fetchone()[0]>0
  with pytest.raises(HTTPException) as error:save_profile(c,body)
  assert error.value.status_code==409
  same=CompanyUpdate(**{k:v for k,v in result.items() if k not in ('organization_id','can_edit','onboarding_status')})
  changes=c.total_changes;assert save_profile(c,same)==result;assert c.total_changes==changes
  source=c.execute("SELECT source_type,confirmed_by_user FROM organization_profile_sources WHERE organization_id=? AND field_name='website' ORDER BY detected_at DESC",(INTERNAL,)).fetchone()
  assert tuple(source)==('USER_ENTERED',1)
 with workspace_scope(c,'second@example.test',other):
  assert read_profile(c)['name']=='Second workspace'
 assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_viewer_reads_only_own_profile_and_cannot_modify_it(companies):
 c,owner,other=companies
 with workspace_scope(c,owner,INTERNAL):change_role(c,owner,'second@example.test','VIEWER')
 with workspace_scope(c,'second@example.test',INTERNAL):
  result=read_profile(c);assert not result['can_edit']
  body=CompanyUpdate(name='Unauthorized',version=result['version'])
  changes=c.total_changes
  with pytest.raises(HTTPException):save_profile(c,body)
  assert c.total_changes==changes
 with pytest.raises(HTTPException):read_profile(c)

@pytest.mark.parametrize('fields',[{'website':'http://127.0.0.1'},{'website':'javascript:alert(1)'},{'timezone':'Invalid/Timezone'},{'contact_email':'bad\r\nBcc:x@example.com'},{'countries_served':['x'*101]}])
def test_profile_input_validation(fields):
 with pytest.raises(ValidationError):CompanyUpdate(name='Controlled Company',**fields)
