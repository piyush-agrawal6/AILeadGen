"""The only anonymous application surface: opaque email tracking capabilities."""
import base64,html,re
from fastapi import APIRouter,Request,Depends
from fastapi.responses import Response,HTMLResponse,RedirectResponse
from app.api.dependencies import get_db
from app.mail import tracking

router=APIRouter(prefix='/tracking',tags=['Email tracking'])
GIF=base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
HEADERS={'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}

def page(text,status=200):
    return HTMLResponse('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><title>PlaneByte email preferences</title><main style="max-width:36rem;margin:4rem auto;font:16px Arial;line-height:1.6;padding:1rem"><h1>PlaneByte email preferences</h1>'+text+'</main></html>',status_code=status,headers=HEADERS)

@router.api_route('/o/{value}',methods=['GET','HEAD'])
def opened(value:str,request:Request,conn=Depends(get_db)):
    token=value[:-4] if value.endswith('.gif') else ''
    if tracking.rate_allowed(conn,token,'o'):
        row=tracking.lookup(conn,token,'o')
        if row:tracking.public_signal(conn,row,request.method,request.headers.get('user-agent',''),request.headers.get('sec-fetch-user',''))
    return Response(GIF,media_type='image/gif',headers=HEADERS)

@router.api_route('/c/{token}',methods=['GET','HEAD'])
def clicked(token:str,request:Request,conn=Depends(get_db)):
    if not tracking.rate_allowed(conn,token,'c'):return page('<p>Please try again shortly.</p>',429)
    row=tracking.lookup(conn,token,'c')
    if not row or not tracking.allowed_url(row['destination']):return page('<p>This link is unavailable.</p>',404)
    tracking.public_signal(conn,row,request.method,request.headers.get('user-agent',''),request.headers.get('sec-fetch-user',''))
    return RedirectResponse(row['destination'],status_code=302,headers=HEADERS)

@router.api_route('/u/{token}',methods=['GET','POST'])
async def optout(token:str,request:Request,conn=Depends(get_db)):
    if not tracking.rate_allowed(conn,token,'u'):return page('<p>Please try again shortly.</p>',429)
    row=tracking.lookup(conn,token,'u')
    if not row:return page('<p>This link is unavailable.</p>',404)
    if request.method=='GET':
        # GET and link previews never change suppression. No account or lead PII is returned.
        return page('<p>Stop receiving PlaneByte outreach?</p><form method="post"><button name="confirm" value="stop">Stop receiving emails</button></form>')
    # Bound the body before parsing, even if Content-Length is missing or forged.
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>1024:return page('<p>Request too large.</p>',413)
    if bytes(body) not in (b'confirm=stop',b'List-Unsubscribe=One-Click'):return page('<p>Please confirm using the button.</p>',400)
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    tracking.unsubscribe(conn,row)
    return page('<p>Email preference recorded.</p>')
