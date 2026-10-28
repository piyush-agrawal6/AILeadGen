from typing import List
from pydantic import BaseModel


class DiagnosticItem(BaseModel):
    name: str
    status: str  # "ok", "warning", "error"
    details: str
    ready: bool


class SystemDoctorResponse(BaseModel):
    overall_status: str  # "READY", "WARNING", "ERROR"
    diagnostics: List[DiagnosticItem]
    api_version: str = "2.0.0"
    environment: str = "local"
