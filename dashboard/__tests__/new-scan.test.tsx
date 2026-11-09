import {describe,it,expect,vi,beforeEach} from "vitest";
import {render,screen,fireEvent,waitFor} from "@testing-library/react";
import {QueryClient,QueryClientProvider} from "@tanstack/react-query";
import FindLeads from "@/app/find-leads/page";
import {request} from "@/lib/intelligence";
const push=vi.hoisted(()=>vi.fn());
vi.mock("next/navigation",()=>({useRouter:()=>({push})}));
vi.mock("@/lib/intelligence",()=>({request:vi.fn()}));
beforeEach(()=>{push.mockClear();vi.mocked(request).mockReset();vi.mocked(request).mockImplementation(async(path)=>path.startsWith('/discovery/searches')?{items:[],total:0}:path==='/foundation/me'?{role:'OWNER'}:{id:'manual-run'});});
function setup(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><FindLeads/></QueryClientProvider>);}
describe('Manual-first scan wizard',()=>{
 it('requires plan review before starting',()=>{setup();expect(screen.getByLabelText('Qualified leads required')).toHaveValue(50);expect(screen.queryByRole('button',{name:'Start Discovery'})).not.toBeInTheDocument();expect(vi.mocked(request).mock.calls.filter(([p])=>p==='/workflow/runs')).toHaveLength(0);});
 it('starts the existing workflow with the selected target only after review',async()=>{setup();fireEvent.change(screen.getByLabelText('Qualified leads required'),{target:{value:'8'}});fireEvent.click(screen.getByRole('button',{name:'Review plan'}));expect(await screen.findByText('Discovery plan')).toBeInTheDocument();expect(vi.mocked(request).mock.calls.filter(([p])=>p==='/workflow/runs')).toHaveLength(0);fireEvent.click(screen.getByRole('button',{name:'Start Discovery'}));await waitFor(()=>expect(push).toHaveBeenCalledWith('/runs/manual-run'));const call=vi.mocked(request).mock.calls.find(([p])=>p==='/workflow/runs');const body=JSON.parse(String(call?.[1]?.body));expect(body.target).toBe(8);expect(body.commercial_fit).toEqual(['HIGH','MEDIUM']);expect(body.opportunities).toEqual([]);expect(body.lighthouse_budget).toBe(0);expect(screen.queryByText('Opportunity targeting')).not.toBeInTheDocument();});
 it('shows server failures without sending or scanning',async()=>{setup();vi.mocked(request).mockRejectedValue(new Error('Workspace busy'));fireEvent.click(screen.getByRole('button',{name:'Review plan'}));fireEvent.click(await screen.findByRole('button',{name:'Start Discovery'}));expect((await screen.findAllByRole('alert')).some(node=>node.textContent?.includes('Workspace busy'))).toBe(true);expect(push).not.toHaveBeenCalled();});
});
