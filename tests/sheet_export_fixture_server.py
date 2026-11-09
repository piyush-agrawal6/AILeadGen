"""Isolated browser fixture: real domain APIs and worker, synthetic Google only."""
import httpx
from app.config.settings import get_settings
assert get_settings().app_env=='test','This fixture must never run outside tests.'
from app.acquisition import sheets
from app.integrations import service,sheet_exports
from app.api.server import app

async def exchange(data):
    code=data.get('code','')
    assert code in ('controlled-read-code','controlled-export-code')
    return {'access_token':'synthetic-browser-access','refresh_token':'synthetic-browser-refresh','expires_in':3600,'scope':service.WRITE_SCOPE if code=='controlled-export-code' else sheets.SCOPE}
sheets.token_request=exchange
original=sheet_exports.write
async def write(token,sid,target,rows,transport=None):
    assert token=='synthetic-browser-access' and sid=='controlled-sheet-id'
    def receiver(request):
        assert request.method=='PUT' and request.url.host=='sheets.googleapis.com' and request.url.params['valueInputOption']=='RAW'
        return httpx.Response(200,json={'updatedCells':sum(len(row) for row in rows)})
    return await original(token,sid,target,rows,httpx.MockTransport(receiver))
sheet_exports.write=write
