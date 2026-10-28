"""Versioned public-footprint heuristics; never an estimate of spending power."""
import json
import re
from urllib.parse import urlsplit,urljoin,urlunsplit
from bs4 import BeautifulSoup
from app.config.verticals import get_vertical_manager
from app.database.prospects import now

CLASSIFICATION_VERSION='scale-2.0.1'

def professional_domain(value):
    if not isinstance(value,str):return False
    host=value.lower().strip().rstrip('.')
    return '.' in host and all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?',part) for part in host.split('.')) and host not in ('nan','none','null','localhost')


def classify_scale_v2(business,location_count=1,city_count=1,region_count=1,pages=None):
    manager=get_vertical_manager()
    if manager.is_chain_domain(business.domain) or manager.is_chain_name(business.name,business.vertical):return 'KNOWN_CHAIN','Known chain name or registered domain',.99
    links=set();schema_locations=0;franchise=False
    for url,html in (pages or {}).items():
        soup=BeautifulSoup(html,'html.parser')
        for a in soup.find_all('a',href=True):
            href=urljoin(url,a['href'])
            if urlsplit(href).hostname!=urlsplit(url).hostname:continue
            if re.search(r'/(?:locations|offices|clinics|hotels|branches)/[^/?#]+',href,re.I):links.add(href.split('?')[0].rstrip('/'))
        for script in soup.find_all('script',type='application/ld+json'):
            try:
                data=json.loads(script.string or script.get_text())
                nodes=data if isinstance(data,list) else [data]
                for node in nodes:
                    if isinstance(node,dict):
                        locations=node.get('location',[])
                        if isinstance(locations,list):schema_locations=max(schema_locations,len(locations))
            except (ValueError,TypeError):pass
        franchise=franchise or bool(re.search(r'franchise opportunities|become a franchisee|our franchise network',soup.get_text(' ',strip=True),re.I))
    footprint=max(location_count,len(links),schema_locations,1)
    corroborated=city_count>1 or region_count>1 or len(links)>1 or schema_locations>1
    context=f'{footprint} observed locations or location pages; {city_count} cities; {region_count} regions'
    if franchise and footprint>=6:return 'KNOWN_CHAIN','Public franchise-network evidence with a multi-location footprint',.85
    if footprint>100 and corroborated:return 'ENTERPRISE',context+'; broad corroborated footprint',.9
    if footprint>=26:return 'REGIONAL',context,.8 if corroborated else .65
    if footprint>=6:return 'MID_MARKET',context+'; independent multi-location target',.85 if corroborated else .65
    if footprint>=2:return 'SMALL_GROUP',context,.8 if corroborated else .65
    return 'LOCAL','One observed location; no wider footprint established',.6


def commercial_fit(business,scale,contactability,profile=None):
    if scale in ('ENTERPRISE','KNOWN_CHAIN'):return 'LOW','Outside the default independent-business target size; this is not a revenue assessment.'
    contact=contactability in ('HIGH','MEDIUM')
    site=bool(business.website and professional_domain(business.domain))
    if scale in ('MID_MARKET','SMALL_GROUP') and site and contact:return 'HIGH','Public multi-location footprint, professional website domain and an available contact route.'
    if site and contact and (scale=='REGIONAL' or profile and profile.reachable):return 'HIGH','Established public website and contact route; suitable for a focused digital improvement discussion.'
    if site or contact:return 'MEDIUM','Some public digital/contact evidence; scope and budget still require a conversation.'
    return 'UNKNOWN','Insufficient public footprint and contact evidence; no spending capacity is inferred.'


def footprint_counts(conn,business):
    if not professional_domain(business.domain):return 1,1,1
    if any(business.domain==x or business.domain.endswith('.'+x) for x in ('wixsite.com','wordpress.com','squarespace.com','square.site','webflow.io')):return 1,1,1
    row=conn.execute("SELECT COUNT(DISTINCT COALESCE(address,'') || '|' || COALESCE(city,'') || '|' || COALESCE(country,'')),COUNT(DISTINCT city),COUNT(DISTINCT state) FROM businesses WHERE domain=? AND is_rejected=0",(business.domain,)).fetchone()
    return max(1,row[0]),max(1,row[1]),max(1,row[2])


def store_intelligence(conn,business,scale,reason,confidence,footprint,fit,fit_reason,social_status='UNKNOWN',metrics=None):
    pid=conn.execute('SELECT prospect_id FROM businesses WHERE id=?',(business.id,)).fetchone()[0]
    conn.execute('''INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,social_presence_status,enrichment_metrics_json,created_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(business_id) DO UPDATE SET classification_version=excluded.classification_version,business_scale=excluded.business_scale,scale_reason=excluded.scale_reason,scale_confidence=excluded.scale_confidence,footprint_json=excluded.footprint_json,commercial_fit=excluded.commercial_fit,commercial_reason=excluded.commercial_reason,social_presence_status=excluded.social_presence_status,enrichment_metrics_json=excluded.enrichment_metrics_json''',
      (business.id,pid,CLASSIFICATION_VERSION,scale,reason,confidence,json.dumps(footprint),fit,fit_reason,social_status,json.dumps(metrics or {}),now()))
