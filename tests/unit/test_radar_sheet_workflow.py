import asyncio,uuid
from unittest.mock import AsyncMock
from urllib.parse import urlsplit,parse_qs
import httpx,pytest
from fastapi import HTTPException
from app.acquisition import sheets
from app.config.settings import get_settings
from app.integrations import service,radar_sheets,sheet_exports
from app.intent_radar.exports import Selection
from app.platform.context import workspace_scope
from test_customer_integrations import workspace,OWNER,TOKENS
from test_intent_radar import example

def test_review_write_once_and_reject_changed_evidence(workspace,monkeypatch):
    c,org,other,path=workspace;monkeypatch.setattr(get_settings(),'intent_radar_stage','Beta')
    c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(org,));c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(org,));c.commit()
    with workspace_scope(c,OWNER,org):
        state=parse_qs(urlsplit(service.authorize(c,write=True)['authorization_url']).query)['state'][0]
        monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=TOKENS|{'scope':service.WRITE_SCOPE}))
        conn=asyncio.run(service.connect(c,state,'review-code'));key=str(uuid.uuid4());s=example()
        c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,org,s['source'],s['source_record_id'],s['source_url'],'A title','A quote',s['observed_at'],s['observed_at'],'Discussion',2,'{}'))
        body=radar_sheets.Draft(selection=Selection(dataset='signals',ids=[key]),spreadsheet='disposable-test-sheet',sheet='Reviews',request_id=uuid.uuid4());j=radar_sheets.stage(c,conn['id'],body);assert j['row_count']==1 and j['target_range']=="'Reviews'!A1:J2";c.commit()
        sheet_exports.approve(c,j['id'],j['fingerprint'],'OVERWRITE_REVIEWED_RANGE');c.commit();calls=[]
        def receiver(req):
            calls.append(req);assert req.method=='PUT' and req.url.params['valueInputOption']=='RAW';return httpx.Response(200,json={'updatedCells':20})
        for _ in range(2):asyncio.run(sheet_exports.execute(j['id'],path,httpx.MockTransport(receiver)))
        assert len(calls)==1 and sheet_exports.owned(c,j['id'])['status']=='COMPLETED'
        pending=radar_sheets.stage(c,conn['id'],body.model_copy(update={'request_id':uuid.uuid4()}));c.execute("UPDATE intent_signals SET title='Changed' WHERE id=?",(key,));c.commit()
        with pytest.raises(HTTPException,match='Evidence changed'):sheet_exports.approve(c,pending['id'],pending['fingerprint'],'OVERWRITE_REVIEWED_RANGE')
    with workspace_scope(c,OWNER,other):
        with pytest.raises(HTTPException):sheet_exports.owned(c,j['id'])
