"""Vertex adapter for the existing structured provider, authenticated only by ADC."""
import asyncio,copy,os
from app.acquisition.ai import GeminiInstructionProvider,AiAuthError,AiApplicationError

def vertex_schema(schema):
    """Translate Pydantic JSON schema to Vertex's supported responseSchema subset.

    Full semantic/length/extra-field validation still runs in application code.
    """
    definitions=schema.get('$defs',{})
    allowed={'type','description','properties','required','items','enum','format','nullable','anyOf','minimum','maximum','propertyOrdering'}
    def convert(node,depth=0):
        if depth>25:raise AiApplicationError('Internal AI schema is too deeply nested.')
        if not isinstance(node,dict):return node
        if '$ref' in node:
            name=node['$ref'].removeprefix('#/$defs/')
            if name not in definitions:raise AiApplicationError('Unresolved internal AI schema reference.')
            return convert(copy.deepcopy(definitions[name]),depth+1)
        out={k:v for k,v in node.items() if k in allowed}
        if 'const' in node and isinstance(node['const'],str) and node['const']:out['enum']=[node['const']]
        if 'properties' in out:
            out['properties']={k:convert(v,depth+1) for k,v in out['properties'].items()};out['propertyOrdering']=list(out['properties'])
        if 'items' in out:out['items']=convert(out['items'],depth+1)
        if 'anyOf' in out:out['anyOf']=[convert(v,depth+1) for v in out['anyOf']]
        if isinstance(out.get('type'),str):out['type']=out['type'].upper()
        if out.get('enum') and any(not isinstance(v,str) for v in out['enum']):out.pop('enum')
        return out
    return convert(schema)

class VertexAIProvider(GeminiInstructionProvider):
    provider_name='VERTEX_AI'
    def __init__(self,config=None,transport=None,credentials=None):
        super().__init__(config,transport);self.credentials=credentials;self.auth_kind='SERVICE_IDENTITY' if os.getenv('K_SERVICE') or os.getenv('CLOUD_RUN_JOB') else 'ADC'
    @property
    def model(self):return self.config.vertex_model
    def generation_format(self,schema):return {'responseMimeType':'application/json','responseSchema':vertex_schema(schema)}
    def access_token(self):
        if os.getenv('APP_ENV')=='production' and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):raise AiAuthError('Production Vertex must use its attached service identity, not a credential-file environment variable.')
        try:
            import google.auth
            from google.auth.transport.requests import Request
            if self.credentials is None:self.credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'],quota_project_id=self.config.vertex_project)
            if not self.credentials.valid:
                class BoundedRequest(Request):
                    def __call__(self,*args,**kwargs):kwargs['timeout']=10;return super().__call__(*args,**kwargs)
                self.credentials.refresh(BoundedRequest())
            if not self.credentials.token:raise AiAuthError('Vertex ADC did not provide an access token.')
            return self.credentials.token
        except AiAuthError:raise
        except Exception as exc:
            # ADC exception bodies may contain credential metadata or paths.
            raise AiAuthError('Vertex ADC authentication failed ('+type(exc).__name__+').') from None
    async def request_target(self):
        if not self.config.vertex_enabled:raise AiAuthError('Vertex AI is disabled in server configuration.')
        token=await asyncio.to_thread(self.access_token);s=self.config;host='aiplatform.googleapis.com' if s.vertex_location=='global' else s.vertex_location+'-aiplatform.googleapis.com'
        endpoint='https://'+host+'/v1/projects/'+s.vertex_project+'/locations/'+s.vertex_location+'/publishers/google/models/'+s.vertex_model+':generateContent'
        return endpoint,{'Authorization':'Bearer '+token,'x-goog-user-project':s.vertex_project}
