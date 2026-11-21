"""Bounded, workspace-owned export snapshots. Only explicit public fields leave the API."""
import csv
import hashlib
import io
import json
import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.intent_radar import service
from app.intent_radar.permissions import context
from app.intent_radar.source_policy import provider_policy

LIMIT = 100
FORMATS = Literal['csv', 'xlsx', 'json', 'pdf']
COLUMNS = ('id', 'signal_id', 'status', 'category', 'title', 'excerpt', 'source', 'source_url', 'observed_at', 'retrieved_at')
MIME = {'csv':'text/csv','json':'application/json','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','pdf':'application/pdf'}

class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset: Literal['signals','opportunities','monitor','saved','discovery','growth']
    ids: list[UUID] | None = Field(None, min_length=1, max_length=LIMIT)
    parent: UUID | None = None
    search: str = Field('',max_length=120)
    status: str = Field('',max_length=60)
    source: str = Field('',max_length=100)
    sort: Literal['newest','score','title'] = 'newest'
    list_filters:dict[str,str]|None=Field(None,max_length=16)

def safe_cell(value):
    text = str(value if value is not None else '')
    start = next((c for c in text if not c.isspace() and not unicodedata.category(c).startswith('C')), '')
    return "'" + text if start in ('=', '+', '-', '@') else text

def attribution(row):
    provenance=row.get('evidence',{}).get('provenance') or {};a=provenance.get('attribution')
    if not isinstance(a,dict):return ''
    return ' · '.join(str(x) for x in (a.get('author'),a.get('profile_url'),a.get('license'),provenance.get('repo'),provenance.get('author_handle')) if x)

def exportable(row, days):
    providers={'Hacker News':'hacker_news','GitHub':'github','Bluesky':'bluesky','Stack Exchange':'stack_exchange'}
    provider=providers.get(row['source'])
    if not provider:return False  # no implicit permission for unreviewed feed publishers
    policy=provider_policy(provider)
    if not row['available'] or not policy['capabilities']['export'] or service.expired(row,min(days,policy['retention_days'])):return False
    if provider=='hacker_news':return row['source_url']==f"https://news.ycombinator.com/item?id={row['source_record_id']}"
    prov=row.get('evidence',{}).get('provenance') or {};a=prov.get('attribution');url=urlsplit(row['source_url'])
    if url.scheme!='https' or url.username or url.password or not isinstance(a,dict) or not a.get('author') or not a.get('license'):return False
    if provider=='github':return url.hostname=='github.com' and prov.get('visibility')=='public' and bool(prov.get('repo'))
    if provider=='bluesky':return url.hostname=='bsky.app' and bool(prov.get('author_handle'))
    return prov.get('fetch_method')=='official_api' and bool(a.get('profile_url')) and a['license'].startswith('CC BY-SA')

