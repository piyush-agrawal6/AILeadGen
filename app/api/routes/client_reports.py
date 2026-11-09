from fastapi import APIRouter,Depends,HTTPException,Request,Query
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_db
from app.api.routes.workflow import require_prospect
from app.reports.service import create_report,expire_reports,launch_reports,public_report

router=APIRouter(tags=['Client PDF reports'])


@router.post('/leads/{lead_id}/pdf-reports',status_code=202)
def generate(lead_id:int,request:Request,conn=Depends(get_db,scope='function')):
    from app.prospecting.policy import unavailable
    unavailable()
@router.get('/client-reports')
def list_reports(request:Request,lead_id:int|None=Query(None,ge=1),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    where=' WHERE r.organization_id=?'+(' AND r.prospect_id=(SELECT prospect_id FROM businesses WHERE id=?)' if lead_id else '')
    args=[organization]+([lead_id] if lead_id else [])
    total=conn.execute('SELECT COUNT(*) FROM client_reports r'+where,args).fetchone()[0]
    rows=conn.execute('SELECT r.*,b.name FROM client_reports r JOIN businesses b ON b.id=r.business_id'+where+' ORDER BY r.created_at DESC,r.version DESC LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size]).fetchall()
    return {'items':[{**public_report(row),'business_name':row['name']} for row in rows],'total':total,'page':page,'page_size':page_size,'total_pages':max(1,(total+page_size-1)//page_size)}


def report_row(conn,report_id,organization=None):
    row=conn.execute('SELECT * FROM client_reports WHERE id=?'+(' AND organization_id=?' if organization else ''),(report_id,)+((organization,) if organization else ())).fetchone()
    if not row:raise HTTPException(404,'Report not found.')
    return row


@router.get('/client-reports/{report_id}')
def report_status(report_id:str,request:Request,conn=Depends(get_db,scope='function')):
    return public_report(report_row(conn,report_id,request.state.organization_id))


@router.get('/client-reports/{report_id}/download')
def download(report_id:str,request:Request,view:bool=False,conn=Depends(get_db,scope='function')):
    from app.storage import artifact_storage
    row=report_row(conn,report_id,request.state.organization_id)
    if row['status']!='READY':raise HTTPException(409,'The PDF is not ready. Please retry shortly.')
    try:body=artifact_storage().get(row['object_key'])
    except Exception:raise HTTPException(503,'The PDF is temporarily unavailable. Please retry.')
    def chunks():
        try:
            while chunk:=body.read(65536):yield chunk
        finally:body.close()
    return StreamingResponse(chunks(),media_type='application/pdf',headers={'Content-Disposition':f'{"inline" if view else "attachment"}; filename="PlaneByte-opportunity-review-v{row["version"]}.pdf"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
