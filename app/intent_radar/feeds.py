"""One bounded RSS/Atom parser; display links never authorize network access."""
import hashlib,re
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

ATOM='http://www.w3.org/2005/Atom'
TOMBSTONES='http://purl.org/atompub/tombstones/1.0'
XMLBASE='{http://www.w3.org/XML/1998/namespace}base'

def reference(url,base=''):
    from app.utils.urls import is_safe_url
    result=urljoin(base,str(url or '').strip());p=urlsplit(result)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port not in (None,80 if p.scheme=='http' else 443) or not is_safe_url(result,check_dns=False):raise ValueError('A public source link is required.')
    query=urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.casefold().startswith('utm_') and k.casefold() not in ('gclid','fbclid')])
    return urlunsplit((p.scheme,p.hostname,p.path or '/',query,p.fragment))

def plain(value,limit=3000):
    soup=BeautifulSoup(str(value or '')[:50000],'html.parser')
    for element in list(soup.find_all(True)):
        if element.name and element.name.rsplit(':',1)[-1].casefold() in ('script','style','template','iframe','object','svg'):element.decompose()
    return re.sub(r'\s+',' ',soup.get_text(' ',strip=True)).strip()[:limit]

def local(node):return node.tag.rsplit('}',1)[-1] if isinstance(node.tag,str) else ''
def children(node,name):return [child for child in node if local(child)==name]
def first(node,name):return next(iter(children(node,name)),None)
def value(node,name):
    child=first(node,name)
    return ' '.join(child.itertext()).strip() if child is not None else ''
def instant(value):
    if not value:return None
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00')) if re.match(r'^\d{4}-\d\d-\d\d',value) else parsedate_to_datetime(value)
        return stamp.astimezone(timezone.utc).isoformat() if stamp.tzinfo else None
    except (ValueError,TypeError,OverflowError):return None

def parse(content,config,normalize):
    if not isinstance(content,bytes) or len(content)>500000:raise ValueError('Unsafe or oversized feed.')
    try:text=content.decode('utf-16' if content.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:raise ValueError('Unsupported feed encoding.') from None
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b',text,re.I):raise ValueError('Unsafe feed declarations.')
    try:root=ET.fromstring(text)
    except ET.ParseError:raise ValueError('Malformed feed.') from None
    nodes=list(root.iter())
    if len(nodes)>5000:raise ValueError('Feed exceeds the XML node limit.')
    stack=[(root,0)]
    while stack:
        node,depth=stack.pop()
        if depth>32:raise ValueError('Feed exceeds the XML nesting limit.')
        stack.extend((child,depth+1) for child in node)
    atom=root.tag=='{'+ATOM+'}feed'
    if atom:entries=[x for x in root if x.tag=='{'+ATOM+'}entry']
    elif local(root)=='rss':
        channel=first(root,'channel');entries=children(channel,'item') if channel is not None else []
    elif root.tag=='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF':entries=children(root,'item')
    else:raise ValueError('Document is not a supported RSS or Atom feed.')
    base=urljoin(config.get('endpoint',''),root.attrib.get(XMLBASE,''));source='Approved Discourse' if config['family']=='discourse' else 'RSS / Atom'
    self_link=None
    for candidate in root:
        if local(candidate)=='link' and candidate.attrib.get('rel')=='self' and candidate.attrib.get('href'):
            try:self_link=reference(candidate.attrib['href'],base)
            except (ValueError,TypeError):pass
            if self_link:break
    items=[]
    for native in entries[:40]:
        item_base=urljoin(base,native.attrib.get(XMLBASE,''))
        link=value(native,'link') if not atom else ''
        if atom:link=next((x.attrib.get('href','') for x in children(native,'link') if x.attrib.get('rel','alternate')=='alternate' and x.attrib.get('type','text/html') in ('text/html','application/xhtml+xml','')),'')
        guid=value(native,'guid') or value(native,'id') or link
        if not guid or len(guid)>2000:continue
        if not link and not atom:
            raw=first(native,'guid')
            if raw is not None and raw.attrib.get('isPermaLink','true').lower()!='false':link=guid
        try:link=reference(link,item_base)
        except (ValueError,TypeError):continue
        published=instant(value(native,'published') or value(native,'pubDate') or value(native,'date'))
        updated=instant(value(native,'updated')) or published
        observed=published or updated
        if not observed:continue
        content_node=first(native,'content')
        body=value(native,'summary') or value(native,'description')
        if content_node is not None and not content_node.attrib.get('src'):
            body=ET.tostring(content_node,encoding='unicode') if content_node.attrib.get('type')=='xhtml' else ' '.join(content_node.itertext())
        elif value(native,'encoded'):body=value(native,'encoded')
        authors=[]
        for author in children(native,'author') or children(root,'author'):
            name=plain(value(author,'name') if atom else ' '.join(author.itertext()),100)
            if '@' in name:name=re.sub(r'\S+@\S+','',name).strip(' ()')
            if name and name not in authors:authors.append(name)
        creator=plain(value(native,'creator'),100)
        if creator and '@' not in creator and creator not in authors:authors.append(creator)
        categories=list(dict.fromkeys(plain(x.attrib.get('term') or ' '.join(x.itertext()),100) for x in children(native,'category')))[:10]
        metadata={'feed_id':config['id'],'feed_name':config['name'],'attribution':config['attribution'],'policy_reference':config['policy_reference'],'retention_days':config['retention_days'],'fetch_method':'public_feed','feed_format':'atom' if atom else 'rss','categories':[x for x in categories if x],'feed_authors':authors[:10],'updated_at':updated,'published_at':published,'observed_time_basis':'published' if published else 'updated','feed_self_url':self_link,'declared_feed_language':next((' '.join(x.itertext())[:30] for x in nodes if local(x)=='language'),None)}
        if config.get('content_kind'):metadata['content_kind']=config['content_kind']
        item=normalize(source,config['id']+':'+hashlib.sha256(guid.encode()).hexdigest(),link,plain(value(native,'title'),300),plain(body),observed,**metadata)
        if item:items.append(item)
    # RFC6721 tombstones are explicit removals; a rotated feed window is not.
    if atom:
        for tombstone in [x for x in root if x.tag=='{'+TOMBSTONES+'}deleted-entry'][:40]:
            ref=tombstone.attrib.get('ref','')
            if ref and len(ref)<=2000:items.append({'source':source,'source_record_id':config['id']+':'+hashlib.sha256(ref.encode()).hexdigest(),'removed':True})
    return items
