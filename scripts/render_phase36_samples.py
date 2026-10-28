"""Render three stored business examples plus an explicitly labeled mid-market layout fixture."""
import copy
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.database.prospects import now
from app.reports.data import client_snapshot
from app.reports.pdf import render_pdf
from pypdf import PdfReader
result={}
with db_session() as c:
    samples={kind:client_snapshot(c,bid,now()) for kind,bid in [('reachable',3953),('no-website',5446),('unreachable',3918)]}
samples['mid-market']=copy.deepcopy(samples['reachable']);samples['mid-market']['business']['name']='Mid-market layout QA - 15-location example';samples['mid-market']['business_scale']='MID_MARKET'
for kind,snapshot in samples.items():
    output=Path('output/pdf')/f'planebyte-phase36-{kind}.pdf';render_pdf(snapshot,output)
    pages=PdfReader(output).pages;text='\n'.join(p.extract_text() for p in pages)
    assert 'LeadEngine' not in text
    assert 'Recommended delivery roadmap' in text and 'Included services' in text
    if kind in ('no-website','unreachable'):assert 'CURRENT SCORE' not in text and 'Target gain:' not in text
    result[kind]={'pages':len(pages),'bytes':output.stat().st_size,'mode':snapshot['mode'],'mid_market_fixture':kind=='mid-market'}
Path('docs/phase36-pdf-qa.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
