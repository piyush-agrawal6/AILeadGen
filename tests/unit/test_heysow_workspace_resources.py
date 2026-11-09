"""Fail closed at worker resource boundaries, without providers or live data."""
import sqlite3

import pytest

from app.acquisition.pipeline import inherit_existing
from app.database.models import Business
from app.database.prospects import ProspectRepository, identity_keys
from app.platform.workspace import business_workspace


@pytest.fixture
def resources():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE pipeline_runs(id INTEGER PRIMARY KEY,organization_id TEXT,campaign_id TEXT);
        CREATE TABLE scan_campaigns(id TEXT PRIMARY KEY,organization_id TEXT);
        CREATE TABLE prospects(id TEXT PRIMARY KEY,organization_id TEXT);
        CREATE TABLE business_identities(identity_key TEXT PRIMARY KEY,prospect_id TEXT);
        CREATE TABLE businesses(id INTEGER PRIMARY KEY,run_id INTEGER,prospect_id TEXT,
            website TEXT,phone TEXT,is_rejected INTEGER DEFAULT 0);
        CREATE TABLE contacts(id INTEGER PRIMARY KEY,business_id INTEGER,contact_type TEXT,contact_value TEXT,
            source_url TEXT,is_valid INTEGER,is_public_business_contact INTEGER);
        INSERT INTO scan_campaigns VALUES('ca','a'),('cb','b');
        INSERT INTO pipeline_runs VALUES(1,'a','ca'),(2,'b','cb'),(3,NULL,NULL);
        INSERT INTO prospects VALUES('pa','a');
        INSERT INTO businesses VALUES(1,1,'pa','https://controlled.invalid','123456789',0);
        INSERT INTO businesses VALUES(2,2,NULL,NULL,NULL,0),(3,3,NULL,NULL,NULL,0);
        INSERT INTO contacts VALUES(1,1,'email','published@controlled.invalid',
            'https://controlled.invalid/contact',1,1);
    """)
    yield conn
    conn.close()


def company(identifier=1, run_id=1):
    return Business(id=identifier, run_id=run_id, name="Controlled Company",
                    normalized_name="controlled company", vertical="home_services",
                    city="Bristol", country="United Kingdom", domain="controlled.invalid")


def test_resource_context_checks_persisted_run_and_campaign_before_writes(resources):
    conn = resources
    assert business_workspace(conn, company(), organization="a", campaign_id="ca") == "a"
    before = conn.total_changes
    for business, organization, campaign in [
        (company(), "b", "ca"),
        (company(), "a", "cb"),
        (company(run_id=2), "b", "cb"),
        (company(3, 3), "a", None),
    ]:
        with pytest.raises(ValueError):
            ProspectRepository(conn).observe(business, campaign, organization=organization)
    with pytest.raises(ValueError, match="organization context"):
        ProspectRepository(conn).observe(company())
    assert conn.total_changes == before


def test_reusing_lead_evidence_never_crosses_workspaces(resources):
    conn = resources
    for key, _ in identity_keys(company()):
        conn.execute("INSERT INTO business_identities VALUES(?,?)", (key, "pa"))
    other = company(2, 2)
    evidence = {}
    inherit_existing(conn, other, evidence, organization="b")
    assert other.website is None and other.public_email is None and evidence == {}
    own = company()
    inherit_existing(conn, own, evidence, organization="a")
    assert own.website == "https://controlled.invalid"
    assert own.public_email == "published@controlled.invalid"
    assert evidence["field_sources"]["email"]["source"] == "EXISTING_MASTER"
    with pytest.raises(ValueError, match="workspace context"):
        inherit_existing(conn, other, {}, organization=None)
