from app.billing import commercial
from importlib.util import find_spec
import asyncio
import pytest
from fastapi import HTTPException

def test_retired_payment_transport_and_callback_are_inert():
    from app.api.routes import fixed_term_billing as routes
    for module in ('app.billing.payu','app.billing.payu_v2'):
        assert find_spec(module) is None
    for call in (routes.create, lambda: asyncio.run(routes.callback(None))):
        with pytest.raises(HTTPException) as denied:call()
        assert denied.value.status_code==410

def test_catalog_approved_prices_not_arbitrary_test_amounts_or_binding_limits():
    catalog=commercial.catalog()
    assert [(p['code'],p['monthly_minor']) for p in catalog['plans']]==[('starter',5900),('growth',14900),('scale',37900),('enterprise',None)]
    assert catalog['prices_approved'] and catalog['allowances_approved'] and not catalog['checkout_enabled']
    assert not catalog['annual_billing'] and not catalog['free_trial']
    assert catalog['plans'][0]['limits']['searches']==100
    assert catalog['plans'][-1]['limits'] is None
    assert catalog['excluded_products']==['lead-engine']
