from pathlib import Path
from pydantic import Field,SecretStr
from pydantic_settings import BaseSettings,SettingsConfigDict
from fastapi import HTTPException

class AcquisitionSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file=Path(__file__).resolve().parents[2]/'.env',extra='ignore',hide_input_in_errors=True)
    enable_ai:bool=Field(False,alias='ENABLE_AI_ACQUISITION')
    enable_firecrawl:bool=Field(False,alias='ENABLE_FIRECRAWL_ACQUISITION')
    enable_import:bool=Field(False,alias='ENABLE_LEAD_IMPORT')
    enable_sheets:bool=Field(False,alias='ENABLE_GOOGLE_SHEETS_IMPORT')
    ai_provider:str=Field('gemini',alias='AI_PROVIDER')
    primary_provider:str=Field('gemini',alias='AI_PRIMARY_PROVIDER',pattern=r'^(vertex|gemini)$')
    vertex_enabled:bool=Field(False,alias='VERTEX_AI_ENABLED')
    vertex_project:str=Field('querryside',alias='VERTEX_AI_PROJECT_ID',pattern=r'^[a-z][a-z0-9-]{4,61}[a-z0-9]$')
    vertex_location:str=Field('global',alias='VERTEX_AI_LOCATION',pattern=r'^[a-z0-9-]{2,30}$')
    vertex_model:str=Field('gemini-3.6-flash',alias='VERTEX_AI_MODEL',pattern=r'^[a-zA-Z0-9._-]{1,100}$')
    gemini_enabled:bool=Field(True,alias='GEMINI_API_ENABLED')
    fallback_enabled:bool=Field(True,alias='AI_FALLBACK_ENABLED')
    gemini_model:str=Field('gemini-3.8-flash',alias='GEMINI_MODEL',pattern=r'^[a-zA-Z0-9._-]{1,100}$')
    copy_batch_size:int=Field(40,ge=10,le=50,alias='GEMINI_COPY_BATCH_SIZE')
    gemini_key:SecretStr=Field(SecretStr(''),alias='GEMINI_API_KEY',repr=False,exclude=True)
    firecrawl_key:SecretStr=Field(SecretStr(''),alias='FIRECRAWL_API_KEY',repr=False,exclude=True)
    firecrawl_url:str=Field('https://api.firecrawl.dev',alias='FIRECRAWL_API_URL')
    google_id:str=Field('',alias='AUTH_GOOGLE_ID',repr=False,exclude=True)
    google_secret:SecretStr=Field(SecretStr(''),alias='AUTH_GOOGLE_SECRET',repr=False,exclude=True)
    sheets_redirect_uri:str=Field('https://leads.planebyte.com/acquisition/sheets/callback',alias='GOOGLE_SHEETS_REDIRECT_URI')
    job_name:str=Field('leadengine-acquisition',alias='ACQUISITION_CLOUD_RUN_JOB')
    model_pricing_json:str=Field('{}',alias='AI_MODEL_PRICING_JSON',repr=False)

def settings():return AcquisitionSettings()
def require(feature,c=None):
    s=settings()
    if not getattr(s,'enable_'+feature):raise HTTPException(503,{'code':'ACQUISITION_FEATURE_DISABLED','message':'This acquisition feature is not enabled yet.'})
    if c is not None:
        from app.acquisition.preferences import load
        if not load(c).get('enabled',{}).get(feature,True):raise HTTPException(503,'This acquisition source is disabled in workspace settings.')
    return s
