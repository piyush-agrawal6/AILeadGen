"""Read-only acceptance evidence export from the approved disposable runtime."""
import argparse,json,sys,time,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.platform.context import workspace_scope
from app.intent_radar import service,intelligence

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',required=True);args=parser.parse_args()
path=Path(args.database).resolve();base=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
assert path.is_relative_to(base) and path.name.startswith('intent-radar-23-') and path.suffix=='.db' and path.is_file()
s=get_settings();s.app_env='test';s.database_path=str(path);s.database_url='';s.intent_radar_stage='Beta';s.allowed_user_emails='radar23@example.test'
c=get_connection(path);owner=c.execute("SELECT id,created_by_user_id FROM organizations WHERE name='Disposable Radar 23 acceptance'").fetchone();assert owner
with workspace_scope(c,owner['created_by_user_id'],owner['id']):
    analyses=[]
    for row in c.execute('SELECT DISTINCT signal_id FROM intent_analyses WHERE organization_id=? LIMIT 10',(owner['id'],)).fetchall():
        signal=service.get(c,'signals',row['signal_id']);history=intelligence.history(c,signal['id'])
        analyses.append({'signal_id':signal['id'],'source_url':signal['source_url'],'source_title':signal['title'],'valid_analyses':history['items']})
    samples=[]
    for source in ('Hacker News','Stack Exchange','RSS / Atom','Approved Discourse'):
        row=c.execute('SELECT id FROM intent_signals WHERE organization_id=? AND source=? AND available=1 ORDER BY id LIMIT 1',(owner['id'],source)).fetchone()
        if row:
            item=service.get(c,'signals',row['id']);samples.append({'source':source,'title':item['title'],'url':item['source_url'],'excerpt':item['excerpt'][:700],'published_at':item['observed_at'],'attribution':item['evidence'].get('provenance',{}).get('attribution')})
    counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('businesses','contact_people','workflow_runs','email_messages')}
    assert all(value==0 for value in counts.values())
    metrics={}
    if samples:
        key=c.execute('SELECT id FROM intent_signals WHERE organization_id=? AND available=1 LIMIT 1',(owner['id'],)).fetchone()[0]
        statements=[0];c.set_trace_callback(lambda _:statements.__setitem__(0,statements[0]+1));latencies=[]
        for _ in range(50):
            start=time.perf_counter();signal=service.get(c,'signals',key);latencies.append((time.perf_counter()-start)*1000)
        c.set_trace_callback(None)
        from app.intent_radar.connectors import normalized
        start=time.perf_counter()
        for _ in range(1000):assert normalized(signal['source'],signal['source_record_id'],signal['source_url'],signal['title'],signal['excerpt'],signal['observed_at'])
        elapsed=time.perf_counter()-start
        metrics={'signal_detail_samples':50,'signal_detail_median_ms':round(statistics.median(latencies),3),'signal_detail_p95_ms':round(sorted(latencies)[47],3),'signal_detail_sql_statements':statements[0],'normalization_items':1000,'normalization_seconds':round(elapsed,4),'normalization_items_per_second':round(1000/elapsed),'scope':'Local SQLite, warm process, actual membership checks; CPU replay of genuine evidence, no external requests or scalability claim'}
    print(json.dumps({'lead_engine_and_mail_counts':counts,'analyses':analyses,'review_samples':samples,'monitors':service.listing(c,'monitors')['items'],'usage':__import__('app.intent_radar.discovery',fromlist=['usage']).usage(c),'performance':metrics},indent=2,default=str))
c.close()
