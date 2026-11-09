"""Bounded explicit geolocation lookup; no duplicate crawler or world-city DB."""
import hashlib,json,time
from pathlib import Path
from functools import lru_cache
import pycountry
from pydantic import BaseModel,Field,model_validator,ConfigDict
from fastapi import HTTPException

@lru_cache(maxsize=1)
def countries():
    return sorted([{'name':c.name,'iso2':c.alpha_2,'iso3':c.alpha_3} for c in pycountry.countries],key=lambda c:c['name'])

def country(value):
    try:return pycountry.countries.lookup(value)
    except LookupError:raise ValueError('Choose a recognized ISO country.')

class Location(BaseModel):
    model_config=ConfigDict(extra='forbid')
    city:str=Field(min_length=2,max_length=120)
    region:str=Field('',max_length=120)
    country:str=Field(min_length=2,max_length=120)
    country_code:str=Field(pattern='^[A-Z]{2}$')
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    bbox:tuple[float,float,float,float]|None=None
    label:str=Field(min_length=2,max_length=300)
    @model_validator(mode='after')
    def consistent(self):
        item=country(self.country_code)
        if country(self.country).alpha_2!=item.alpha_2:raise ValueError('Country and ISO code do not match.')
        self.country=item.name
        if self.bbox:
            south,north,west,east=self.bbox
            if not(-90<=south<north<=90 and -180<=west<east<=180):raise ValueError('Invalid geographic bounds.')
        self.label=', '.join(dict.fromkeys(x for x in (self.city,self.region,self.country) if x))
        return self

async def search(c,query,code):
    from app.config.settings import get_settings
    from app.utils.http import SafeAsyncClient
    from app.api.read_cache import read_cache
    s=get_settings();item=country(code);q=query.strip()
    if len(q)<3:return []
    cache_key='geo:'+hashlib.sha256((s.nominatim_url+item.alpha_2+q.casefold()).encode()).hexdigest()
    path=Path('data/cache/locations')/(cache_key[4:]+'.json')
    if path.is_file() and time.time()-path.stat().st_mtime<86400:
        try:return [Location.model_validate(x).model_dump() for x in json.loads(path.read_text())]
        except (ValueError,OSError):pass
    cfg=read_cache.configuration()
    if cfg:
        cached=await read_cache.command('GET',cfg[2]+':'+cache_key)
        if cached:
            try:return [Location.model_validate(x).model_dump() for x in json.loads(cached)]
            except (ValueError,TypeError):pass
    # Shared DB reservation remains effective when Redis is unavailable.
    at=time.time()
    reserved=c.execute('INSERT INTO provider_rate_limits(provider,next_request_at) VALUES(?,?) ON CONFLICT(provider) DO UPDATE SET next_request_at=excluded.next_request_at WHERE provider_rate_limits.next_request_at<=? RETURNING provider',('nominatim',at+1.1,at)).fetchone()
    c.commit()
    if not reserved:raise HTTPException(429,'Location provider is busy. Retry shortly.',headers={'Retry-After':'2'})
    try:
        async with SafeAsyncClient(timeout=8,max_bytes=200000,headers={'User-Agent':s.crawler_user_agent+' contact:'+s.crawler_contact_email}) as client:
            response=await client.get(s.nominatim_url.rstrip('/')+'/search',params={'q':q,'format':'jsonv2','addressdetails':1,'countrycodes':item.alpha_2.lower(),'limit':5,'featureType':'city'})
            response.raise_for_status();data=response.json()
    except Exception:raise HTTPException(503,'City lookup is unavailable. Retry later or use a saved market.') from None
    results=[]
    for r in data[:5]:
        a=r.get('address',{});city=a.get('city') or a.get('town') or a.get('village') or a.get('municipality')
        if not city or a.get('country_code','').upper()!=item.alpha_2:continue
        try:loc=Location(city=city,region=a.get('state') or a.get('county') or '',country=item.name,country_code=item.alpha_2,latitude=float(r['lat']),longitude=float(r['lon']),bbox=tuple(float(v) for v in r['boundingbox']) if r.get('boundingbox') else None,label=city)
        except (ValueError,KeyError):continue
        results.append(loc.model_dump())
    path.parent.mkdir(parents=True,exist_ok=True)
    try:path.write_text(json.dumps(results))
    except OSError:pass
    if cfg:await read_cache.command('SET',cfg[2]+':'+cache_key,json.dumps(results),'EX',86400)
    return results

def seed_selected(c,locations,verticals):
    import uuid
    from app.database.prospects import now
    for loc in locations:
        loc=Location.model_validate(loc);city=', '.join(dict.fromkeys(x for x in (loc.city,loc.region) if x))
        # Reuse the existing market table and geographic disk cache.
        from app.config.markets import _load_disk_cache,_save_disk_cache
        lookup=city+', '+loc.country;stored=_load_disk_cache()
        if loc.bbox:
            south,north,west,east=loc.bbox
            stored[lookup.strip().lower()]={'query':lookup,'city':loc.city,'state':loc.region,'country':loc.country,'country_code':loc.country_code,'center_lat':loc.latitude,'center_lon':loc.longitude,'bbox':{'min_lat':south,'max_lat':north,'min_lon':west,'max_lon':east}}
            _save_disk_cache(stored)
        for vertical in verticals:
            c.execute('INSERT INTO scan_markets(id,country,region,city,vertical,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(country,city,vertical) DO NOTHING',(str(uuid.uuid4()),loc.country,loc.region,city,vertical,now(),now()))
