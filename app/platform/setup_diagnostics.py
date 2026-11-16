"""Safe machine-readable causes and durable attempt events, never model content."""
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import organization

CODES=frozenset(('INSUFFICIENT_COMPANY_EVIDENCE','INVALID_GROUNDING_REVIEW','ICP_UNSUPPORTED_CRITERIA','ICP_UNKNOWN_SERVICE','ICP_DUPLICATE_SEGMENTS','ICP_TOO_MANY_SEGMENTS','ICP_VERBOSE_RESPONSE','AI_TIMEOUT','AI_NETWORK_ERROR','AI_RATE_LIMITED','AI_QUOTA_EXCEEDED','AI_AUTH_ERROR','AI_MODEL_UNAVAILABLE','AI_OUTPUT_INVALID','AI_CONTENT_REJECTED','AI_INTERNAL_REQUEST_INVALID','SETUP_CONTEXT_CHANGED','SETUP_ACCESS_REVOKED','SETUP_LIMIT_EXHAUSTED','WEBSITE_REVIEW_FAILED','SETUP_REVIEW_FAILED'))
_trace=ContextVar('setup_attempt_trace',default=None)

class SetupAIError(HTTPException):
    def __init__(self,code):
        self.diagnostic_code=code if code in CODES else 'AI_OUTPUT_INVALID'
        super().__init__(503,'AI could not prepare reliable suggestions. Your saved details are unchanged. Review the analysis details before retrying.')

@contextmanager
def attempt():
    trace={'started':time.monotonic(),'provider':None,'model':None,'stage':'STARTING'}
    token=_trace.set(trace)
    try:yield trace
    finally:_trace.reset(token)

def provider_observed(provider):
    trace=_trace.get()
    if trace is not None:trace.update(provider=provider.provider_name if provider.provider_name in ('VERTEX_AI','GEMINI_API') else None,model=provider.model[:100])

def error_code(error):
    from app.acquisition import ai
    from app.acquisition.ai_router import normalized_error
    from pydantic import ValidationError
    if getattr(error,'diagnostic_code',None) in CODES:return error.diagnostic_code
    if isinstance(error,ai.AiOutputError):return str(error) if str(error) in CODES else 'AI_OUTPUT_INVALID'
    if isinstance(error,ai.AiProvidersUnavailable):
        values=set(error.errors.values())
        # Preserve actual provider failure class; never an arbitrary response body.
        for value in ('AUTH_ERROR','QUOTA_EXCEEDED','RATE_LIMITED','MODEL_UNAVAILABLE','TIMEOUT','NETWORK_ERROR'):
            if value in values:return 'AI_'+value
        return 'AI_OUTPUT_INVALID' if 'INVALID_RESPONSE' in values else 'SETUP_REVIEW_FAILED'
    if isinstance(error,ai.AiApplicationError):return 'AI_INTERNAL_REQUEST_INVALID'
    if isinstance(error,ai.AiUnavailable):
        value='AI_'+normalized_error(error)
        return value if value in CODES else 'SETUP_REVIEW_FAILED'
    if isinstance(error,TimeoutError):return 'AI_TIMEOUT'
    if isinstance(error,ValidationError):return 'AI_OUTPUT_INVALID'
    return {403:'SETUP_ACCESS_REVOKED',409:'SETUP_CONTEXT_CHANGED',429:'SETUP_LIMIT_EXHAUSTED'}.get(getattr(error,'status_code',None),'SETUP_REVIEW_FAILED')

def event(c,row,attempt_number,stage,outcome,trace,code=None):
    if not get_settings().heysow_setup_diagnostics_enabled:return
    if row['organization_id']!=organization():raise HTTPException(403,'Setup attempt workspace mismatch.')
    stages={'STARTING','READING_WEBSITE','RENDERING_WEBSITE','ANALYZING','CHECKING_EVIDENCE','VALIDATING','READY','FAILED','CANCELLED'}
    if stage not in stages:raise ValueError('Unsupported setup diagnostic stage')
    c.execute('INSERT INTO organization_profile_job_events(id,organization_id,job_id,attempt,stage,outcome,error_code,provider,model,duration_ms,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),organization(),row['id'],attempt_number,stage,outcome,code if code in CODES else None,trace.get('provider'),trace.get('model'),max(0,round((time.monotonic()-trace['started'])*1000)),now()))

def history(c,key):
    if not get_settings().heysow_setup_diagnostics_enabled:return []
    return [dict(r) for r in c.execute('SELECT attempt,stage,outcome,error_code,provider,model,duration_ms,created_at FROM organization_profile_job_events WHERE organization_id=? AND job_id=? ORDER BY created_at,id LIMIT 40',(organization(),key)).fetchall()]