def snapshot(c, selection):
    ctx=context(c); org=ctx.organization_id
    from app.billing.access_periods import require_current
    require_current(c,org)
    sel=selection; kind=sel.dataset
    if bool(sel.parent) != (kind in ('monitor','discovery','growth')):
        raise HTTPException(422,'Specify an owning monitor or discovery only for its results.')
    join=''; rid='s.id'; state='s.status'; where=['s.organization_id=?']; args=[org]
    if kind=='opportunities':
        join='JOIN intent_opportunities o ON o.organization_id=s.organization_id AND o.signal_id=s.id';rid='o.id';state='o.status'
    elif kind=='saved':join='JOIN intent_saved_signals b ON b.organization_id=s.organization_id AND b.signal_id=s.id'
    elif kind=='monitor':
        service.get(c,'monitors',str(sel.parent));join='JOIN intent_monitor_signals m ON m.organization_id=s.organization_id AND m.signal_id=s.id';where.append('m.monitor_id=?');args.append(str(sel.parent))
    ids=list(dict.fromkeys(map(str,sel.ids or [])))
    if sel.list_filters is not None:
        common={'search','sort'};allowed={'opportunities':common|{'status','priority','source','assigned_to'},'signals':common|{'status','source','category','min_score','view','buying_intent','icp_fit','from_date','to_date','monitor_id','discovery_id','saved'},'saved':common|{'collection'}}
        filters=dict(sel.list_filters)
        if ids or kind not in allowed or set(filters)-allowed[kind] or any(len(v)>254 for v in filters.values()):raise HTTPException(422,'Unsupported export filters.')
        if 'min_score' in filters:
            if not filters['min_score'].isdecimal() or len(filters['min_score'])>3 or int(filters['min_score'])>100:raise HTTPException(422,'Invalid minimum score.')
            filters['min_score']=int(filters['min_score'])
        page=service.saved(c,size=LIMIT,**filters) if kind=='saved' else service.listing(c,kind,size=LIMIT,**filters)
        if page['total']>LIMIT:raise HTTPException(422,'More than 100 results match. Narrow the filter.')
        ids=[r['signal_id' if kind=='saved' else 'id'] for r in page['items']]
        if not ids:raise HTTPException(422,'No matching records.')
    report=None
    if kind=='growth':
        from app.growth_intelligence.service import detail
        report=detail(c,str(sel.parent))
        if not report['export_available'] or ids or sel.search or sel.source or sel.status:raise HTTPException(409,'Select one completed, current report.')
        ids=list(dict.fromkeys(r['id'] for r in report['snapshot'].get('evidence',[])))
        if not 0<len(ids)<=LIMIT:raise HTTPException(422,'Report must have 1–100 evidence records.')
    if kind=='discovery':
        if not c.execute('SELECT d.id FROM intent_discoveries d LEFT JOIN intent_discovery_runs_meta m ON m.organization_id=d.organization_id AND m.discovery_id=d.id WHERE d.organization_id=? AND d.id=? AND m.deleted_at IS NULL',(org,str(sel.parent))).fetchone():raise HTTPException(404,'Discovery not found.')
        matches={key for row in c.execute('SELECT result_json FROM intent_source_runs WHERE organization_id=? AND discovery_id=?',(org,str(sel.parent))).fetchall() for key in json.loads(row[0]).get('signals',[])}
        if not set(ids)<=matches:raise HTTPException(404,'Selected results unavailable.')
        if not ids:
            if len(matches)>LIMIT:raise HTTPException(422,'Select at most 100 discovery results.')
            ids=sorted(matches)
        if not ids:raise HTTPException(422,'No matching discovery results.')
    if ids:where.append(rid+' IN ('+','.join('?' for _ in ids)+')');args.extend(ids)
    if sel.status:where.append(state+'=?');args.append(sel.status)
    if sel.source:where.append('s.source=?');args.append(sel.source)
    if sel.search:where.append('(LOWER(s.title) LIKE ? OR LOWER(s.excerpt) LIKE ?)');args.extend(['%'+sel.search.casefold()+'%']*2)
    order={'newest':'s.observed_at DESC','score':'s.score DESC','title':'s.title'}[sel.sort]
    rows=c.execute(f"SELECT s.*, {rid} AS record_id,{state} AS record_status FROM intent_signals s {join} WHERE {' AND '.join(where)} ORDER BY {order},s.id LIMIT ?",[*args,LIMIT+1]).fetchall()
    if len(rows)>LIMIT:raise HTTPException(422,'Export limit is 100 records. Narrow the filter or selection.')
    if ids and len(rows)!=len(ids):raise HTTPException(404,'Selected records unavailable.')
    if not rows:raise HTTPException(422,'No matching records.')
    days=service.preferences(c)['source_retention_days'];records=[]
    for row in rows:
        item=service.decode(row)
        if not exportable(item,days):raise HTTPException(409,'Selection contains expired or export-restricted evidence. Choose eligible records.')
        records.append({k:item[k] for k in COLUMNS if k not in ('signal_id','id','status')} | {'id':item['record_id'],'signal_id':item['id'],'status':item['record_status']})
        if item['source']!='Hacker News':records[-1]['attribution']=attribution(item)
    if sel.ids or sel.list_filters is not None:
        positions={str(k):i for i,k in enumerate(ids)};records.sort(key=lambda r:positions[r['id']])
    if report:
        for rec in records:rec.update(research_id=str(sel.parent),research_title=report['title'],research_summary=report['output'].get('executive_summary',''))
    body={'version':1,'dataset':kind,'records':records}; raw=json.dumps(body,sort_keys=True,ensure_ascii=False).encode()
    if len(raw)>512000:raise HTTPException(422,'Export exceeds 500 KiB. Narrow the selection.')
    return dict(body,identity=hashlib.sha256(raw).hexdigest(),workspace=org,actor=ctx.actor,selection=sel.model_dump(mode='json',exclude_none=True))

