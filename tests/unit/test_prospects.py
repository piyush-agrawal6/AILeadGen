import pytest
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business, PipelineRun
from app.database.repositories import BusinessRepository, PipelineRunRepository
from app.database.prospects import ProspectRepository


@pytest.fixture
def db(tmp_path):
    conn = get_connection(tmp_path / "prospects.db")
    run_migrations(conn)
    yield conn
    conn.close()


def observation(conn, name="Independent Dentist", website="https://dental.example", city="Austin", source=None):
    run = PipelineRun(market=city, vertical="dentists", target=5)
    PipelineRunRepository(conn).create(run)
    b = Business(name=name, normalized_name=name.lower(), vertical="dentists", city=city, website=website, run_id=run.id, external_osm_id=source)
    BusinessRepository(conn).insert(b)
    return b


def test_cross_scan_identity_preserves_workflow(db):
    repo = ProspectRepository(db)
    first = observation(db)
    pid = repo.observe(first, "campaign-one")
    repo.workflow(pid, "a@example.com", lead_status="CONTACTED", assigned_to="b@example.com")
    repo.add_note(pid, "b@example.com", "Call after reviewing public website evidence.")
    second = observation(db)
    assert repo.observe(second, "campaign-two") == pid
    assert repo.dossier(second.id)["times_discovered"] == 2
    assert repo.dossier(second.id)["lead_status"] == "CONTACTED"
    assert repo.dossier(second.id)["first_campaign_id"] == "campaign-one"
    assert repo.dossier(second.id)["notes"][0]["created_by"] == "b@example.com"


def test_retry_does_not_increment_discovery_count(db):
    b = observation(db)
    repo = ProspectRepository(db)
    assert repo.observe(b) == repo.observe(b)
    assert repo.dossier(b.id)["times_discovered"] == 1


def test_different_locations_and_hosted_tenants_do_not_merge(db):
    repo = ProspectRepository(db)
    a = observation(db, website="https://one.wixsite.com/dental")
    b = observation(db, website="https://one.wixsite.com/vet")
    c = observation(db, website="https://one.wixsite.com/dental", city="Dallas")
    assert len({repo.observe(a), repo.observe(b), repo.observe(c)}) == 3


def test_invalid_workflow_status_rejected_by_database(db):
    b = observation(db)
    repo = ProspectRepository(db)
    pid = repo.observe(b)
    with pytest.raises(Exception):
        repo.workflow(pid, "a@example.com", lead_status="INVENTED")


def test_shared_corporate_domain_separate_street_addresses(db):
    repo = ProspectRepository(db)
    a = observation(db, name="Venue One", website="https://corporate.example/one")
    b = observation(db, name="Venue Two", website="https://corporate.example/two")
    a.address = "100 First Street"
    b.address = "200 Second Street"
    assert repo.observe(a) != repo.observe(b)
