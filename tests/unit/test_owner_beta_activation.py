import pytest
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from scripts.activate_owner_radar_beta import grant

@pytest.fixture
def owner_database(tmp_path,monkeypatch):
    monkeypatch.setattr(get_settings(),'allowed_user_emails','planebyte@gmail.com')
    c=get_connection(tmp_path/'activation.db');run_migrations(c);c.commit()
    yield c
    c.close()

def test_dry_run_requires_real_membership_and_changes_no_grants(owner_database):
    c=owner_database;result=grant(c,'planebyte@gmail.com')
    assert result['mode']=='dry-run' and result['verified_role']=='OWNER'
    assert c.execute("SELECT enabled FROM organization_products WHERE product='INTENT_RADAR'").fetchone()[0]==0

def test_apply_is_exact_workspace_only_and_idempotent(owner_database):
    c=owner_database;other=create_organization(c,'planebyte@gmail.com','Separate non-beta company')['organization_id'];c.commit()
    result=grant(c,'planebyte@gmail.com',apply=True);c.commit()
    assert result['enabled'] and result['changed']
    assert c.execute("SELECT enabled FROM organization_products WHERE product='INTENT_RADAR' AND organization_id=?",(other,)).fetchone()[0]==0
    assert grant(c,'planebyte@gmail.com',apply=True)['changed'] is False
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='OWNER_APPROVED_RADAR_BETA'").fetchone()[0]==1

def test_incomplete_or_revoked_workspace_cannot_be_granted(owner_database):
    c=owner_database;c.execute("UPDATE organization_onboarding SET status='IN_PROGRESS'")
    with pytest.raises(RuntimeError):grant(c,'planebyte@gmail.com',apply=True)
    c.execute("UPDATE organization_onboarding SET status='COMPLETED'");c.execute("UPDATE organization_memberships SET role='VIEWER'")
    with pytest.raises(RuntimeError):grant(c,'planebyte@gmail.com',apply=True)
    assert c.execute("SELECT enabled FROM organization_products WHERE product='INTENT_RADAR'").fetchone()[0]==0