def columns(snap):return COLUMNS+(('attribution',) if any('attribution' in r for r in snap['records']) else ())+(('research_id','research_title','research_summary') if snap['dataset']=='growth' else ())

def serialize(snap,fmt):
    records=snap['records'];fields=columns(snap); rows=[[r.get(k,'') for k in fields] for r in records];out=io.BytesIO()
    if fmt=='json':return json.dumps({k:snap[k] for k in ('version','dataset','identity','records')},ensure_ascii=False).encode()
    if fmt=='csv':
        stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(fields);writer.writerows([safe_cell(v) for v in row] for row in rows);return stream.getvalue().encode('utf-8-sig')
    if fmt=='xlsx':
        from openpyxl import Workbook
        from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
        from openpyxl.utils import get_column_letter
        from datetime import timezone
        book=Workbook();sheet=book.active;sheet.title=snap['dataset'];sheet.append(fields);sheet.freeze_panes='A2'
        for row in rows:
            cells=[]
            for k,v in zip(fields,row):
                if len(str(v))>32767 or ILLEGAL_CHARACTERS_RE.search(str(v)):raise HTTPException(422,'Cell cannot be represented safely in Excel; choose JSON.')
                try:cell=datetime.fromisoformat(v).astimezone(timezone.utc).replace(tzinfo=None) if k.endswith('_at') else safe_cell(v)
                except (TypeError,ValueError,OverflowError):raise HTTPException(422,'Invalid source date. Choose JSON to inspect the original value.') from None
                cells.append(cell)
            sheet.append(cells)
        for i,k in enumerate(fields,1):sheet.column_dimensions[get_column_letter(i)].width=52 if k in ('title','excerpt','source_url') else 24
        sheet.auto_filter.ref=sheet.dimensions;book.save(out)
    elif fmt=='pdf':
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from app.reports.pdf import fonts,mark
        fonts();styles=getSampleStyleSheet()
        for name in ('Title','Heading2','Heading3'):styles[name].fontName='PBBold'
        styles['BodyText'].fontName='PBRegular'
        story=[Paragraph('PlaneByte | Intent Radar',styles['Title']),Paragraph(escape(snap['dataset'].title())+' — '+str(len(rows))+' records',styles['Heading2'])]
        if snap['dataset']=='growth':story.extend([Paragraph(escape(records[0]['research_title']),styles['Heading2']),Paragraph(escape(records[0]['research_summary']),styles['BodyText'])])
        for r in records:
            for k in ('title','excerpt','status','category','source','source_url','observed_at','retrieved_at','id')+(('attribution',) if 'attribution' in r else ()):
                story.append(Paragraph(escape(str(r[k])) if k=='title' else escape(k.replace('_',' ').title()+': '+str(r[k])),styles['Heading3' if k=='title' else 'BodyText']))
            story.append(Spacer(1,12))
        def footer(canvas,doc):
            canvas.saveState();mark(canvas,doc.leftMargin,24,18);canvas.setFont('PBRegular',8);canvas.drawString(doc.leftMargin+25,30,'PlaneByte research · '+str(doc.page));canvas.restoreState()
        SimpleDocTemplate(out,title='PlaneByte Intent Radar').build(story,onFirstPage=footer,onLaterPages=footer)
    else:raise ValueError('Unsupported format')
    return out.getvalue()
