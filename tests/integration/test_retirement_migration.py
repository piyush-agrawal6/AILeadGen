"""Prove the clean-lineage retirement aborts atomically on unexpected data or dependencies."""
import pytest
from test_postgres import postgres,pytestmark
from app.config.settings import get_settings
from app.database import intent_profile as profile

@pytest.mark.parametrize('blocker',['populated','referenced'])
def test_1018_refuses_unsafe_drop(postgres,monkeypatch,blocker):
    c=postgres;s=get_settings();monkeypatch.setattr(s,'lead_engine_available',False)
    full=profile.migrations();assert full[-1][0]==1018
    monkeypatch.setattr(profile,'migrations',lambda:full[:-1])
    # The previous source used the previous structure fingerprint as its head.
    manifest=profile.manifest();prior={**manifest,**manifest['previous_versions']['1017']}
    with monkeypatch.context() as m:
        m.setattr(profile,'manifest',lambda:prior);profile.migrate(c)
    monkeypatch.setattr(profile,'migrations',lambda:full)
    from app.api.organization import create_organization
    monkeypatch.setattr(s,'subscription_onboarding_required',False)
    org=create_organization(c,'retirement-fixture@example.test','Preserved workspace')['organization_id']
    c.execute("INSERT INTO organization_products(organization_id,product,enabled,created_at,updated_at) VALUES(?,'LEADGEN',0,'test','test') ON CONFLICT(organization_id,product) DO NOTHING",(org,));
    if blocker=='populated':c.execute("INSERT INTO discovery_searches(id,organization_id,name,configuration_json,request_id,fingerprint,created_by,created_at,updated_at) VALUES('retained',?,'Retained fixture','{}','request','fp','retirement-fixture@example.test','test','test')",(org,))
    else:c.execute('CREATE VIEW retained_dependency AS SELECT id FROM discovery_searches')
    c.commit()
    with pytest.raises(Exception,match='retention review|depend on it'):profile.migrate(c)
    assert profile.verify(c)==1017 and c.execute("SELECT count(*) FROM organization_products WHERE organization_id=? AND product='LEADGEN'",(org,)).fetchone()[0]==1
