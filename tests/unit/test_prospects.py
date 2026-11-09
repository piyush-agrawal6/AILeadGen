import pytest
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business, PipelineRun
from app.database.repositories import BusinessRepository, PipelineRunRepository
from app.database.prospects import ProspectRepository
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


@pytest.fixture
def db(tmp_path,request):
    conn = get_connection(tmp_path / "prospects.db")
    run_migrations(conn)
    from tests.workspace_fixtures import bind_internal_workspace
    bind_internal_workspace(conn,request)
    yield conn
    conn.close()


def observation(conn, name="Independent Dentist", website="https://dental.example", city="Austin", source=None):
    run = PipelineRun(market=city, vertical="dentists", target=5)
    PipelineRunRepository(conn).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b = Business(name=name, normalized_name=name.lower(), vertical="dentists", city=city, website=website, run_id=run.id, external_osm_id=source)
    BusinessRepository(conn).insert(b)
    return b


def test_cross_scan_identity_preserves_workflow(db):
    repo = ProspectRepository(db)
    first = observation(db)
    from campaign_fixtures import campaign
    campaign(db,cid='campaign-one');campaign(db,cid='campaign-two')
    db.execute("UPDATE pipeline_runs SET campaign_id='campaign-one' WHERE id=?",(first.run_id,))
    pid = repo.observe(first, "campaign-one", organization=PLANEBYTE_ORGANIZATION_ID)
    from app.platform.context import current
    from app.platform.memberships import change_role
    change_role(db,current().actor,'b@example.com','MEMBER')
    repo.workflow(pid, "a@example.com", lead_status="CONTACTED", assigned_to="b@example.com")
    repo.add_note(pid, "b@example.com", "Call after reviewing public website evidence.")
    second = observation(db)
    db.execute("UPDATE pipeline_runs SET campaign_id='campaign-two' WHERE id=?",(second.run_id,))
    assert repo.observe(second, "campaign-two", organization=PLANEBYTE_ORGANIZATION_ID) == pid
    assert repo.dossier(second.id)["times_discovered"] == 2
    assert repo.dossier(second.id)["lead_status"] == "CONTACTED"
    assert repo.dossier(second.id)["first_campaign_id"] == "campaign-one"
    assert repo.dossier(second.id)["notes"][0]["created_by"] == "b@example.com"


def test_retry_does_not_increment_discovery_count(db):
    b = observation(db)
    repo = ProspectRepository(db)
    assert repo.observe(b, organization=PLANEBYTE_ORGANIZATION_ID) == repo.observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
    assert repo.dossier(b.id)["times_discovered"] == 1


def test_assignment_rejects_foreign_or_revoked_member_before_any_write(db):
    from fastapi import HTTPException
    from app.api.organization import create_organization
    from app.platform.context import current
    from app.platform.memberships import change_role
    repo=ProspectRepository(db)
    b=observation(db)
    pid=repo.observe(b,organization=PLANEBYTE_ORGANIZATION_ID)
    create_organization(db,'foreign@example.test','Other workspace')
    changes=db.total_changes
    with pytest.raises(HTTPException) as denied:
        repo.workflow(pid,current().actor,lead_status='CONTACTED',assigned_to='foreign@example.test')
    assert denied.value.status_code==422
    assert db.total_changes==changes
    assert repo.dossier(b.id)['lead_status']=='NEW'
    change_role(db,current().actor,'member@example.test','MEMBER')
    repo.workflow(pid,current().actor,assigned_to='member@example.test')
    db.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=? AND user_id=?",(PLANEBYTE_ORGANIZATION_ID,'member@example.test'))
    with pytest.raises(HTTPException):repo.workflow(pid,current().actor,assigned_to='member@example.test')
    # A historical assignment survives unrelated status changes, and can be cleared.
    repo.workflow(pid,current().actor,lead_status='SHORTLISTED')
    assert repo.dossier(b.id)['assigned_to']=='member@example.test'
    repo.workflow(pid,current().actor,assigned_to=None)
    assert repo.dossier(b.id)['assigned_to'] is None


def test_different_locations_and_hosted_tenants_do_not_merge(db):
    repo = ProspectRepository(db)
    a = observation(db, website="https://one.wixsite.com/dental")
    b = observation(db, website="https://one.wixsite.com/vet")
    c = observation(db, website="https://one.wixsite.com/dental", city="Dallas")
    assert len({repo.observe(a, organization=PLANEBYTE_ORGANIZATION_ID), repo.observe(b, organization=PLANEBYTE_ORGANIZATION_ID), repo.observe(c, organization=PLANEBYTE_ORGANIZATION_ID)}) == 3


def test_invalid_workflow_status_rejected_by_database(db):
    b = observation(db)
    repo = ProspectRepository(db)
    pid = repo.observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
    with pytest.raises(Exception):
        repo.workflow(pid, "a@example.com", lead_status="INVENTED")


def test_shared_corporate_domain_separate_street_addresses(db):
    repo = ProspectRepository(db)
    a = observation(db, name="Venue One", website="https://corporate.example/one")
    b = observation(db, name="Venue Two", website="https://corporate.example/two")
    a.address = "100 First Street"
    b.address = "200 Second Street"
    assert repo.observe(a, organization=PLANEBYTE_ORGANIZATION_ID) != repo.observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
