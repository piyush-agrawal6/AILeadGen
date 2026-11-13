import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {expect,it,vi} from 'vitest';
import Developer from '@/app/settings/developer/page';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
it('requires explicit scopes and can issue an Intent-only key without an invisible company scope',async()=>{
 vi.mocked(request).mockImplementation(async(path:string)=>{
  if(path.endsWith('/status'))return {enabled:true,can_manage:true,mcp_available:false};
  return {items:[],available_scopes:['intent:read','mcp:use'],rate_limit_per_minute:60};
 });
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Developer/></QueryClientProvider>);
 const intent=await screen.findByRole('checkbox',{name:'intent:read'});
 expect(intent).not.toBeChecked();expect(screen.queryByRole('checkbox',{name:'companies:read'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Key name'),{target:{value:'Intent read client'}});
 expect(screen.getByRole('button',{name:'Create API key'})).toBeDisabled();
 fireEvent.click(intent);fireEvent.click(screen.getByRole('checkbox',{name:'mcp:use'}));
 fireEvent.click(screen.getByRole('button',{name:'Create API key'}));
 await waitFor(()=>expect(vi.mocked(request).mock.calls.some(([path,options])=>path==='/organization/developer/keys'&&options?.method==='POST'&&JSON.parse(String(options.body)).scopes.join(',')==='intent:read,mcp:use')).toBe(true));
});
