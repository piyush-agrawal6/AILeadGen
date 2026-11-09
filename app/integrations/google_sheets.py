"""Customer Sheets reads/imports through the existing bounded transport and pipeline."""
import asyncio,json
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from app.acquisition import sheets
from app.platform.context import current,organization
from app.database.prospects import now
from app.integrations import service


def reader_for(key,expected_revision=None,*,importing=False):
    async def reader(connection,actor,path,params):
        service.manager(connection)
        if importing:
            from app.acquisition.config import require
            require('import',connection);require('sheets',connection)
        row=service.owned(connection,key)
        if row['provider']!=service.PROVIDER:raise HTTPException(404,'Spreadsheet connection not found.')
        if expected_revision is not None and row['revision']!=expected_revision:raise HTTPException(409,'The spreadsheet connection changed after review. Stage a new import.')
        token,revision=await service.access_token(connection,key)
        try:result=await asyncio.wait_for(sheets.read_with_token(token,path,params),timeout=30)
        except (sheets.SheetsUnavailable,TimeoutError):
            service.manager(connection);latest=service.owned(connection,key)
            if latest['revision']==revision:service.provider_error(connection,latest,'SHEETS_READ_UNAVAILABLE')
            raise HTTPException(503,'The spreadsheet could not be read. Check this connection and the spreadsheet permissions.') from None
        service.manager(connection);latest=service.owned(connection,key)
        if latest['status']!='CONNECTED' or latest['revision']!=revision:raise HTTPException(409,'Connection changed while reading. Reload before retrying.')
        connection.execute('UPDATE organization_integrations SET last_success_at=?,last_error_code=NULL WHERE id=? AND organization_id=? AND revision=?',(now(),key,organization(),revision));connection.commit()
        return result
    return reader


async def metadata(c,key,spreadsheet):
    service.manager(c);row=service.owned(c,key)
    return await sheets.metadata(c,current().actor,spreadsheet,reader=reader_for(key,row['revision']))


async def stage_import(c,key,spreadsheet,tab,request_id):
    from app.acquisition.config import require
    from app.acquisition import service as acquisition
    service.manager(c);require('import',c);require('sheets',c);row=service.owned(c,key)
    if row['status']!='CONNECTED':raise HTTPException(409,'Connect Google Sheets for this workspace first.')
    sid=sheets.spreadsheet_id(spreadsheet)
    old=c.execute('SELECT * FROM acquisition_jobs WHERE organization_id=? AND request_key=?',(organization(),str(request_id))).fetchone()
    if old:
        origin=json.loads(old['origin_json'])
        if old['owner']!=current().actor or old['source_type']!='GOOGLE_SHEETS' or origin.get('workspace_connection_id')!=key or origin.get('spreadsheet_id')!=sid or origin.get('sheet')!=tab:raise HTTPException(409,'Import request ID belongs to different source content.')
        return acquisition.detail(c,old['id'])
    cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    if c.execute("SELECT COUNT(*) FROM acquisition_jobs WHERE organization_id=? AND source_type='GOOGLE_SHEETS' AND created_at>?",(organization(),cutoff)).fetchone()[0]>=20:raise HTTPException(429,'Review existing spreadsheet imports before staging more.')
    result=await sheets.stage(c,current().actor,sid,tab,str(request_id),reader=reader_for(key,row['revision'],importing=True),connection=row)
    service.audit(c,key,'SHEETS_IMPORT_STAGED_FOR_REVIEW')
    return result
