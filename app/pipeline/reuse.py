"""Canonical analysis reuse; campaign evidence remains in immutable snapshots."""
import base64,hashlib,json,zlib
from datetime import datetime,timedelta,timezone
from app.database.foundation_schema import ready
from app.workflows.history import encoded

WINDOWS={'contacts':7,'crawl':7,'website':7,'seo':7,'security':7,'social':7,'lighthouse':14}
VERSION='foundation-1'

def fingerprint(probe,analyzer):
    if not probe or not probe.reachable or not probe.html_content:return None
    value={'url':probe.final_url,'status':probe.http_status,'html':hashlib.sha256(probe.html_content.encode()).hexdigest()}
    if analyzer=='security':
        value={**value,'headers':{k.lower():v for k,v in probe.response_headers.items() if k.lower() in ('strict-transport-security','content-security-policy','x-frame-options','x-content-type-options','referrer-policy','permissions-policy','server','x-powered-by')},'cookies':sorted(probe.cookies),'certificate_valid':probe.certificate_valid,'https':probe.https_enabled,'redirects_https':probe.http_redirects_https}
    return hashlib.sha256(encoded(value).encode()).hexdigest()

def dump_crawl(result):
    value=dict(vars(result));value['all_links']=sorted(result.all_links);value['contacts']=vars(result.contacts)
    return base64.b64encode(zlib.compress(encoded(value).encode())).decode()

def load_crawl(value):
    from app.enrichment.crawler import CrawlResult
    from app.enrichment.contacts import ExtractedContacts
    # Compressed payload is application-generated and bounded again on read.
    decoder=zlib.decompressobj();raw=decoder.decompress(base64.b64decode(value),32_000_000)
    if not decoder.eof:raise ValueError('Crawl cache exceeds safe size')
    data=json.loads(raw);result=CrawlResult(data['start_url']);contact=ExtractedContacts()
    for k,v in data.pop('contacts').items():setattr(contact,k,v)
    result.__dict__.update(data);result.contacts=contact;result.all_links=set(result.all_links)
    return result

class AnalysisReuse:
    def __init__(self,c,run_id,configuration):
        self.c=c;self.run_id=run_id;self.options=configuration or {};self.enabled=ready(c)
        self.mode=self.options.get('analysis_mode','INCREMENTAL');self.pending={};self.operations={};self.entries={};self.pids={}
        relevant={k:self.options.get(k) for k in ('crawler','auditing','social','vertical','opportunities')}
        self.configuration_hash=hashlib.sha256(encoded([VERSION,relevant]).encode()).hexdigest()
        groups={'crawl':('crawler',),'contacts':('crawler',),'website':('crawler','auditing','vertical'),'seo':('crawler','auditing','vertical'),'security':(),'social':('crawler','social'),'lighthouse':('auditing',)}
        from app.scoring.opportunities import SCORING_VERSION
        self.hashes={kind:hashlib.sha256(encoded([VERSION,SCORING_VERSION,{k:self.options.get(k) for k in keys}]).encode()).hexdigest() for kind,keys in groups.items()}
        self.windows={**WINDOWS,**self.options.get('reuse_windows',{})}
        if self.enabled:
            self.pids={r['id']:r['prospect_id'] for r in c.execute('SELECT id,prospect_id FROM businesses WHERE run_id=?',(run_id,)).fetchall()}
            self.entries={(r['prospect_id'],r['analyzer']):dict(r) for r in c.execute('SELECT a.* FROM analysis_cache a WHERE a.prospect_id IN (SELECT prospect_id FROM businesses WHERE run_id=?)',(run_id,)).fetchall()}

    def get(self,b,analyzer,probe):
        if not self.enabled or self.mode=='FULL':return None
        row=self.entries.get((self.pids.get(b.id),analyzer));fp=fingerprint(probe,analyzer)
        if not row or not fp or row['fingerprint']!=fp or row['configuration_hash']!=self.hashes[analyzer]:return None
        expiry=datetime.fromisoformat(row['expires_at']).replace(tzinfo=timezone.utc)
        expiry=min(expiry,datetime.fromisoformat(row['analyzed_at']).replace(tzinfo=timezone.utc)+timedelta(days=self.windows[analyzer]))
        if expiry<=datetime.now(timezone.utc):return None
        try:result=json.loads(row['payload_json'])
        except (ValueError,TypeError):return None
        self.operation(b,analyzer,'REUSED');return result

    def operation(self,b,analyzer,operation):
        if self.enabled:self.operations[(b.id,analyzer)]=(self.run_id,b.id,analyzer,operation,datetime.now(timezone.utc).isoformat())

    def put(self,b,analyzer,probe,payload):
        pid=self.pids.get(b.id);fp=fingerprint(probe,analyzer)
        self.operation(b,analyzer,'REFRESHED' if (pid,analyzer) in self.entries else 'NEW')
        if not self.enabled or not pid or not fp:return
        value=encoded(payload)
        if len(value.encode())>2_000_000:return
        stamp=datetime.now(timezone.utc);expiry=stamp+timedelta(days=self.windows[analyzer])
        self.pending[(pid,analyzer)]=(pid,analyzer,b.id,fp,self.hashes[analyzer],value,stamp.isoformat(),expiry.isoformat())

    def flush(self):
        if not self.enabled:return
        if self.pending:
            self.c.executemany('''INSERT INTO analysis_cache(prospect_id,analyzer,source_business_id,fingerprint,configuration_hash,payload_json,analyzed_at,expires_at)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(prospect_id,analyzer) DO UPDATE SET source_business_id=excluded.source_business_id,fingerprint=excluded.fingerprint,configuration_hash=excluded.configuration_hash,payload_json=excluded.payload_json,analyzed_at=excluded.analyzed_at,expires_at=excluded.expires_at''',list(self.pending.values()))
        if self.operations:
            self.c.executemany('INSERT INTO analysis_operations(run_id,business_id,analyzer,operation,recorded_at) VALUES(?,?,?,?,?) ON CONFLICT(run_id,business_id,analyzer) DO NOTHING',list(self.operations.values()))
        self.pending.clear();self.operations.clear()

def efficiency(c,cid):
    rows=[dict(r) for r in c.execute('SELECT a.analyzer,a.operation,COUNT(*) count FROM analysis_operations a JOIN pipeline_runs r ON r.id=a.run_id WHERE r.campaign_id=? GROUP BY a.analyzer,a.operation',(cid,)).fetchall()]
    total=sum(r['count'] for r in rows);reused=sum(r['count'] for r in rows if r['operation']=='REUSED')
    businesses=dict(c.execute('''SELECT COUNT(DISTINCT b.prospect_id) discovered,
      COUNT(DISTINCT CASE WHEN p.first_campaign_id=? THEN p.id ELSE NULL END) new_businesses
      FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id JOIN prospects p ON p.id=b.prospect_id WHERE r.campaign_id=?''',(cid,cid)).fetchone())
    businesses['existing_businesses']=businesses['discovered']-businesses['new_businesses']
    runtime=c.execute('SELECT SUM(a.runtime_seconds) FROM worker_attempts a JOIN pipeline_runs r ON r.id=a.run_id WHERE r.campaign_id=?',(cid,)).fetchone()[0]
    return {'operations':rows,'total':total,'reused':reused,'refreshed_or_new':total-reused,'reuse_rate':round(100*reused/total,1) if total else None,'fresh_analysis_rate':round(100*(total-reused)/total,1) if total else None,'worker_runtime_seconds':runtime,**businesses,'scope':'Recorded analyzer operations; unavailable for historical runs before schema 12.'}
