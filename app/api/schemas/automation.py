"""Allowlisted customer summary; internal controls and diagnostics never serialize."""
from pydantic import BaseModel, ConfigDict, Field


class SummaryRecord(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)


class Today(SummaryRecord):
    qualified: int = Field(ge=0)
    sent: int = Field(ge=0)
    replies: int = Field(ge=0)
    bounces: int = Field(ge=0)
    queued: int = Field(ge=0)
    manual: int = Field(ge=0)


class Targets(SummaryRecord):
    daily_lead_target: int = Field(ge=0)
    daily_email_target: int = Field(ge=0)
    hourly_limit: int = Field(ge=0)
    daily_limit: int = Field(ge=0)


class ContactCount(SummaryRecord):
    contact_state: str = Field(min_length=1, max_length=80)
    count: int = Field(ge=0)


class QueueCount(SummaryRecord):
    status: str = Field(min_length=1, max_length=80)
    count: int = Field(ge=0)


class CustomerSummary(SummaryRecord):
    today: Today
    # Retain the existing consumer's key, but expose only workspace target values.
    environment: Targets
    contact_counts: list[ContactCount]
    queue: list[QueueCount]
