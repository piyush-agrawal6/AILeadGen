import {beforeEach,describe,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {ProductSwitcher} from '@/components/layout/product-switcher';
import {Sidebar} from '@/components/layout/sidebar';
import {MonitorWizard} from '@/components/intent-radar/monitors';
import {pageTitle} from '@/components/layout/header';
const state=vi.hoisted(()=>({path:'/',enabled:true,mutateAsync:vi.fn()}));
vi.mock('next/navigation',()=>({usePathname:()=>state.path,useRouter:()=>({push:vi.fn()})}));
vi.mock('@/components/workspaces/use-products',()=>({useProducts:()=>({data:{lead_engine:true,intent_radar:{enabled:state.enabled,stage:'Beta'}}})}));
vi.mock('@/components/intent-radar/provider',()=>({useRadarMutation:()=>({mutateAsync:state.mutateAsync,isPending:false}),useRadarRead:()=>({data:undefined}),useRadarCapabilities:()=>({data:{can_write:true,can_manage:true}})}));
beforeEach(()=>{state.path='/';state.enabled=true;state.mutateAsync.mockReset().mockResolvedValue({id:'controlled-monitor'})});
describe('native multi-product navigation',()=>{
  it('opens the accessible product menu and exposes only authorized products',async()=>{render(<ProductSwitcher/>);fireEvent.keyDown(screen.getByRole('button',{name:'Switch PlaneByte product'}),{key:'Enter'});expect(await screen.findByRole('menuitem',{name:/Intent Radar/})).toHaveAttribute('href','/intent-radar');expect(screen.getByText('Beta',{exact:true})).toBeVisible();expect(screen.getByRole('menuitem',{name:/Lead Engine/})).toHaveAttribute('href','/lead-engine')});
 it('keeps unentitled Radar out of customer navigation',async()=>{state.enabled=false;render(<ProductSwitcher/>);fireEvent.keyDown(screen.getByRole('button',{name:'Switch PlaneByte product'}),{key:'Enter'});await screen.findByRole('menuitem',{name:/Lead Engine/});expect(screen.queryByRole('menuitem',{name:/Intent Radar/})).not.toBeInTheDocument()});
  it('preserves Lead Engine links and changes only the entitled product navigation',()=>{const rendered=render(<Sidebar/>);expect(screen.getByRole('link',{name:'Find Leads'})).toHaveAttribute('href','/find-leads');expect(screen.getByRole('link',{name:'Campaigns'})).toHaveAttribute('href','/campaigns');state.path='/intent-radar/signals';rendered.rerender(<Sidebar/>);expect(screen.getByRole('link',{name:'Signals'})).toHaveAttribute('aria-current','page');expect(screen.getByRole('link',{name:'Monitoring'})).toHaveAttribute('href','/intent-radar/monitors');expect(screen.queryByRole('link',{name:'Find Leads'})).not.toBeInTheDocument();expect(pageTitle('/intent-radar/signals/test')).toBe('Intent Signals');expect(pageTitle('/campaigns')).toBe('Campaigns')});
});
it('migrated wizard validates and persists a reviewed monitor without running discovery',async()=>{
 const close=vi.fn();render(<MonitorWizard open onClose={close}/>);fireEvent.click(screen.getByRole('button',{name:'Continue'}));fireEvent.click(screen.getByRole('button',{name:'Continue'}));expect(screen.getByRole('alert')).toHaveTextContent('Enter a monitor name');
  fireEvent.change(screen.getByLabelText('Monitor name'),{target:{value:'Native website demand'}});fireEvent.change(screen.getByLabelText('Add Keywords'),{target:{value:'website'}});fireEvent.keyDown(screen.getByLabelText('Add Keywords'),{key:'Enter'});fireEvent.click(screen.getByRole('button',{name:'Continue'}));fireEvent.click(screen.getByRole('button',{name:'Continue'}));fireEvent.click(screen.getByRole('button',{name:'Continue'}));fireEvent.click(screen.getByRole('button',{name:'Create Monitor'}));
 await waitFor(()=>expect(state.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({path:'/monitors',body:expect.objectContaining({name:'Native website demand',status:'Active',configuration:expect.objectContaining({keywords:['website'],source:'Hacker News'})})})));expect(state.mutateAsync.mock.calls.every(([arg])=>arg.path!=='/discover')).toBe(true);expect(close).toHaveBeenCalled();
});
