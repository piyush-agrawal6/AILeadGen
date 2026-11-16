"""Assisted setup round-trip in a disposable PostgreSQL schema, no live providers."""
from contextlib import contextmanager
from unittest.mock import AsyncMock
import uuid
from test_intent_radar_postgres import pg_radar,postgres,pytestmark
from app.database.postgres import PostgresConnection
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.platform import onboarding_ai as setup,company_discovery as reviews,company_autofill
from app.acquisition.config import AcquisitionSettings
from app.acquisition import ai as gateway
from app.icp import builder,ai as icp_ai
from test_icp_business_builder import five_candidates


def test_postgres_reviewed_setup_worker_replay_defaults_and_no_automatic_actions(pg_radar,monkeypatch):
    c,org,_=pg_radar;s=get_settings()
    for flag in ('heysow_workspace_management_enabled','heysow_company_discovery_enabled','heysow_company_ai_enabled','heysow_icp_ai_enabled','heysow_setup_diagnostics_enabled'):monkeypatch.setattr(s,flag,True)
    cfg=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,AI_PRIMARY_PROVIDER='vertex')
    monkeypatch.setattr(company_autofill,'provider_settings',lambda:cfg);monkeypatch.setattr(icp_ai,'provider_settings',lambda:cfg)
    provider=AsyncMock();provider.structured.return_value=builder.exact_suggestions(5)(candidates=five_candidates());monkeypatch.setattr(gateway,'provider',lambda c:provider)
    @contextmanager
    def session(path=None):
        db=PostgresConnection(s.database_url,schema=c.schema)
        try:yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()
    monkeypatch.setattr(reviews,'db_session',session)
    c.execute("UPDATE organization_onboarding SET status='IN_PROGRESS' WHERE organization_id=?",(org,));c.commit()
    with workspace_scope(c,'radar-pg@example.test',org):
        profile=setup.state(c)['company']
        fields={key:value for key,value in profile.items() if key in setup.CompanyUpdate.model_fields}
        fields.update(description='We build custom software for businesses.',countries_served=['United Kingdom'],products_services=[{'name':'Custom applications'}])
        saved=setup.company(c,setup.SaveCompany(revision=0,objective='RESEARCH_MARKETS',profile=fields));c.commit()
        request=setup.Recommend(revision=saved['progress']['revision'],request_id=uuid.uuid4())
        job=setup.recommendations(c,request);c.commit();reviews.execute(job['review']['id'])
        reviewed=setup.detail(c,job['review']['id']);assert reviewed['status']=='READY',reviewed
        assert len(reviewed['preview']['candidates'])==5
        assert reviewed['attempt_history'][0]['outcome']=='STARTED'
        assert reviewed['attempt_history'][-1]['outcome']=='READY'
        assert all(event['attempt']==1 for event in reviewed['attempt_history'])
        again=setup.recommendations(c,request);assert again['progress']['revision']==job['progress']['revision'];c.commit()
        proposal=reviewed['preview'];draft=proposal['candidates'][0]['draft']
        body=setup.Accept(revision=job['progress']['revision'],proposal_id=proposal['proposal_id'],candidates=[{'candidate_index':0,**{k:v for k,v in draft.items() if k in ('name','description','criteria')}}],primary_index=0,request_id=uuid.uuid4(),research_keywords=['Custom applications'])
        accepted=setup.accept(c,body);c.commit();assert setup.accept(c,body)['progress']==accepted['progress'];c.commit()
        finish=setup.Finish(revision=accepted['progress']['revision'],primary_icp_id=accepted['progress']['default_icp_id'],research_keywords=['Custom applications'],excluded_keywords=['jobs'])
        assert setup.finish(c,finish)['status']=='COMPLETED';c.commit()
        assert setup.finish(c,finish)['discovery_started'] is False;c.commit()
        assert setup.state(c)['progress']['status']=='COMPLETED'
        assert provider.structured.await_count==1
        for table in ('intent_monitors','intent_discoveries','email_messages'):
            assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE organization_id=?',(org,)).fetchone()[0]==0
