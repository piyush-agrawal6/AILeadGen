"""Bounded Firecrawl discovery. Structured extraction is cross-checked with page evidence."""
import asyncio,json,re,time,os
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
import httpx
from app.acquisition.config import settings
from app.acquisition.models import Strict
from pydantic import Field
from app.utils.urls import is_safe_url,extract_domain
from app.enrichment.contacts import extract_contacts_from_html

class SourceUnavailable(RuntimeError):pass
class PublicBusiness(Strict):
    company_name:str=Field(min_length=2,max_length=180)
    website:str|None=None
    description:str|None=Field(None,max_length=800)
    city:str|None=Field(None,max_length=100)
    region:str|None=Field(None,max_length=100)
    country:str|None=Field(None,max_length=100)
    phone:str|None=None
    email:str|None=None
    contact_page:str|None=None
    social_urls:list[str]=Field(default_factory=list,max_length=6)

DIRECTORIES={'yelp.com','tripadvisor.com','booking.com','expedia.com','facebook.com','instagram.com','linkedin.com','google.com','yell.com','thomsonlocal.com','indeed.com','wikipedia.org','cqc.org.uk','whatclinic.com','dentalchoices.org'}

def discovery_url_allowed(url):
    host=extract_domain(url)
    return bool(host and host not in DIRECTORIES and not re.search(r'(?:journal|directory|directories|reviews|listings|news)(?:\.[a-z]+){1,2}$',host))

def identity_text(value):
    return isinstance(value,str) and 2<=len(value.strip())<=180 and not re.search(r'(?i)^(?:copy link|recaptcha|facebook|instagram|linkedin|youtube|working feedback|cookie|privacy preference|just a moment|access denied|verify you are human)\b',value.strip())

def public_company_name(parsed,url,metadata=None):
    """Prefer first-party structured identity and document title over widget metadata."""
    for script in parsed.find_all('script',type='application/ld+json')[:20]:
        try:payload=json.loads(script.string or script.get_text())
        except (ValueError,TypeError):continue
        nodes=payload if isinstance(payload,list) else [payload]
        if isinstance(payload,dict) and isinstance(payload.get('@graph'),list):nodes.extend(payload['@graph'][:50])
        for node in nodes[:50]:
            if not isinstance(node,dict):continue
            kind=node.get('@type',[]);kind=[kind] if isinstance(kind,str) else kind
            if not isinstance(kind,list) or not any(t in ('Organization','LocalBusiness','Dentist','Hotel','Restaurant','MedicalBusiness','ProfessionalService','Corporation','LegalService','AutoRepair','VeterinaryCare') for t in kind):continue
            name=node.get('name');website=node.get('url') or node.get('@id','')
            if identity_text(name) and isinstance(website,str) and extract_domain(website)==extract_domain(url):return name.strip()
    # A rendered page can contain titles from embedded frames. Match fallback
    # names to the official site's brand rather than accepting its first title.
    host=re.sub(r'[^a-z0-9]','',extract_domain(url).split('.')[0].casefold())
    generic={'home','contact','contact us','about','about us','welcome','dentist','dentists','dental','clinic','practice','hotel','hotels','restaurant','services','photos','copy','link','the','and','for','your','with','best','care','health','online'}
    titles=[(metadata or {}).get('title','')]+[t.get_text(' ',strip=True) for t in parsed.find_all('title')[:20]]
    for title in titles:
        if not identity_text(title):continue
        for part in re.split(r'\s+[|–—-]\s+|\|',title):
            name=part.strip();tokens=re.findall(r'[a-z0-9]{3,}',name.casefold())
            if identity_text(name) and name.casefold() not in generic and any(t not in generic and t in host for t in tokens):return name
    # Metadata inside embedded third-party widgets is not the business identity.
    site=parsed.find('meta',property='og:site_name');canonical=parsed.find('meta',property='og:url')
    if site and canonical and extract_domain(canonical.get('content',''))==extract_domain(url):
        value=str(site.get('content','')).strip()
        if identity_text(value) and any(t not in generic and t in host for t in re.findall(r'[a-z0-9]{3,}',value.casefold())):return value
    return ''
