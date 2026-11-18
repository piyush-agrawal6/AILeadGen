"""Official App JWT/installation-token lifecycle. Tokens never leave the server."""
import asyncio,hashlib,time
from datetime import datetime,timezone
import jwt
from app.config.settings import get_settings
from app.intent_radar.source_http import JsonClient,ProviderFailure
_CACHE={}
_LOCKS={}

class GitHubAuth:
    def __init__(self,*,permit=lambda:True):self.settings=get_settings();self.permit=permit
    def jwt(self):
        key=self.settings.github_app_private_key.get_secret_value().replace('\\n','\n')
        issuer=self.settings.github_app_client_id or self.settings.github_app_id
        if not key or not issuer:raise ProviderFailure('GITHUB_APP_NOT_CONFIGURED')
        try:return jwt.encode({'iat':int(time.time())-60,'exp':int(time.time())+540,'iss':issuer},key,algorithm='RS256')
        except (ValueError,TypeError,jwt.PyJWTError):raise ProviderFailure('GITHUB_PRIVATE_KEY_INVALID') from None
    def client(self,token=None):
        return JsonClient('https://api.github.com',permit=self.permit,headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':self.settings.github_api_version,**({'Authorization':'Bearer '+token} if token else {})})
    async def app(self):return await self.client(self.jwt()).request('/app')
    async def installations(self,page=1):return await self.client(self.jwt()).request('/app/installations',params={'per_page':100,'page':page})
    async def installation(self,key):
        if not str(key).isdigit():raise ValueError('A numeric installation is required.')
        return await self.client(self.jwt()).request('/app/installations/'+str(key))
    async def token(self,key,repository_ids=None):
        key=str(key)
        if not key.isdigit():raise ValueError('A numeric installation is required.')
        repositories=sorted(set(repository_ids or []))
        if len(repositories)>100 or any(type(v) is not int or v<=0 for v in repositories):raise ValueError('Invalid repository selection.')
        fingerprint=hashlib.sha256((self.settings.github_app_id+':'+self.settings.github_app_private_key.get_secret_value()+':'+key+':'+str(repositories)).encode()).hexdigest()
        # Event-loop-local locks avoid sharing asyncio primitives across the
        # isolated loops used by worker executions and ordinary HTTP requests.
        lock_key=(id(asyncio.get_running_loop()),fingerprint)
        async with _LOCKS.setdefault(lock_key,asyncio.Lock()):
            cached=_CACHE.get(fingerprint)
            if cached and cached['until']>time.time()+120:return cached['token']
            detail=await self.installation(key)
            if detail.get('suspended_at'):raise ProviderFailure('GITHUB_INSTALLATION_SUSPENDED')
            permissions={k:'read' for k,v in detail.get('permissions',{}).items() if k in ('metadata','contents','issues','discussions','pull_requests') and v in ('read','write','admin')}
            payload={'permissions':permissions}
            if repositories:payload['repository_ids']=repositories
            result=await self.client(self.jwt()).request('/app/installations/'+key+'/access_tokens',method='POST',body=payload)
            try:until=datetime.fromisoformat(result['expires_at'].replace('Z','+00:00')).timestamp();token=result['token']
            except (ValueError,KeyError,TypeError):raise ProviderFailure('GITHUB_INVALID_TOKEN_RESPONSE') from None
            if not isinstance(token,str) or not token or until<=time.time()+120:raise ProviderFailure('GITHUB_INVALID_TOKEN_RESPONSE')
            if len(_CACHE)>256:_CACHE.clear();_LOCKS.clear()
            _CACHE[fingerprint]={'token':token,'until':until}
            return token
    @staticmethod
    def revoke_cached():_CACHE.clear()
