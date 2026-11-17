"""One platform-wide provider order; only inference failures permit fallback."""
import asyncio,json,random,time
from collections import Counter
from datetime import datetime,timedelta,timezone
from app.acquisition.ai import (GeminiInstructionProvider,AiUnavailable,AiApplicationError,AiProviderError,AiOutputError,AiContentRejected,AiAuthError,AiTransportError,AiRateLimited,AiProvidersUnavailable)
from app.acquisition.config import settings
from app.acquisition.vertex import VertexAIProvider
from app.database.prospects import now


def normalized_error(exc):
    if isinstance(exc,AiRateLimited):return 'QUOTA_EXCEEDED' if exc.kind=='QUOTA_EXHAUSTED' else 'RATE_LIMITED'
    if isinstance(exc,AiAuthError):return 'AUTH_ERROR'
    if isinstance(exc,AiOutputError):return 'INVALID_RESPONSE'
    if isinstance(exc,AiContentRejected):return 'CONTENT_REJECTED'
    if isinstance(exc,AiTransportError):return 'TIMEOUT' if 'timeout' in str(exc).lower() else 'NETWORK_ERROR'
    if isinstance(exc,AiProviderError):
        return {401:'AUTH_ERROR',403:'AUTH_ERROR',402:'QUOTA_EXCEEDED',404:'MODEL_UNAVAILABLE',408:'TIMEOUT',429:'RATE_LIMITED',500:'UNKNOWN_PROVIDER_ERROR',502:'NETWORK_ERROR',503:'MODEL_UNAVAILABLE',504:'TIMEOUT'}.get(exc.status,'INVALID_INTERNAL_REQUEST' if exc.status==400 else 'UNKNOWN_PROVIDER_ERROR')
    return 'UNKNOWN_PROVIDER_ERROR'

