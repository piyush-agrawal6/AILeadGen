"""Bounded stated company attributes from public structured data, never estimates."""
import json
from bs4 import BeautifulSoup
from app.utils.text import normalize_business_name


def extract(pages,company_name=None):
    fields={};remaining=1000
    def record(key,value,url):
        if key in fields or value in (None,'',[]):return
        if isinstance(value,str):value=value.strip()[:1500]
        if isinstance(value,list):value=list(dict.fromkeys(str(item).strip()[:180] for item in value if isinstance(item,str) and item.strip()))[:20]
        if value not in ('',[]):fields[key]={'value':value,'source_url':url,'evidence_type':'STATED_STRUCTURED_DATA','independently_verified':False}
    def walk(value,url,depth=0):
        nonlocal remaining
        if remaining<=0 or depth>10:return
        remaining-=1
        if isinstance(value,list):
            for item in value[:100]:walk(item,url,depth+1)
        elif isinstance(value,dict):
            types=value.get('@type',[]);types=[types] if isinstance(types,str) else types
            if isinstance(types,list) and any(item in types for item in ('Organization','Corporation','LocalBusiness','ProfessionalService')):
                name=value.get('name');matches=isinstance(name,str) and (not company_name or normalize_business_name(name)==normalize_business_name(company_name))
                if matches:
                    record('name',name,url)
                    for field in ('description','industry','slogan'):
                        if isinstance(value.get(field),str):record(field,value[field],url)
                    n=value.get('numberOfEmployees');n=n.get('value') if isinstance(n,dict) else n
                    if isinstance(n,int) and not isinstance(n,bool) and 0<=n<=10000000:record('employee_count',n,url)
                    address=value.get('address',{})
                    if isinstance(address,dict):
                        for key,target in [('addressLocality','city'),('addressRegion','region'),('addressCountry','country')]:
                            raw=address.get(key)
                            if isinstance(raw,dict):raw=raw.get('name')
                            if isinstance(raw,str):record(target,raw,url)
                    areas=value.get('areaServed',[]);areas=areas if isinstance(areas,list) else [areas]
                    record('countries_or_areas_served',[item.get('name','') if isinstance(item,dict) else item for item in areas],url)
                    catalog=value.get('hasOfferCatalog',{})
                    if isinstance(catalog,dict):
                        offers=catalog.get('itemListElement',[])
                        if isinstance(offers,list):record('products_services',[item.get('itemOffered',{}).get('name','') for item in offers[:20] if isinstance(item,dict) and isinstance(item.get('itemOffered'),dict)],url)
            for item in value.values():
                if isinstance(item,(dict,list)):walk(item,url,depth+1)
    for url,html in list(pages.items())[:3]:
        for script in BeautifulSoup(html[:500000],'html.parser').find_all('script',type='application/ld+json')[:20]:
            text=script.string or ''
            if len(text)>128000:continue
            try:walk(json.loads(text),url)
            except (ValueError,TypeError,RecursionError):continue
    return fields
