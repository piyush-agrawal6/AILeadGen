"""Real scoped text/JSON/CSV exports with current-source retention enforcement."""
import csv,io,json,html
from fastapi import HTTPException
from .service import detail

def cell(value):
    from app.intent_radar.exports import safe_cell
    return safe_cell(value)

def render(c,key,format):
    data=detail(c,key)
    if not data['export_available']:raise HTTPException(409,'Finish generation and review current evidence before export.')
    from app.intent_radar.exports import Selection,snapshot
    authorized=snapshot(c,Selection(dataset='growth',parent=key));credits={r['id']:r.get('attribution','') for r in authorized['records']}
    output=data['output'];snapshot=data['snapshot'];evidence=snapshot.get('evidence',[])
    if format=='json':return json.dumps({'version':1,'title':data['title'],'output':output,'evidence':authorized['records']},indent=2,ensure_ascii=False),'application/json'
    if format=='csv':
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['Signal','Source','URL','Published/observed','Collected','Title','Evidence','Attribution'])
        for row in evidence:writer.writerow([cell(row[k]) for k in ('id','source','source_url','observed_at','retrieved_at','title','excerpt')]+[cell(credits[row['id']])])
        return stream.getvalue(),'text/csv'
    text=lambda value:html.escape(str(value)).replace('\n',' ')
    lines=['# '+text(data['title']),'','Prepared in PlaneByte · Growth Intelligence','',text(output.get('executive_summary','Source evidence review')),'','## Methodology and coverage','',text(snapshot.get('sampling','')),json.dumps(snapshot.get('coverage',{}),ensure_ascii=False),'','## Cited findings','']
    for item in output.get('findings',[]):
        lines.extend(['### '+text(item['section']),text(item['interpretation'])])
        for cite in item['citations']:lines.extend(['> '+text(cite['quote']),'Signal: '+str(cite['signal_id']),''])
    for theme in output.get('themes',[]):lines.extend(['### '+text(theme['name']),text(theme['description']),''])
    lines.extend(['## Limitations',*['- '+text(x) for x in output.get('limitations',[])],'','Collected discussion patterns are not verified market size, revenue, purchase probability or representative demand. AI text is an interpretation requiring review.','','## Original sources',''])
    for row in evidence:lines.extend([text(row['title']),row['source_url'],'> '+text(row['excerpt']),text(credits[row['id']]),''])
    return '\n'.join(lines),'text/markdown'
