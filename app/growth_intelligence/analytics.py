"""Bounded analytics over authorized collected evidence, never market-size claims."""
import hashlib,json,math,re,unicodedata
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from fastapi import HTTPException
from app.config.settings import get_settings
from app.intent_radar.permissions import context
from app.intent_radar import service
from .models import Scope

VERSION='GROWTH_EVIDENCE_V1'
LIMIT=1000
STOP=set('the a an and or of to in on for is are with from that this i we our you your it as at be have has was can how what which not'.split())

def access(c,write=False,manager=False):
    if not get_settings().intent_radar_growth_enabled:raise HTTPException(404,'Growth Intelligence is unavailable.')
    return context(c,write,manager)

def instant(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None

def tokens(text):
    return [s for s in re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold(),re.UNICODE) if len(s)>2 and s not in STOP]

def canonical_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),urlencode(sorted((k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('ref','source'))),''))

def dedupe(rows):
    result=[];seen={};duplicates=0
    for item in rows:
        evidence=item.get('evidence',{});discussion=evidence.get('discussion_id')
        body=' '.join(tokens(item['title']+' '+item['excerpt']))
        key=('discussion:'+item['source']+':'+str(discussion)) if discussion else canonical_url(item['source_url'])
        fingerprint=hashlib.sha256(body.encode()).hexdigest() if len(body)>80 else None
        match=seen.get(key) or (seen.get('body:'+fingerprint) if fingerprint else None)
        if match:
            match['duplicate_source_ids'].append(item['id']);duplicates+=1;continue
        item={**item,'duplicate_source_ids':[],'conversation_key':key}
        seen[key]=item
        if fingerprint:seen['body:'+fingerprint]=item
        result.append(item)
    return result,duplicates

