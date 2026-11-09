"""Conservative public Person extraction; no inferred names or email patterns."""
import json,re
from bs4 import BeautifulSoup
from app.utils.text import normalize_business_name

def extract_people(pages,company_name,maximum=20):
    found=[];seen=set();remaining=500
    def walk(value,url,organization=None,depth=0):
        nonlocal remaining
        if depth>10 or remaining<=0 or len(found)>=maximum:return
        remaining-=1
        if isinstance(value,list):
            for item in value[:100]:walk(item,url,organization,depth+1)
        elif isinstance(value,dict):
            kind=value.get('@type',[]);kind=[kind] if isinstance(kind,str) else kind
            organization=company_name if 'Organization' in kind and normalize_business_name(str(value.get('name','')))==normalize_business_name(company_name) else organization
            if 'Person' in kind:
                employer=value.get('worksFor',{});employer=employer.get('name','') if isinstance(employer,dict) else employer
                affiliated=isinstance(employer,str) and normalize_business_name(employer)==normalize_business_name(company_name)
                name=value.get('name');title=value.get('jobTitle','');email=value.get('email','');profile=value.get('sameAs','')
                if isinstance(profile,list):profile=next((item for item in profile if isinstance(item,str) and item.startswith('https://')),'')
                if (affiliated or organization) and isinstance(name,str) and 2<=len(name.strip())<=150 and not any(ord(ch)<32 for ch in name):
                    identity=(name.strip().casefold(),title.casefold() if isinstance(title,str) else '')
                    if identity not in seen:
                        seen.add(identity);found.append({'name':name.strip(),'role':title[:150] if isinstance(title,str) else '', 'work_email':email.removeprefix('mailto:') if isinstance(email,str) else '', 'phone':value.get('telephone','') if isinstance(value.get('telephone',''),str) else '', 'profile_url':profile if isinstance(profile,str) else '', 'source_url':url,'evidence':json.dumps({'name':name,'jobTitle':title,'worksFor':employer or organization},ensure_ascii=False)[:3000]})
            for key,item in value.items():
                if isinstance(item,(dict,list)):walk(item,url,organization if key in ('employee','member','employees','members') else None,depth+1)
    for url,html in list(pages.items())[:3]:
        soup=BeautifulSoup(html[:500000],'html.parser')
        for script in soup.find_all('script',type='application/ld+json')[:20]:
            text=script.string or ''
            if len(text)>128000:continue
            try:walk(json.loads(text),url)
            except (ValueError,TypeError,RecursionError):continue
    return found
