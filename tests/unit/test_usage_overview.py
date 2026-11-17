"""Current scope, real counters, price approval, and historical-provider labels."""
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned
from app.billing.overview import overview
from app.platform.context import workspace_scope

def test_customer_usage_requires_membership_and_has_nonchargeable_catalog(radar):
    c,path,org,other=radar
    with pytest.raises(HTTPException):overview(c)
    with workspace_scope(c,'controlled@example.test',org):
        result=overview(c)
        assert result['access']['kind']=='Approved Beta'
        assert result['commercial_pricing_approved'] and not result['live_payments_enabled']
        assert result['commercial']['provider']=='creem' and not result['commercial']['checkout_enabled']
        assert result['commercial']['catalog']['plans'][0]['limits']['reports']==5
        assert result['provider_usage']['estimated_cost_usd'] is None
        assert result['team_seats']==1 and all(i['enforced'] for i in result['usage'])
    with workspace_scope(c,'foreign@example.test',other):
        result=overview(c)
        assert result['access']['kind']=='Restricted'
        assert result['commercial']['historical_payments']==[]
