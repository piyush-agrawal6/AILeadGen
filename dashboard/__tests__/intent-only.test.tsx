import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {leadEngineEnabled,isLeadEnginePage} from '@/lib/product-availability';
import {WorkspaceAccessRetry} from '@/components/intent-radar/access-retry';
import {AuthFrame} from '@/components/auth/auth-frame';
import {Sidebar} from '@/components/layout/sidebar';
import {CapabilityFeatures} from '@/components/workspaces/features';
const {refresh}=vi.hoisted(()=>({refresh:vi.fn()}));
vi.mock('next/navigation',()=>({usePathname:()=>'/intent-radar',useRouter:()=>({refresh})}));
vi.mock('@/components/workspaces/use-products',()=>({useProducts:()=>({data:{lead_engine:true,intent_radar:{enabled:true,growth_enabled:true}}})}));
afterEach(()=>vi.unstubAllEnvs());
it('uses a fail-closed reversible server configuration without gating shared settings',()=>{
 expect(leadEngineEnabled(undefined)).toBe(false);expect(leadEngineEnabled('false')).toBe(false);expect(leadEngineEnabled('true')).toBe(true);
 for(const path of ['/lead-engine','/scans/4','/campaigns/owned','/settings/limits','/settings/integrations/gmail-callback','/%63ampaigns','/scans%2F4'])expect(isLeadEnginePage(path)).toBe(true);
 for(const path of ['/intent-radar','/intent-radar/growth','/settings/company','/settings/icp','/settings/developer','/billing','/account/security'])expect(isLeadEnginePage(path)).toBe(false);
});
it('unmounts the product selector even when historical grants include Lead Engine',()=>{
 render(<CapabilityFeatures.Provider value={{companyDiscovery:false,leadEngineAvailable:false}}><Sidebar/></CapabilityFeatures.Provider>);
 expect(screen.queryByRole('button',{name:'Switch PlaneByte product'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('Intent Radar product')).toBeVisible();
 for(const label of ['Find Leads','Companies','Contacts','Campaigns','Outreach','Schedules'])expect(screen.queryByRole('link',{name:label})).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Discover Intent'})).toBeVisible();expect(screen.getByRole('link',{name:'Research assistant'})).toBeVisible();
});
it('public authentication presents Intent Radar without prospecting promotion',()=>{
 vi.stubEnv('LEAD_ENGINE_AVAILABLE','false');render(<AuthFrame><h2>Welcome back</h2></AuthFrame>);
 expect(screen.getByText('Discover relevant conversations')).toBeInTheDocument();expect(screen.queryByText(/Lead Engine/)).not.toBeInTheDocument();expect(screen.queryByText('Discover relevant companies')).not.toBeInTheDocument();
});
it('retains the original authentication product content for an explicit reactivation',()=>{
 vi.stubEnv('LEAD_ENGINE_AVAILABLE','true');render(<AuthFrame><h2>Welcome back</h2></AuthFrame>);
 expect(screen.getByText('Discover relevant companies')).toBeInTheDocument();
});

it('distinguishes a failed access check and offers an explicit server retry without granting access',()=>{render(<WorkspaceAccessRetry/>);expect(screen.getByRole('heading',{name:'Workspace access could not be checked'})).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Retry access check'}));expect(refresh).toHaveBeenCalledTimes(1);expect(screen.queryByText('Intent Radar access is restricted')).not.toBeInTheDocument();});
