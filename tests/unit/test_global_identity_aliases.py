from test_automation import db
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository
import pytest
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def observe(c,city,website,email=None):
    run=PipelineRun(market=city,vertical='home_services',target=1);rid=PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b=Business(name='Controlled Company',normalized_name='controlled company',vertical='home_services',city=city,country='United Kingdom',website=website,domain=website.split('/')[2],public_email=email,run_id=rid)
    BusinessRepository(c).insert(b);return ProspectRepository(c).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)


def test_company_domain_matches_across_city_changes_and_preserves_history(db):
    first=observe(db,'London','https://controlled.invalid')
    assert observe(db,'Bristol','https://controlled.invalid')==first
    assert db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
    assert db.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==2


def test_public_company_email_matches_across_domain_changes(db):
    first=observe(db,'London','https://old-controlled.invalid','contact@controlled.invalid')
    assert observe(db,'Bristol','https://new-controlled.invalid','contact@controlled.invalid')==first


def test_legacy_profile_gets_alias_without_new_record_or_migration(db):
    first=observe(db,'London','https://controlled.invalid')
    db.execute("DELETE FROM business_identities WHERE evidence_type IN ('COMPANY_DOMAIN','COMPANY_EMAIL')")
    assert observe(db,'Bristol','https://controlled.invalid')==first
    assert db.execute("SELECT COUNT(*) FROM business_identities WHERE evidence_type='COMPANY_DOMAIN'").fetchone()[0]==1


def test_shared_host_tenants_do_not_merge_by_platform_root(db):
    first=observe(db,'London','https://tenant.wixsite.com/one')
    assert observe(db,'Bristol','https://tenant.wixsite.com/two')!=first


def test_conflicting_legacy_profiles_require_review_without_merging(db):
    first=observe(db,'London','https://one.invalid')
    other=observe(db,'Bristol','https://two.invalid')
    db.execute("UPDATE businesses SET domain='shared.invalid',website='https://shared.invalid'")
    with pytest.raises(ValueError,match='Conflicting canonical identity evidence'):
        observe(db,'Manchester','https://shared.invalid')
    assert db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==2
    assert {r[0] for r in db.execute('SELECT id FROM prospects').fetchall()}=={first,other}