class AIProviderRouter(GeminiInstructionProvider):
    provider_name='AI_ROUTER'
    is_router=True
    def __init__(self,config=None,*,c=None,providers=None):
        super().__init__(config);self.c=c;self.metrics=Counter();self.last_provider=None;self.last_model=None;self.memory={}
        if providers is not None:self.providers=providers
        else:
            vertex=VertexAIProvider(self.config);gemini=GeminiInstructionProvider(self.config)
            self.providers=([vertex,gemini] if self.config.primary_provider=='vertex' else [gemini,vertex])
            self.providers=[p for p in self.providers if (p.provider_name=='VERTEX_AI' and self.config.vertex_enabled) or (p.provider_name=='GEMINI_API' and self.config.gemini_enabled and bool(self.config.gemini_key.get_secret_value()))]
            if not self.config.fallback_enabled:self.providers=[p for p in self.providers if p.provider_name==('VERTEX_AI' if self.config.primary_provider=='vertex' else 'GEMINI_API')]
        for provider in self.providers:provider.usage_connection=self.c
    def states(self):
        if self.c is None:return self.memory
        from app.config.settings import get_settings
        if get_settings().database_schema_profile!='intent-radar-v1':
            try:
                row=self.c.execute('SELECT configuration_json FROM acquisition_preferences WHERE id=1').fetchone()
                if row:return json.loads(row[0]).get('ai_providers',{})
            except Exception:
                pass
        try:
            rows=self.c.execute('SELECT provider,status,error_code,checked_at FROM acquisition_provider_health').fetchall()
            health={}
            for r in rows:
                pname='VERTEX_AI' if r['provider']=='vertex' else 'GEMINI_API'
                health[pname]={'provider':pname,'status':r['status'],'error_code':r['error_code'],'checked_at':r['checked_at']}
            return {**self.memory,**health}
        except Exception:
            return self.memory
    def record(self,p,status,error=None,retry_after=None):
        state={'provider':p.provider_name,'model':p.model,'status':status,'error_code':error,'retry_after':retry_after,'checked_at':now()}
        if p.provider_name=='VERTEX_AI':state.update(project=self.config.vertex_project,location=self.config.vertex_location,authentication='SERVICE_IDENTITY' if __import__('os').getenv('K_SERVICE') or __import__('os').getenv('CLOUD_RUN_JOB') else 'ADC')
        self.memory[p.provider_name]=state
        if self.c is None:return
        c=self.c
        from app.config.settings import get_settings
        if get_settings().database_schema_profile!='intent-radar-v1':
            try:
                if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691945612)')
                row=c.execute('SELECT configuration_json FROM acquisition_preferences WHERE id=1').fetchone();config=json.loads(row[0]) if row else {};config.setdefault('ai_providers',{})[p.provider_name]=state
                c.execute('INSERT INTO acquisition_preferences(id,configuration_json,updated_by,updated_at) VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET configuration_json=excluded.configuration_json,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(json.dumps(config),'ai-router',now()))
            except Exception:
                pass
        try:
            c.execute('INSERT INTO acquisition_provider_health(provider,status,checked_at,error_code) VALUES(?,?,?,?) ON CONFLICT(provider) DO UPDATE SET status=excluded.status,checked_at=excluded.checked_at,error_code=excluded.error_code',('vertex' if p.provider_name=='VERTEX_AI' else 'gemini',status,now(),error));c.commit()
        except Exception:
            pass
    async def structured(self,instruction,value,model,*,bypass_cooldown=False,attempts_per_provider=3,**options):
        # Application/schema construction runs outside provider-failure handling.
        if not isinstance(model.model_json_schema(),dict):raise AiApplicationError('Invalid internal AI schema.')
        if type(attempts_per_provider) is not int or not 1<=attempts_per_provider<=3:raise AiApplicationError('Provider attempt bound must be between one and three.')
        budget=min(170,options.get('timeout_seconds',35)*(2 if options.get('raw_json') else 1));start=time.monotonic();errors={};invalid=False
        for p in self.providers:
            state=self.states().get(p.provider_name,{})
            if not bypass_cooldown and state.get('retry_after') and state['retry_after']>now():errors[p.provider_name]=state.get('error_code','COOLDOWN');continue
            prefix='vertex' if p.provider_name=='VERTEX_AI' else 'gemini'
            for attempt in range(attempts_per_provider):
                remaining=budget-(time.monotonic()-start)
                if remaining<2:break
                self.metrics[prefix+'_requests']+=1
                if prefix=='gemini' and self.config.primary_provider=='vertex':self.metrics['gemini_fallback_requests']+=1
                before=time.monotonic();parameters={**options,'retry_transient':False,'timeout_seconds':min(options.get('timeout_seconds',35),max(2,int(remaining)))}
                try:
                    output=await p.structured(instruction,value,model,**parameters)
                    self.metrics[prefix+'_successes']+=1;self.last_provider=p.provider_name;self.last_model=p.model;self.last_usage=getattr(p,'last_usage',None);self.record(p,'READY');return output
                except (AiProviderError,AiAuthError,AiTransportError,AiOutputError,AiContentRejected) as exc:
                    code=normalized_error(exc)
                    if code=='INVALID_INTERNAL_REQUEST':raise AiApplicationError('Internal provider request/schema was rejected; review it before retrying.') from None
                    errors[p.provider_name]=code;self.metrics[prefix+'_failures']+=1
                    if code in ('QUOTA_EXCEEDED','RATE_LIMITED'):self.metrics[prefix+('_quota_errors' if code=='QUOTA_EXCEEDED' else '_rate_limits')]+=1
                    if code=='INVALID_RESPONSE':invalid=True;self.record(p,'DEGRADED',code);break
                    transient=code in ('TIMEOUT','NETWORK_ERROR','UNKNOWN_PROVIDER_ERROR') or isinstance(exc,AiProviderError) and exc.status in (500,502,503,504)
                    if transient and attempt<attempts_per_provider-1 and time.monotonic()-start<budget-3:
                        await asyncio.sleep(2**attempt+random.uniform(0,.25));continue
                    seconds=exc.retry_after if isinstance(exc,AiRateLimited) else 3600 if code in ('QUOTA_EXCEEDED','AUTH_ERROR') else 300 if code=='MODEL_UNAVAILABLE' else 60
                    self.record(p,'DEGRADED',code,(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat());break
                finally:self.metrics[prefix+'_latency_ms']+=round((time.monotonic()-before)*1000)
        if invalid:raise AiOutputError('Structured provider output was invalid; a smaller batch may be attempted.')
        raise AiProvidersUnavailable(errors)
