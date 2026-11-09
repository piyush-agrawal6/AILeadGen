import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {WorkspaceGate} from '@/components/workspaces/gate';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
vi.mock('next/navigation',()=>({usePathname:()=>'/'}));
const mocked=vi.mocked(request);
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><WorkspaceGate><p>Private product</p></WorkspaceGate></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('offers a new signed-in user their own workspace without mounting private data views',async()=>{
 mocked.mockResolvedValue({items:[],active_organization_id:null,active_onboarding_status:null});mount();expect(await screen.findByRole('link',{name:'Create your workspace'})).toHaveAttribute('href','/settings/workspaces');expect(screen.queryByText('Private product')).not.toBeInTheDocument();
});
it('keeps incomplete company setup outside product views',async()=>{
 mocked.mockResolvedValue({items:[{organization_id:'owned',name:'Company',role:'OWNER'}],active_organization_id:'owned',active_onboarding_status:'IN_PROGRESS'});mount();expect(await screen.findByRole('link',{name:'Resume company setup'})).toBeVisible();expect(screen.queryByText('Private product')).not.toBeInTheDocument();
});
it('renders products only after verified completed workspace metadata',async()=>{
 mocked.mockResolvedValue({items:[{organization_id:'owned',name:'Company',role:'OWNER'}],active_organization_id:'owned',active_onboarding_status:'COMPLETED'});mount();await waitFor(()=>expect(screen.getByText('Private product')).toBeVisible());
});
