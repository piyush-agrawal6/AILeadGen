import asyncio
import pytest
from fastapi import HTTPException
from app.platform import modules
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

def test_disabled_experiment_cannot_be_triggered_even_by_owner(monkeypatch):
    monkeypatch.setattr(modules,'legacy_enabled',lambda:False)
    with pytest.raises(HTTPException) as error:modules.guard_route('/api/experiments/setup',organization_id=PLANEBYTE_ORGANIZATION_ID,role='OWNER')
    assert error.value.status_code==404
    from app.experiments.runtime import can_send,tick
    class NoDatabase:
        def execute(self,*a):raise AssertionError('Disabled jobs must not touch the database or provider.')
    assert can_send(NoDatabase(),'old') is False
    asyncio.run(tick(NoDatabase()))

def test_explicit_archive_access_still_requires_internal_workspace_owner(monkeypatch):
    monkeypatch.setattr(modules,'legacy_enabled',lambda:True)
    with pytest.raises(HTTPException):modules.guard_route('/api/experiments/current',organization_id='another-workspace',role='OWNER')
    with pytest.raises(HTTPException):modules.guard_route('/api/experiments/current',organization_id=PLANEBYTE_ORGANIZATION_ID,role='VIEWER')
    modules.guard_route('/api/experiments/current',organization_id=PLANEBYTE_ORGANIZATION_ID,role='OWNER')
    modules.guard_route('/api/acquisition',organization_id='another-workspace',role='MEMBER')

def test_unavailable_products_are_not_advertised_as_enabled():
    assert modules.MODULES['ai_agent'].lifecycle=='PLANNED'
    assert modules.MODULES['legacy_experiment'].lifecycle=='DISABLED'


def test_customer_owner_cannot_use_platform_wide_controls():
    for path in ('/api/automation/controls','/api/automation/markets/any','/api/foundation/emergency/email/pause','/api/foundation/health','/api/foundation/settings','/api/system','/api/acquisition/providers/vertex/test','/api/acquisition/sheets/authorize'):
        with pytest.raises(HTTPException) as error:modules.guard_route(path,organization_id='customer',role='OWNER')
        assert error.value.status_code==403
        modules.guard_route(path,organization_id=PLANEBYTE_ORGANIZATION_ID,role='OWNER')
    modules.guard_route('/api/organization/profile',organization_id='customer',role='OWNER')
    modules.guard_route('/api/foundation/contacts/owned',organization_id='customer',role='MEMBER')
