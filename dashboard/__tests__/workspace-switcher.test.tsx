import {describe,it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {WorkspaceSwitcher} from '@/components/workspaces/switcher';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const fixtures={active_organization_id:'one',items:[{organization_id:'one',name:'First company',role:'OWNER'},{organization_id:'two',name:'Second company',role:'VIEWER'}]};
function mount(onSelected=vi.fn()){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><WorkspaceSwitcher onSelected={onSelected}/></QueryClientProvider>);
 return onSelected;
}
beforeEach(()=>vi.resetAllMocks());
describe('workspace selection',()=>{
 it('changes workspace only after the server confirms it and blocks duplicate selection',async()=>{
  let complete!:(value:unknown)=>void;
  mocked.mockResolvedValueOnce(fixtures).mockImplementationOnce(()=>new Promise(resolve=>{complete=resolve}));
  const selected=mount();const select=await screen.findByRole('button',{name:'Workspace: First company'});
  expect(select).toHaveTextContent('First company');fireEvent.keyDown(select,{key:'ArrowDown'});fireEvent.click(await screen.findByRole('menuitemradio',{name:'Second company'}));
  await waitFor(()=>expect(select).toBeDisabled());expect(selected).not.toHaveBeenCalled();
  expect(mocked).toHaveBeenLastCalledWith('/organization/active',{method:'PUT',body:JSON.stringify({organization_id:'two'})});
  complete({organization_id:'two'});await waitFor(()=>expect(selected).toHaveBeenCalledWith('two'));
 });
 it('retains the current workspace after a rejected change',async()=>{
  mocked.mockResolvedValueOnce(fixtures).mockRejectedValueOnce(new Error('Denied'));
  const selected=mount();const select=await screen.findByRole('button',{name:'Workspace: First company'});fireEvent.keyDown(select,{key:'ArrowDown'});fireEvent.click(await screen.findByRole('menuitemradio',{name:'Second company'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be changed');expect(select).toHaveTextContent('First company');expect(selected).not.toHaveBeenCalled();
 });
});
