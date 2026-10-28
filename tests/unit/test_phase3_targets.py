import json
import pytest
from app.config.presets import market_presets
from app.config.verticals import get_vertical_manager
from app.database.models import Business
from app.qualification.vertical_validator import VerticalValidator
from app.api.schemas.campaigns import CampaignCreate


@pytest.mark.parametrize("vertical,tag", [("home_services",{"craft":"plumber"}),("dentists",{"amenity":"dentist"}),("auto_repair",{"shop":"car_repair"}),("legal",{"office":"lawyer"}),("veterinary",{"amenity":"veterinary"})])
def test_new_verticals_require_source_tags(vertical, tag):
    b=Business(name="Independent local business", normalized_name="independent local business",vertical=vertical,source_tags=json.dumps(tag))
    assert VerticalValidator.validate(b)[0].value == "VALID"
    b.source_tags=None
    assert VerticalValidator.validate(b)[0].value == "UNCERTAIN"
    b.source_category="restaurant"
    assert VerticalValidator.validate(b)[0].value == "INVALID"


def test_presets_cover_requested_countries_and_cities():
    presets=market_presets()
    assert {p["country_code"] for p in presets} == {"US","GB","CA","AU","FR","DE"}
    assert sum(len(p["cities"]) for p in presets) == 38
    assert all(c["lookup_name"] and c["priority"] and c["country_code"] for p in presets for c in p["cities"])
    assert len(get_vertical_manager().verticals) == 8


def test_campaign_limits_and_unknown_verticals():
    base={"cities":["Austin, United States"],"verticals":["dentists"],"target":5,"request_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
    assert CampaignCreate(**base).opportunities == ["WEBSITE","SEO","SECURITY"]
    with pytest.raises(ValueError): CampaignCreate(**{**base,"verticals":["unknown"]})
    with pytest.raises(ValueError): CampaignCreate(**{**base,"cities":[str(i) for i in range(11)]})
