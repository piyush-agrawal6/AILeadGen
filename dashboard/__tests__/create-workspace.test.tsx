import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {CreateWorkspace} from '@/components/workspaces/create-workspace';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
it('retries creation with the same durable request ID and preserves selection when creation already completed',async()=>{
 const mocked=vi.mocked(request);mocked.mockRejectedValueOnce(new Error('Connection interrupted.')).mockResolvedValueOnce({organization_id:'created',reused:true});
 const done=vi.fn();render(<CreateWorkspace onCreated={done}/>);
 fireEvent.change(screen.getByLabelText('Company name'),{target:{value:'Controlled Company'}});fireEvent.click(screen.getByRole('button',{name:'Create workspace'}));
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Connection interrupted.'));expect(done).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Create workspace'}));expect(await screen.findByRole('status')).toHaveTextContent('already created.');expect(done).not.toHaveBeenCalled();
 const first=JSON.parse(String(mocked.mock.calls[0][1]?.body)),second=JSON.parse(String(mocked.mock.calls[1][1]?.body));
 expect(first).toEqual(second);expect(first.name).toBe('Controlled Company');expect(first.request_id).toMatch(/^[a-f0-9-]{36}$/);expect(first.organization_id).toBeUndefined();expect(first.role).toBeUndefined();
});
