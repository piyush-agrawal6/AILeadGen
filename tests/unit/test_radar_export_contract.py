import csv,io,json
import pytest
from fastapi import HTTPException
from openpyxl import load_workbook
from pypdf import PdfReader
from app.intent_radar import exports
from app.platform.context import workspace_scope
from test_intent_radar import radar, owned, example
from uuid import uuid4

def test_all_file_encodings_and_fences(radar):
    c,_,org,other=radar;key=str(uuid4());s=example();title=' \t=1+2, "quoted"\nCafé'
    c.execute("INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(key,org,s['source'],s['source_record_id'],s['source_url'],title,'permitted text',s['observed_at'],s['observed_at'],'Discussion',1,'{}'))
    selection=exports.Selection(dataset='signals',ids=[key])
    with workspace_scope(c,'controlled@example.test',org):
        snap=exports.snapshot(c,selection)
        csvrow=list(csv.DictReader(io.StringIO(exports.serialize(snap,'csv').decode('utf-8-sig'))))[0];assert csvrow['title']=="'"+title
        book=load_workbook(io.BytesIO(exports.serialize(snap,'xlsx')));assert book.active['E2'].value=="'"+title and book.active['I2'].is_date
        assert 'permitted text' in PdfReader(io.BytesIO(exports.serialize(snap,'pdf'))).pages[0].extract_text()
        assert json.loads(exports.serialize(snap,'json'))['records'][0]['source_url']==s['source_url']
        assert exports.snapshot(c,exports.Selection(dataset='signals',search='quoted'))['identity']==snap['identity']
        c.execute('UPDATE intent_signals SET available=0 WHERE id=?',(key,))
        with pytest.raises(HTTPException,match='restricted'):exports.snapshot(c,selection)
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):exports.snapshot(c,selection)

def test_limit_and_provider_forbidden_are_explicit(radar):
    c,_,org,_=radar;s=example()
    with workspace_scope(c,'controlled@example.test',org):
        for i in range(101):
            c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),org,'YouTube',str(i),'https://www.youtube.com',str(i),'restricted',s['observed_at'],s['observed_at'],'Discussion',5,'{}'))
        with pytest.raises(HTTPException,match='100'):exports.snapshot(c,exports.Selection(dataset='signals'))
        with pytest.raises(HTTPException,match='restricted'):exports.snapshot(c,exports.Selection(dataset='signals',search='100'))

@pytest.mark.parametrize('text',['\x00\t=SUM(A1)','\n @demo','\ufeff+1',' \r-2'])
def test_inert_cells(text):assert exports.safe_cell(text)=="'"+text
