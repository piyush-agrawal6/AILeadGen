"""Browser-suite probe using the official client through the local Next gateway."""
import asyncio,json,os,uuid
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

async def main():
    # A local-only fixture utility; no arbitrary destination or credentials on disk.
    endpoint='http://127.0.0.1:13000/api/v1/mcp'
    token=os.environ['PLANEBYTE_TEST_API_CREDENTIAL']
    async with httpx2.AsyncClient(headers={'authorization':'Bearer '+token},trust_env=False,timeout=15) as http:
        async with Client(streamable_http_client(endpoint,http_client=http,terminate_on_close=False),read_timeout_seconds=12) as client:
            tools=await client.list_tools();found=await client.call_tool('search_companies',{})
            assert not found.is_error
            proposal=await client.call_tool('propose_action',{'kind':'create_list','arguments':{'name':'Controlled MCP browser list'},'request_id':str(uuid.uuid4())})
            assert not proposal.is_error
            print(json.dumps({'tools':len(tools.tools),'companies':len(found.structured_content['items']),'proposal_id':proposal.structured_content['id'],'status':proposal.structured_content['status']}))

if __name__=='__main__':asyncio.run(main())
