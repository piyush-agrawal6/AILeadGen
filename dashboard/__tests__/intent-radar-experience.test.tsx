import {beforeEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {DiscoverExperience} from '@/components/intent-radar/discovery';
import {EvidenceDetail} from '@/components/intent-radar/evidence-experience';
import {IntegrationsPage} from '@/components/intent-radar/integrations';
import {emptyIntentSearch} from '@/lib/intent-radar';
const state=vi.hoisted(()=>({mutate:vi.fn(),signal:{id:'controlled-evidence',title:'<script>alert(1)</script>',excerpt:'<img src=x onerror=alert(1)>',source:'Hacker News',source_url:'https://news.ycombinator.com/item?id=999123',observed_at:'2026-11-10T00:00:00Z',retrieved_at:'2026-11-10T00:00:00Z',category:'Uncertain',score:40,status:'New',notes:'',revision:1,saved:false,monitors:[],evidence:{matched_keywords:[],unknown:['Buying authority is unknown.'],confidence:'Low',explanation:'Public-source text only.'}}}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn()})}));
vi.mock('@/components/workspaces/use-workspace',()=>({useWorkspace:()=>({data:{active_organization_id:'fixture-workspace'}})}));
vi.mock('@/lib/intelligence',()=>({request:vi.fn().mockResolvedValue({enabled:false,mcp_available:false,can_manage:true})}));
vi.mock('@/components/intent-radar/provider',()=>({useRadarMutation:()=>({mutateAsync:state.mutate,mutate:state.mutate,isPending:false}),useRadarRefresh:()=>vi.fn(),useRadarRead:(path:string)=>({data:path==='/settings'?{default_view:'table',topics:[],min_relevance:0,alerts_enabled:true,alert_threshold:85,revision:0}:path.startsWith('/signals/')?state.signal:undefined}),useRadarCapabilities:()=>({data:{can_write:true,can_manage:true,sources:[{name:'Hacker News',state:'Available',coverage:'Recent Ask HN stories only',documentation:'https://github.com/HackerNews/API'}]}})}));
beforeEach(()=>state.mutate.mockReset());
it('an explicitly labeled manual draft stays inert until the user confirms a public search',async()=>{
 state.mutate.mockResolvedValueOnce({draft:{configuration:{...emptyIntentSearch(),keywords:['website']}},mode:'Manual fallback',fallback_reason:'AI assistance is disabled.'}).mockResolvedValueOnce({id:'fixture-job'});
 render(<DiscoverExperience/>);fireEvent.click(screen.getByRole('button',{name:/Describe with AI/i}));fireEvent.change(screen.getByLabelText('What are you looking for?'),{target:{value:'Find website development recommendations'}});fireEvent.click(screen.getByRole('button',{name:/Generate Criteria/i}));
 await screen.findByRole('heading',{name:'Review Search Criteria'});expect(screen.getByText(/Manual Fallback Criteria/i)).toBeVisible();expect(state.mutate).toHaveBeenCalledTimes(1);expect(state.mutate.mock.calls[0][0].path).toBe('/draft');
 fireEvent.click(screen.getByRole('button',{name:/Run Search/i}));await waitFor(()=>expect(state.mutate).toHaveBeenCalledWith(expect.objectContaining({path:'/discover',body:expect.objectContaining({configuration:expect.objectContaining({keywords:['website']})})})));
});
it('advanced search requires a committed keyword before reaching review',()=>{
 render(<DiscoverExperience/>);fireEvent.click(screen.getByRole('button',{name:'Advanced Search'}));fireEvent.click(screen.getByRole('button',{name:'Review Search'}));expect(screen.getByRole('alert')).toHaveTextContent('Add at least one keyword');expect(state.mutate).not.toHaveBeenCalled();
});
it('public source markup is displayed as inert text in the evidence view',()=>{
 const view=render(<EvidenceDetail id="controlled-evidence"/>);expect(screen.getByRole('heading',{name:'<script>alert(1)</script>'})).toBeVisible();expect(screen.getByText('<img src=x onerror=alert(1)>',{exact:true})).toBeVisible();expect(view.container.querySelector('script')).toBeNull();expect(view.container.querySelector('img[src="x"]')).toBeNull();expect(screen.getByRole('link',{name:/Open original public discussion/})).toHaveAttribute('rel','noopener noreferrer');
});
it('the real source details navigate to discovery while roadmap providers offer no fake Connect action',async()=>{
 render(<QueryClientProvider client={new QueryClient()}><IntegrationsPage/></QueryClientProvider>);fireEvent.click(screen.getByRole('button',{name:'View details for Hacker News'}));expect(screen.getByRole('link',{name:'Open signal search'})).toHaveAttribute('href','/intent-radar/discover');fireEvent.click(screen.getByRole('button',{name:'Close dialog'}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());fireEvent.mouseDown(screen.getByRole('tab',{name:'AI Assistants & MCP'}),{button:0,ctrlKey:false});fireEvent.click(await screen.findByRole('button',{name:'Learn more about ChatGPT / OpenAI'}));await screen.findByRole('dialog',{name:'ChatGPT / OpenAI'});expect(screen.getByRole('dialog')).toHaveTextContent('not been implemented');expect(screen.queryByRole('button',{name:/^Connect/})).not.toBeInTheDocument();
});
