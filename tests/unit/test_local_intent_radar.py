import json

import pytest
from fastapi import HTTPException

from test_prospecting_only import owned
from app.api.organization import products
from app.config.settings import get_settings
from app.intent_radar.permissions import availability
from scripts.local_intent_radar import local_grant


def test_local_beta_grant_is_scoped_audited_idempotent_and_revocable(owned, monkeypatch):
    c, path, org, other = owned
    monkeypatch.setattr(get_settings(), 'intent_radar_stage', 'Beta')
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
    c.commit()
    assert local_grant(c, 'controlled@example.test', org, True)
    c.commit()
    assert products(c, org) == {'LEADGEN': True, 'INTENT_RADAR': True, 'SEARCH_VISIBILITY': False}
    assert availability(c, org)['enabled']
    assert not availability(c, other)['enabled']
    assert not availability(c, None)['enabled']
    assert not local_grant(c, 'controlled@example.test', org, True)
    entries = c.execute("SELECT actor,organization_id,details_json FROM audit_log WHERE action='LOCAL_INTENT_RADAR_BETA_CHANGED'").fetchall()
    assert len(entries) == 1 and entries[0]['organization_id'] == org
    assert json.loads(entries[0]['details_json'])['previous_enabled'] is False
    monkeypatch.setattr(get_settings(), 'intent_radar_stage', 'Disabled')
    assert not availability(c, org)['enabled']
    assert local_grant(c, 'controlled@example.test', org, False)
    c.commit()
    assert not products(c, org)['INTENT_RADAR'] and products(c, org)['LEADGEN']
    for table in ('businesses', 'contact_people', 'email_messages', 'intent_monitors'):
        assert c.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] == 0


def test_local_beta_grant_cannot_bypass_membership_roles_or_onboarding(owned):
    c, path, org, other = owned
    with pytest.raises(HTTPException):
        local_grant(c, 'controlled@example.test', other, True)
    with pytest.raises(ValueError, match='onboarding'):
        local_grant(c, 'controlled@example.test', org, True)
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
    for role in ('MEMBER', 'VIEWER'):
        c.execute('UPDATE organization_memberships SET role=? WHERE organization_id=?', (role, org))
        with pytest.raises(HTTPException) as denied:
            local_grant(c, 'controlled@example.test', org, True)
        assert denied.value.status_code == 403
    assert not products(c, org)['INTENT_RADAR']
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='LOCAL_INTENT_RADAR_BETA_CHANGED'").fetchone()[0] == 0
    c.execute("UPDATE organization_memberships SET role='ADMIN' WHERE organization_id=?", (org,))
    assert local_grant(c, 'controlled@example.test', org, True)


def test_missing_product_record_does_not_create_a_new_entitlement(owned):
    c, path, org, other = owned
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?", (org,))
    c.execute("DELETE FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR'", (org,))
    with pytest.raises(ValueError, match='record is missing'):
        local_grant(c, 'controlled@example.test', org, True)
    assert products(c, org)['LEADGEN'] and not products(c, org)['INTENT_RADAR']
