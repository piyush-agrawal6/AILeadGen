"""Real isolated Chromium, synthetic public transport; never a customer browser."""
import asyncio
import os
import httpx
import pytest
from app.platform.company_render import render
from app.utils.http import SafeAsyncClient

pytestmark=pytest.mark.skipif(os.environ.get('RUN_RENDER_BROWSER_TESTS')!='1',reason='Explicit isolated Chromium acceptance required.')


def test_render_executes_public_js_but_blocks_foreign_post_private_and_websocket(monkeypatch):
    calls=[]
    monkeypatch.setattr('app.utils.http.is_safe_url',lambda url,**kw:True)
    def handler(request):
        calls.append((request.method,str(request.url)))
        return httpx.Response(200,headers={'content-type':'text/javascript'},text="document.querySelector('main').textContent='Rendered public company services: practical software engineering.';")
    html='''<html><body><main>Loading</main><script src="/assets/company.js"></script><script>
    fetch('https://foreign.example.org/exfiltrate').catch(()=>{});
    fetch('https://example.com/write',{method:'POST',body:'blocked'}).catch(()=>{});
    fetch('http://127.0.0.1/private').catch(()=>{});
    try{new WebSocket('wss://example.com/socket')}catch(e){}
    document.body.dataset.alternateTransports=String([typeof RTCPeerConnection,typeof WebTransport,typeof Worker,typeof SharedWorker]);
    </script></body></html>'''
    async def exercise():
        policies=[]
        async def permitted(url):policies.append(url)
        async with SafeAsyncClient(transport=httpx.MockTransport(handler),timeout=4,max_bytes=400000) as client:
            result=await render('https://example.com',html,client,permitted,lambda *a:None)
        return result,policies
    result,policies=asyncio.run(exercise())
    assert 'Rendered public company services' in result
    assert 'data-alternate-transports="undefined,undefined,undefined,undefined"' in result
    assert calls==[('GET','https://example.com/assets/company.js')]
    assert policies==['https://example.com/assets/company.js']
