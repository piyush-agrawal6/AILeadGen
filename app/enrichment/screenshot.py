"""Bounded anonymous public-page capture; private artifacts, never a PDF-time crawl."""
import asyncio
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from app.database.prospects import now
from app.storage import publish_artifact
from app.utils.browser_proxy import public_browser_proxy
from app.utils.urls import is_safe_url

async def capture_website(conn,business,profile,crawl):
    stamp=now();url=(profile.final_url or business.website) if profile else business.website
    status,reason,key='UNAVAILABLE','No reachable, crawl-permitted public homepage is available.',None
    if profile and profile.reachable and crawl and crawl.homepage_html and url and is_safe_url(url,check_dns=True):
        node=shutil.which('node')
        if node:
            try:
                with tempfile.TemporaryDirectory(prefix='planebyte-capture-') as folder, public_browser_proxy() as proxy:
                    path=Path(folder)/'homepage.webp'
                    proc=await asyncio.create_subprocess_exec(node,str(Path('scripts/capture-website.mjs').resolve()),url,str(path),proxy,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                    try:await asyncio.wait_for(proc.wait(),20)
                    except BaseException:
                        if proc.returncode is None:proc.kill();await proc.wait()
                        raise
                    if proc.returncode==0 and path.is_file() and path.stat().st_size<=2_000_000:
                        key=f'audits/{business.id}/captures/{uuid.uuid4()}.webp'
                        publish_artifact(conn,key,path,run_id=business.run_id,business_id=business.id,kind='website_desktop')
                        status,reason='READY','Public homepage captured during the scan.'
                    else:reason='Capture unavailable: page restricted, timed out, or did not produce a bounded public image.'
            except Exception:reason='Capture could not complete within the public-page limits.'
        else:reason='Screenshot browser runtime is unavailable.'
    conn.execute('INSERT INTO website_captures(business_id,object_key,page_url,captured_at,status,reason) VALUES(?,?,?,?,?,?) ON CONFLICT(business_id) DO UPDATE SET object_key=excluded.object_key,page_url=excluded.page_url,captured_at=excluded.captured_at,status=excluded.status,reason=excluded.reason',(business.id,key,url,stamp,status,reason))
    return status
