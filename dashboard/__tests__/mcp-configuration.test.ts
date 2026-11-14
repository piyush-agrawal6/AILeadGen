import {expect,it} from 'vitest';
import {publicMcpEndpoint,copilotConfiguration} from '@/lib/mcp-configuration';
it('exposes only the configured public transport origin, rejecting credentials and ambiguous URLs',()=>{
 expect(publicMcpEndpoint('https://api.example.test')).toBe('https://api.example.test/api/v1/mcp');
 for(const value of ['https://key:secret@api.example.test','https://api.example.test/?token=secret','https://api.example.test/#secret','http://public.example.test','javascript:alert(1)','https://api.example.test/extra'])expect(publicMcpEndpoint(value)).toBe('');
 expect(publicMcpEndpoint('http://127.0.0.1:18787')).toBe('http://127.0.0.1:18787/api/v1/mcp');
});
it('copies the documented portable schema with an environment reference and explicitly selected read tools',()=>{
 const config=JSON.parse(copilotConfiguration('https://api.example.test/api/v1/mcp'));
 expect(config.mcpServers.planeByte.headers.Authorization).toBe('Bearer ${PLANEBYTE_MCP_KEY}');
 expect(config.mcpServers.planeByte.tools).toEqual(['search_intent_signals','list_intent_monitors','get_intent_signal']);
 expect(config.inputs).toBeUndefined();expect(config.servers).toBeUndefined();
});
