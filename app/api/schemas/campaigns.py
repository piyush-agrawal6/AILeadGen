from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.config.settings import get_settings
from app.config.verticals import get_vertical_manager

Opportunity = Literal["WEBSITE", "SEO", "SECURITY"]


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cities: list[str] = Field(min_length=1, max_length=10)
    verticals: list[str] = Field(min_length=1, max_length=8)
    opportunities: list[Opportunity] = Field(default_factory=lambda: ["WEBSITE", "SEO", "SECURITY"], min_length=1, max_length=3)
    quality: Literal["maximum_volume", "balanced", "high_intent"] = "balanced"
    business_scales: list[Literal["LOCAL", "SMALL_GROUP", "MID_MARKET", "REGIONAL", "ENTERPRISE", "KNOWN_CHAIN"]] = Field(default_factory=lambda: ["LOCAL", "SMALL_GROUP","MID_MARKET"], min_length=1, max_length=6)
    social_enrichment_enabled: bool = True
    social_activity_enabled: bool = True
    results: Literal["new", "include_previous", "all"] = "new"
    target: int = Field(default=250, ge=5, le=1000)
    lighthouse_enabled: bool = True
    fixture: bool = False
    request_id: str = Field(pattern=r"^[a-f0-9-]{36}$")

    @model_validator(mode="after")
    def workload(self):
        settings = get_settings()
        self.cities = list(dict.fromkeys(city.strip() for city in self.cities))
        self.verticals = list(dict.fromkeys(self.verticals))
        self.opportunities = list(dict.fromkeys(self.opportunities))
        if any(len(city) < 2 or len(city) > 200 for city in self.cities):
            raise ValueError("Choose valid cities or custom locations")
        if len(self.cities) > settings.max_cities_per_scan or self.target > settings.max_target_leads:
            raise ValueError("Scan exceeds configured safety limits")
        if any(v not in get_vertical_manager().verticals for v in self.verticals):
            raise ValueError("Unknown vertical")
        if self.target < len(self.cities) * len(self.verticals):
            raise ValueError("Target must allow at least one result per city and vertical")
        if self.fixture and settings.app_env != "test":
            raise ValueError("Fixture campaigns are available only in explicit test mode")
        return self