def evidence(c,scope:Scope,as_of=None):
    org=access(c).organization_id;end=as_of or datetime.now(timezone.utc);days=scope.days or 7
    start=end-timedelta(days=days);previous=start-timedelta(days=days)
    where=['organization_id=?','available=1','observed_at>=?','observed_at<?',service.rank_expression()+'>=?'];args=[org,previous.isoformat(),end.isoformat(),scope.min_score]
    if scope.sources:where.append('source IN ('+','.join('?' for _ in scope.sources)+')');args.extend(scope.sources)
    if scope.search:where.append('(LOWER(title) LIKE ? OR LOWER(excerpt) LIKE ?)');args.extend(['%'+scope.search.casefold()+'%']*2)
    if scope.icp_id:
        from app.icp.service import get
        get(c,str(scope.icp_id))
    if scope.theme_ids:
        marks=','.join('?' for _ in scope.theme_ids);ids=list(map(str,scope.theme_ids))
        if c.execute('SELECT COUNT(*) FROM growth_themes WHERE organization_id=? AND id IN ('+marks+')',[org,*ids]).fetchone()[0]!=len(set(ids)):raise HTTPException(404,'Theme not found.')
        where.append('id IN (SELECT signal_id FROM growth_theme_signals WHERE organization_id=? AND theme_id IN ('+marks+'))');args.extend([org,*ids])
    competitor=None
    if scope.competitor_id:
        r=c.execute('SELECT * FROM growth_competitors WHERE organization_id=? AND id=? AND archived_at IS NULL',(org,str(scope.competitor_id))).fetchone()
        if not r:raise HTTPException(404,'Competitor not found.')
        competitor=dict(r);terms=[r['name'],*json.loads(r['aliases_json'])]
        where.append('('+' OR '.join('(LOWER(title) LIKE ? OR LOWER(excerpt) LIKE ?)' for _ in terms)+')')
        for term in terms:args.extend(['%'+term.casefold()+'%']*2)
    language_sql=",(SELECT analysis_json FROM intent_analyses a WHERE a.organization_id=intent_signals.organization_id AND a.signal_id=intent_signals.id ORDER BY a.created_at DESC,a.id DESC LIMIT 1) AS language_analysis" if scope.language!='any' else ''
    rows=c.execute('SELECT *, '+service.rank_expression()+' AS current_score'+language_sql+' FROM intent_signals WHERE '+' AND '.join(where)+' ORDER BY observed_at DESC,id LIMIT ?',[*args,LIMIT+1]).fetchall()
    preferences=service.preferences(c);valid=[]
    for r in rows[:LIMIT]:
        item=dict(r);item['evidence']=json.loads(item.pop('evidence_json'));item['score']=item.pop('current_score')
        if service.expired(item,preferences['source_retention_days']):continue
        if scope.language!='any':
            # A quote-validated existing interpretation supplies language; Unicode
            # or location guesses alone never grant a language/geography filter.
            analysis=item.pop('language_analysis',None)
            data=json.loads(analysis).get('interpretation') if analysis else None
            if not data or data.get('detected_language')!=scope.language or not data.get('language_evidence') or data['language_evidence'] not in item['title']+'\n'+item['excerpt']:continue
        if competitor:
            terms=[competitor['name'],*json.loads(competitor['aliases_json'])]
            if not any(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',item['title']+'\n'+item['excerpt'],re.I) for t in terms):continue
        valid.append(item)
    unique,duplicates=dedupe(valid)
    runs=[dict(r) for r in c.execute('SELECT provider,status,updated_at,result_json FROM intent_source_runs WHERE organization_id=? AND updated_at>=? AND updated_at<? ORDER BY updated_at LIMIT 1001',(org,previous.isoformat(),end.isoformat())).fetchall()]
    if scope.sources:
        family={'Hacker News':'hacker_news','Stack Exchange':'stack_exchange','RSS / Atom':'rss','Approved Discourse':'discourse'}
        selected={family[name] for name in scope.sources if name in family}
        runs=[r for r in runs if r['provider'] in selected]
    source_where='organization_id=?'+(' AND source IN ('+','.join('?' for _ in scope.sources)+')' if scope.sources else '')
    source_first=c.execute('SELECT MIN(retrieved_at) FROM intent_signals WHERE '+source_where,[org,*scope.sources]).fetchone()[0]
    current=[r for r in unique if instant(r['observed_at']) and instant(r['observed_at'])>=start]
    prior=[r for r in unique if instant(r['observed_at']) and instant(r['observed_at'])<start]
    def configurations(a,b):
        rows=c.execute('SELECT configuration_json FROM intent_discoveries WHERE organization_id=? AND created_at>=? AND created_at<? ORDER BY created_at LIMIT 1001',(org,a.isoformat(),b.isoformat())).fetchall()
        return {hashlib.sha256(r[0].encode()).hexdigest() for r in rows},len(rows)
    old_configs,old_n=configurations(previous,start);new_configs,new_n=configurations(start,end)
    successes=lambda a,b:sum(r['status'] in ('COMPLETE','NO_RESULTS') and a<=instant(r['updated_at'])<b for r in runs if instant(r['updated_at']))
    old_checks=successes(previous,start);new_checks=successes(start,end)
    source_error=any(r['status'] not in ('COMPLETE','NO_RESULTS') for r in runs)
    enough_span=bool(instant(source_first) and instant(source_first)<=previous)
    comparable=bool(enough_span and old_checks>=2 and new_checks>=2 and old_configs==new_configs and old_configs and max(old_n,new_n)<=1.25*max(1,min(old_n,new_n)) and not source_error and len(rows)<=LIMIT and len(runs)<=1000)
    supported={str(d):bool(instant(source_first) and instant(source_first)<=end-timedelta(days=d)) for d in (7,30,90)}
    coverage={'current_checks':new_checks,'previous_checks':old_checks,'comparable':comparable,'source_errors':source_error,'configuration_changed':old_configs!=new_configs,'collection_started_at':source_first,'windows_supported':supported,'truncated':len(rows)>LIMIT or len(runs)>1000,'limit':LIMIT,'duplicates_excluded':duplicates,'scope':'Collected discussions only; not a representative market sample.','time_basis':'Original publication timestamp where supplied by source; ingestion timestamps establish collection coverage.'}
    if scope.days and not supported[str(scope.days)]:raise HTTPException(422,'That time window is not supported by collected history. Use available evidence.')
    digest=hashlib.sha256(json.dumps([[r[k] for k in ('id','title','excerpt','revision','score','source','source_url','observed_at','retrieved_at','evidence')] for r in unique],sort_keys=True).encode()).hexdigest()
    return {'items':current,'previous':prior,'coverage':coverage,'as_of':end.isoformat(),'start':start.isoformat(),'previous_start':previous.isoformat(),'input_hash':digest}

def comparison(current,previous,coverage):
    enough=coverage['comparable'] and current>=5 and previous>=5
    if not coverage['comparable']:state='Insufficient comparable coverage'
    elif current>=5 and previous==0:state='Newly observed in this collection'
    elif not enough:state='Small sample — review evidence'
    elif current>previous:state='Increasing collected mentions'
    elif current<previous:state='Declining collected mentions'
    else:state='Stable collected mentions'
    return {'current':current,'previous':previous,'state':state,'percentage_change':round((current-previous)*100/previous,1) if enough else None,'market_trend_proven':False,'minimum_sample_per_period':5}

def lexical_groups(items):
    docs=[set(tokens(r['title']+' '+r['excerpt'][:600])) for r in items];df=Counter(t for d in docs for t in d)
    groups=[]
    for item,words in zip(items,docs):
        best=None;value=0
        for group in groups:
            common=words&group['terms'];den=len(words|group['terms']) or 1
            score=len(common)/den
            if score>value:best=group;value=score
        if best and value>=.16:best['items'].append(item);best['terms']|=words
        else:groups.append({'items':[item],'terms':set(words)})
    result=[]
    for group in sorted(groups,key=lambda g:len(g['items']),reverse=True)[:8]:
        weights=Counter(t for r in group['items'] for t in tokens(r['title']))
        terms=[t for t,_ in sorted(weights.items(),key=lambda x:-(x[1]*(math.log((len(items)+1)/(df[x[0]]+1))+1)))[:4]]
        if not terms:continue
        result.append({'name':' · '.join(terms).capitalize(),'description':'Provisional lexical grouping from the cited discussions; semantic interpretation has not been verified.','citations':[{'signal_id':r['id'],'quote':(r['excerpt'] or r['title'])[:300]} for r in group['items'][:12]]})
    return result

def overview(c,scope):
    data=evidence(c,scope);items=data['items'];org=access(c).organization_id
    daily=Counter(r['observed_at'][:10] for r in items);categories=Counter(r['category'] for r in items)
    from .service import themes as theme_listing
    themes=theme_listing(c,size=25)['items']
    return {'sample_size':len(items),'comparison':comparison(len(items),len(data['previous']),data['coverage']),'coverage':data['coverage'],'as_of':data['as_of'],'sources':dict(Counter(r['source'] for r in items)),'categories':dict(categories),'daily':[{'day':d,'conversations':n} for d,n in sorted(daily.items())],'themes':themes,'monitored_topics':c.execute("SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active'",(org,)).fetchone()[0],'opportunity_candidates':sum(r['score']>=45 for r in items),'freshest_evidence':max((r['retrieved_at'] for r in items),default=None),'signals':[{k:r[k] for k in ('id','title','source','source_url','observed_at','retrieved_at','score','category')} for r in items[:25]],'geography':'Unknown unless explicitly evidenced; no inferred country filter.'}