class FirecrawlLeadSource:
    def __init__(self,config=None,transport=None,*,contactable=False):
        self.config=config or settings();self.transport=transport;self.contactable=contactable
        p=urlsplit(self.config.firecrawl_url)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or not is_safe_url(self.config.firecrawl_url,check_dns=False):raise SourceUnavailable('Configure a public HTTPS Firecrawl endpoint.')
        self.base=self.config.firecrawl_url.rstrip('/')
    async def request(self,path,body=None,method='POST'):
        from app.config.settings import get_settings
        if get_settings().app_env=='test' and self.transport is None and os.getenv('ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK')!='1':raise SourceUnavailable('Provider requests are disabled in offline tests.')
        key=self.config.firecrawl_key.get_secret_value()
        if not key:raise SourceUnavailable('Firecrawl acquisition unavailable. Configure FIRECRAWL_API_KEY on the server.')
        # Validate self-hosted endpoints too; never forward API credentials through redirects.
        if self.transport is None and not is_safe_url(self.base,check_dns=True):raise SourceUnavailable('Firecrawl endpoint is not publicly reachable.')
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(50,connect=5),follow_redirects=False,trust_env=False,transport=self.transport) as client:
                async with client.stream(method,self.base+path,json=body,headers={'Authorization':'Bearer '+key}) as response:
                    if not response.is_success:raise SourceUnavailable('Firecrawl acquisition unavailable (HTTP '+str(response.status_code)+'). Partial results are preserved.')
                    raw=bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw)>5_000_000:raise SourceUnavailable('Firecrawl response exceeded the bounded page limit.')
            result=json.loads(raw)
            if result.get('success') is not True:raise SourceUnavailable('Firecrawl did not return a successful response.')
            return result
        except SourceUnavailable:raise
        except (httpx.HTTPError,ValueError,TypeError):raise SourceUnavailable('Firecrawl acquisition unavailable. Partial results are preserved; retry explicitly.') from None
    async def search(self,query,limit=20,country_code=None):
        body={'query':query[:300],'limit':min(50,max(1,limit)),'sources':['web'],'timeout':40000}
        if country_code:body['country']=country_code
        result=await self.request('/v2/search',body);data=result.get('data') or {};rows=data.get('web',[]) if isinstance(data,dict) else data
        return {'items':[r for r in rows if isinstance(r,dict)][:limit],'credits':result.get('creditsUsed')}
    async def scrape(self,url):
        if not is_safe_url(url,check_dns=False):raise SourceUnavailable('Candidate URL must be a public HTTP website.')
        formats=['html','links'] if self.contactable else ['html','links',{'type':'json','schema':PublicBusiness.model_json_schema(),'prompt':'Extract one business operating this official website. Only public facts explicitly on this page. Use null for missing facts. Never infer contact details, location, security issues or performance.'}]
        result=await self.request('/v2/scrape',{'url':url,'formats':formats,'onlyMainContent':False,'timeout':40000,**({'parsers':[]} if self.contactable else {})})
        data=result.get('data') or {};data['_credits_used']=result.get('creditsUsed',data.get('metadata',{}).get('creditsUsed'));return data
    async def bounded_crawl(self,url,limit):
        """Opt-in contact/about discovery only, with hard page/depth/time limits."""
        if not 1<=limit<=5 or not is_safe_url(url,check_dns=False):raise SourceUnavailable('Bounded crawl accepts 1–5 public pages.')
        created=await self.request('/v2/crawl',{'url':url,'limit':limit,'maxDiscoveryDepth':1,'sitemap':'skip','includePaths':['^/?$','.*contact.*','.*about.*','.*team.*'],'allowExternalLinks':False,'allowSubdomains':False,'crawlEntireDomain':False,'scrapeOptions':{'formats':['html'],'onlyMainContent':False}})
        cid=created.get('id')
        if not isinstance(cid,str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}',cid):raise SourceUnavailable('Firecrawl crawl identifier was invalid.')
        for _ in range(8):
            await asyncio.sleep(1);result=await self.request('/v2/crawl/'+cid,method='GET')
            if result.get('status')=='completed':return (result.get('data') or [])[:limit]
            if result.get('status') in ('failed','cancelled'):raise SourceUnavailable('Bounded Firecrawl crawl failed.')
        await self.request('/v2/crawl/'+cid,method='DELETE')
        raise SourceUnavailable('Bounded Firecrawl crawl timed out and was cancelled.')
    async def health(self):
        result=await self.request('/v2/team/credit-usage',method='GET');data=result.get('data') or {}
        return {k:data[k] for k in ('remainingCredits','planCredits') if isinstance(data.get(k),(int,float))}

    def candidate(self,url,page):
        if not discovery_url_allowed(url):return None,'Directory/aggregator results require ownership review.'
        structured=page.get('json') or {}
        if self.contactable and not structured:
            parsed=BeautifulSoup(page.get('html') or '','html.parser');name=public_company_name(parsed,url,page.get('metadata'))
            structured={'company_name':name,'website':url}
        try:record=PublicBusiness.model_validate(structured)
        except ValueError:return None,'Structured business details were incomplete.'
        html=page.get('html') or ''
        if not isinstance(html,str) or not html or len(html)>3_000_000:return None,'No bounded public page evidence was returned.'
        soup=BeautifulSoup(html,'html.parser');text=' '.join(soup.stripped_strings).casefold()
        name=' '.join(record.company_name.split())
        if name.casefold() not in text and name.casefold() not in html.casefold():return None,'Company name was not confirmed in the public page.'
        final=page.get('metadata',{}).get('sourceURL') or url
        if not is_safe_url(final,check_dns=False) or extract_domain(final)!=extract_domain(url):return None,'Website ownership changed during extraction.'
        data={'company_name':name,'website':final,'description':record.description if record.description and record.description.casefold() in text else None,'source_url':final,'source_type':'FIRECRAWL'}
        evidence={k:{'source':'FIRECRAWL','url':final,'verification':'OBSERVED_PUBLIC_PAGE'} for k in ('company_name','website')}
        for key in ('city','region','country'):
            value=getattr(record,key)
            if value and value.casefold() in text:data[key]=value;evidence[key]={'source':'FIRECRAWL','url':final,'verification':'OBSERVED_PUBLIC_PAGE'}
        contacts=extract_contacts_from_html(html,final)
        if contacts.emails:data['email']=contacts.emails[0][0];evidence['email']={'source':'FIRECRAWL','url':contacts.emails[0][1],'verification':'PUBLICLY_PUBLISHED'}
        if contacts.phones:data['phone']=contacts.phones[0][0];evidence['phone']={'source':'FIRECRAWL','url':contacts.phones[0][1],'verification':'OBSERVED_PUBLIC_PAGE'}
        links=[str(x) for x in page.get('links',[]) if isinstance(x,str) and is_safe_url(x,check_dns=False)]
        contact=next((x for x in links if extract_domain(x)==extract_domain(final) and re.search(r'/(?:contact|about|team)',urlsplit(x).path,re.I)),None)
        data['contact_page']=contact;data['field_sources']=evidence
        data['evidence_text']=text[:12000]
        return data,None
