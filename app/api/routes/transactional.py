from fastapi import APIRouter,Depends,HTTPException,Request
from app.api.dependencies import get_db
from app.notifications.webhooks import receive
router=APIRouter(prefix='/notifications/webhooks',tags=['Transactional email events'])
@router.post('/resend')
async def resend(request:Request,c=Depends(get_db,scope='function')):
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>65536:raise HTTPException(413,'Email event exceeds its bound.')
    # Signature validation and metadata persistence are small bounded work.
    import asyncio
    return await asyncio.to_thread(receive,c,bytes(raw),request.headers)
