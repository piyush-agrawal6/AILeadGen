"""Dedicated loopback browser acceptance; bootstrap only a fresh data/e2e fixture."""
from tests.intent_radar_fixture_server import app,path,PLANEBYTE_ORGANIZATION_ID
from app.database.connection import db_session
from app.database.prospects import now
from app.acquisition import sheets
from app.integrations import service,sheet_exports
from app.config.settings import get_settings
from uuid import uuid4

assert get_settings().app_env=='test'
get_settings().radar_actions_enabled=True

with db_session(path) as c:
    c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),PLANEBYTE_ORGANIZATION_ID,'Hacker News','990011','https://news.ycombinator.com/item?id=990011','Controlled export example','Fixture evidence only.',now(),now(),'Discussion',42,'{}'))

async def exchange(payload):
    assert get_settings().app_env=='test' and payload['code']=='offline-code'
    return {'access_token':'offline-access','refresh_token':'offline-refresh','expires_in':3600,'scope':service.WRITE_SCOPE}

async def read(token,path,params):
    assert token=='offline-access'
    if path.startswith('controlled-sheet-id/values/'):return {'range':path.split('/values/')[1],'values':[]}
    assert path=='controlled-sheet-id'
    return {'spreadsheetId':path,'properties':{'title':'QA only'},'sheets':[{'properties':{'title':'QA','gridProperties':{'rowCount':100,'columnCount':20}}}]}

sheets.token_request=exchange
sheets.read_with_token=read
# The normal worker refuses network in test mode. Inject only its HTTP transport.
import httpx
write=sheet_exports.write
async def write_fixture(token,sid,target,rows,transport=None,*,verify_read=False,before=None):
    assert sid=='controlled-sheet-id' and token=='offline-access'
    def response(req):
        if req.method=='GET' and req.url.params['valueRenderOption']=='FORMULA':return httpx.Response(200,json={'range':target})
        return httpx.Response(200,json={'values':rows} if req.method=='GET' else {'updatedCells':sum(map(len,rows))})
    return await write(token,sid,target,rows,httpx.MockTransport(response),verify_read=verify_read,before=before)
sheet_exports.write=write_fixture
