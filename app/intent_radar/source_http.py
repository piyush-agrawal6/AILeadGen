"""Bounded JSON requests to fixed official API hosts; no credential redirects."""
import asyncio,time,logging,re
from urllib.parse import urlsplit,urlencode
import httpx
from app.utils.http import SafeAsyncClient

class CredentialRedaction(logging.Filter):
    def filter(self,record):
        message=record.getMessage()
        redacted=re.sub(r'([?&](?:key|keyString|api_key|access_token|client_secret|token|password)=)[^&\s]+',r'\1[REDACTED]',message,flags=re.I)
        if redacted!=message:record.msg=redacted;record.args=()
        return True

logging.getLogger('httpx').addFilter(CredentialRedaction())

class ProviderFailure(RuntimeError):
    def __init__(self,code,*,status=None,retry_at=None):
        self.code,self.status,self.retry_at=code,status,retry_at
        super().__init__(code)

class JsonClient:
    def __init__(self,base,*,permit=lambda:True,headers=None,max_requests=24,seconds=25):
        self.base=base.rstrip('/');self.host=urlsplit(base).hostname;self.permit=permit;self.headers=headers or {};self.requests=0;self.max_requests=max_requests;self.deadline=time.monotonic()+seconds;self.last_headers={}
        if urlsplit(base).scheme!='https' or self.host not in ('api.github.com','github.com','www.googleapis.com','public.api.bsky.app','api.bsky.app','bsky.social','api.stackexchange.com'):raise ValueError('Only an explicit official provider base is supported.')
    async def request(self,path,*,params=None,method='GET',body=None,headers=None):
        if not path.startswith('/') or path.startswith('//') or '\\' in path:raise ValueError('A provider-relative endpoint is required.')
        url=self.base+path
        if params:url+='?'+urlencode(params,doseq=True)
        if self.requests>=self.max_requests or time.monotonic()>=self.deadline:raise ProviderFailure('PROVIDER_REQUEST_BUDGET')
        self.permit();self.requests+=1
        async with SafeAsyncClient(timeout=min(10,max(.1,self.deadline-time.monotonic())),max_bytes=1_000_000,redirect_limit=0) as client:
            kwargs={'headers':{'User-Agent':'PlaneByte-IntentRadar/2.0 (+https://planebyte.com)',**self.headers,**(headers or {})}}
            if method=='GET':response=await client.get(url,allowed_host=self.host,require_https=True,**kwargs)
            else:
                # Host and relative path are fixed above; the shared transport
                # resolves/pins public addresses and validates TLS for POST too.
                request=client.build_request(method,url,json=body,**kwargs)
                response=await client.send(request,stream=True,follow_redirects=False)
                try:
                    content=bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content)>1_000_000:raise ProviderFailure('PROVIDER_RESPONSE_TOO_LARGE')
                    clean=httpx.Headers(response.headers);clean.pop('content-encoding',None);clean.pop('content-length',None)
                    result=httpx.Response(response.status_code,headers=clean,content=bytes(content),request=request)
                finally:await response.aclose()
                response=result
        self.permit();self.last_headers=dict(response.headers)
        if response.is_redirect:raise ProviderFailure('PROVIDER_REDIRECT_DENIED',status=response.status_code)
        if response.status_code>=400:
            code='PROVIDER_AUTH_REQUIRED' if response.status_code==401 else 'PROVIDER_FORBIDDEN' if response.status_code==403 else 'PROVIDER_NOT_FOUND' if response.status_code==404 else 'PROVIDER_RATE_LIMITED' if response.status_code==429 else 'PROVIDER_UNAVAILABLE'
            try:
                error=response.json().get('error',{})
                reason=(error.get('errors') or [{}])[0].get('reason') if isinstance(error,dict) else None
                known={'quotaExceeded':'PROVIDER_QUOTA_EXHAUSTED','dailyLimitExceeded':'PROVIDER_QUOTA_EXHAUSTED','commentsDisabled':'COMMENTS_DISABLED','videoNotFound':'CONTENT_UNAVAILABLE','keyInvalid':'API_KEY_INVALID','accessNotConfigured':'API_SERVICE_DISABLED','forbidden':'PROVIDER_FORBIDDEN'}
                code=known.get(reason,code)
            except (ValueError,TypeError,AttributeError,IndexError):pass
            raise ProviderFailure(code,status=response.status_code,retry_at=response.headers.get('retry-after'))
        if response.status_code==304:return {'not_modified':True}
        try:return response.json()
        except ValueError:raise ProviderFailure('PROVIDER_INVALID_JSON',status=response.status_code) from None
