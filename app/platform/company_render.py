"""Optional isolated rendering; every network read uses the pinned public client.

No customer browser/session, cookies, downloads, form submission, third-party
requests, service workers or WebSockets are used. A failed sandbox stays failed;
there is no retry with Chromium security disabled.
"""
import asyncio
import os
from urllib.parse import urlsplit
from app.utils.urls import _tld_extractor


async def render(url, html, client, permitted, active):
    from playwright.async_api import async_playwright
    domain=_tld_extractor(urlsplit(url).hostname or '').top_domain_under_public_suffix
    requests=0;total_bytes=0;main_seen=False
    semaphore=asyncio.Semaphore(2)
    async with asyncio.timeout(15):
        async with async_playwright() as playwright:
            executable=os.environ.get('CHROME_PATH')
            browser=await playwright.chromium.launch(headless=True,chromium_sandbox=True,args=['--disable-background-networking','--disable-component-update','--disable-quic','--no-pings','--force-webrtc-ip-handling-policy=disable_non_proxied_udp'],**({'executable_path':executable} if executable else {}))
            try:
                context=await browser.new_context(service_workers='block',accept_downloads=False,user_agent=client.headers.get('user-agent'))
                # HTTP routing does not cover peer-to-peer UDP or QUIC. Remove
                # alternate transports/workers in every frame before site code.
                await context.add_init_script("""for (const name of ['RTCPeerConnection','webkitRTCPeerConnection','WebTransport','Worker','SharedWorker']) {
                    Object.defineProperty(globalThis,name,{value:undefined,writable:false,configurable:false});
                }""")
                await context.route_web_socket('**/*',lambda socket:socket.close())
                async def route_request(route):
                    nonlocal requests,total_bytes,main_seen
                    request=route.request;parsed=urlsplit(request.url)
                    if request.method!='GET' or parsed.scheme!='https' or parsed.username or parsed.password or _tld_extractor(parsed.hostname or '').top_domain_under_public_suffix!=domain:
                        return await route.abort()
                    if request.resource_type not in ('document','script','xhr','fetch') or requests>=24:return await route.abort()
                    if request.resource_type=='document':
                        if main_seen or request.url.rstrip('/')!=url.rstrip('/'):return await route.abort()
                        main_seen=True
                        return await route.fulfill(status=200,content_type='text/html',body=html)
                    requests+=1
                    try:
                        async with semaphore:
                            await asyncio.to_thread(active)
                            response=await client.get(request.url,allowed_domain=domain,require_https=True,before_request=permitted)
                            response.raise_for_status();total_bytes+=len(response.content)
                            if total_bytes>3_000_000:raise ValueError('Rendering byte budget exceeded')
                            await route.fulfill(status=response.status_code,content_type=response.headers.get('content-type','text/plain'),body=response.content)
                    except Exception:
                        await route.abort()
                await context.route('**/*',route_request)
                page=await context.new_page()
                await page.goto(url,wait_until='networkidle',timeout=11000)
                await asyncio.to_thread(active)
                return await page.content()
            finally:
                await browser.close()
