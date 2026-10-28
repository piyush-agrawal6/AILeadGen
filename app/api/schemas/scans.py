from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ScanSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exclude_chains: bool = True
    lighthouse_enabled: bool = True
    overture_enabled: bool = True
    osm_enabled: bool = True
    max_pages: Optional[int] = Field(default=8, ge=1, le=50)
    page_timeout: Optional[int] = Field(default=15, ge=3, le=60)
    site_timeout: Optional[int] = Field(default=60, ge=10, le=300)
    http_concurrency: Optional[int] = Field(default=20, ge=1, le=100)
    crawler_concurrency: Optional[int] = Field(default=5, ge=1, le=20)
    min_score: Optional[float] = Field(default=35.0, ge=0.0, le=100.0)


class ScanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market: str = Field(..., min_length=2, max_length=200)
    vertical: str = Field(default="restaurant", min_length=2, max_length=100)
    target: int = Field(default=50, ge=5, le=1000)
    settings: Optional[ScanSettings] = Field(default_factory=ScanSettings)


class ScanCreateResponse(BaseModel):
    run_id: int
    status: str
    message: str


class PipelineEventSchema(BaseModel):
    id: Optional[int] = None
    run_id: int
    timestamp: Optional[str] = None
    stage: str
    event_type: str
    message: str
    completed: int = 0
    total: int = 0
    metadata_json: Optional[str] = None


class PipelineRunDetail(BaseModel):
    id: int
    market: str
    vertical: str
    target: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str
    raw_found: int = 0
    deduped: int = 0
    filtered: int = 0
    websites_processed: int = 0
    qualified: int = 0
    exported: int = 0
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    cancelled_at: Optional[str] = None
    run_configuration: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None
