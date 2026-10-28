from fastapi import APIRouter,Depends,HTTPException,Request,Query
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_db
from app.api.routes.workflow import require_prospect
from app.reports.service import create_report,expire_reports,launch_reports,public_report

router=APIRouter(tags=['Client PDF reports'])


@router.post('/leads/{lead_id}/pdf-reports',status_code=202)
def generate(lead_id:int,request:Request,conn=Depends(get_db)):
    if getattr(conn,'backend',None)!='postgres':conn.execute('BEGIN IMMEDIATE')
    prospect_id=require_prospect(conn,lead_id,request.state.user_email)
    report=create_report(conn,lead_id,prospect_id,request.state.user_email)
    conn.commit()
    try:launch_reports()
    except Exception:
        conn.execute("UPDATE client_reports SET status='FAILED',error_message='Worker dispatch failed' WHERE id=? AND status='QUEUED'",(report['id'],));conn.commit()
        report=public_report(conn.execute('SELECT * FROM client_reports WHERE id=?',(report['id'],)).fetchone())
    return report


@router.get('/client-reports')
def list_reports(lead_id:int|None=Query(None,ge=1),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),conn=Depends(get_db)):
    expire_reports(conn)
    where=' WHERE r.prospect_id=(SELECT prospect_id FROM businesses WHERE id=?)' if lead_id else ''
    args=[lead_id] if lead_id else []
    total=conn.execute('SELECT COUNT(*) FROM client_reports r'+where,args).fetchone()[0]
    rows=conn.execute('SELECT r.*,b.name FROM client_reports r JOIN businesses b ON b.id=r.business_id'+where+' ORDER BY r.created_at DESC,r.version DESC LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size]).fetchall()
    return {'items':[{**public_report(row),'business_name':row['name']} for row in rows],'total':total,'page':page,'page_size':page_size,'total_pages':max(1,(total+page_size-1)//page_size)}


def report_row(conn,report_id):
    expire_reports(conn)
    row=conn.execute('SELECT * FROM client_reports WHERE id=?',(report_id,)).fetchone()
    if not row:raise HTTPException(404,'Report not found.')
    return row


@router.get('/client-reports/{report_id}')
def report_status(report_id:str,conn=Depends(get_db)):
    return public_report(report_row(conn,report_id))


@router.get('/client-reports/{report_id}/download')
def download(report_id:str,conn=Depends(get_db)):
    from app.storage import artifact_storage
    row=report_row(conn,report_id)
    if row['status']!='READY':raise HTTPException(409,'The PDF is not ready. Please retry shortly.')
    try:body=artifact_storage().get(row['object_key'])
    except Exception:raise HTTPException(503,'The PDF is temporarily unavailable. Please retry.')
    def chunks():
        try:
            while chunk:=body.read(65536):yield chunk
        finally:body.close()
    return StreamingResponse(chunks(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="PlaneByte-audit-v{row["version"]}.pdf"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
