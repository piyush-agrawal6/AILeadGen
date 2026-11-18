import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import Lists from '@/app/lists/page';
import Tasks from '@/app/tasks/page';
import Recommendations from '@/app/recommendations/page';
import Help from '@/app/help/page';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',async original=>({...await original<typeof import('@/lib/intelligence')>(),request:vi.fn()}));
const calls=vi.mocked(request);
function mount(component:React.ReactNode){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{component}</QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());

it('creates lists through a focused dialog, preserves an empty-state next step and hides unnecessary pagination',async()=>{
 calls.mockImplementation(async path=>path==='/foundation/me'?{role:'OWNER'}:{items:[],total:0});mount(<Lists/>);
 fireEvent.click(await screen.findByRole('button',{name:'Create list'}));const dialog=screen.getByRole('dialog');expect(within(dialog).getByRole('heading',{name:'Create a list'})).toBeVisible();
 fireEvent.change(within(dialog).getByLabelText('List name'),{target:{value:'Priority companies'}});fireEvent.click(within(dialog).getByRole('button',{name:'Create list'}));
 expect(await screen.findByText('List created. No discovery or outreach was started.')).toBeVisible();expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Previous lists'})).not.toBeInTheDocument();expect(screen.getByRole('link',{name:'Find companies for your first list'})).toHaveAttribute('href','/find-leads');
 expect(calls.mock.calls.some(([path,options])=>path==='/sales/lists'&&options?.method==='POST')).toBe(true);
});

it('edits a task with revision protection and explicit reassignment without sending email',async()=>{
 const task={id:'owned-task',title:'Review evidence',company_name:'Controlled company',business_id:5,task_type:'REVIEW',priority:'NORMAL',note:'',due_at:'2026-12-01T09:00:00Z',status:'OPEN',revision:2,assigned_to:null};
 calls.mockImplementation(async path=>path==='/foundation/me'?{role:'OWNER'}:path==='/users'?[{id:'owner@example.test',display_name:'Owner'}]:{items:[task],total:1});mount(<Tasks/>);
 fireEvent.click(await screen.findByRole('button',{name:'Edit Review evidence'}));const dialog=screen.getByRole('dialog');fireEvent.change(within(dialog).getByLabelText('Edit task title'),{target:{value:'Prepare a practical approach'}});fireEvent.change(within(dialog).getByLabelText('Edit priority'),{target:{value:'HIGH'}});fireEvent.change(within(dialog).getByLabelText('Edit assigned member'),{target:{value:'owner@example.test'}});fireEvent.click(within(dialog).getByRole('button',{name:'Save task changes'}));
 await screen.findByRole('button',{name:'Create sales task'});expect(await screen.findByRole('heading',{name:'Review evidence'})).toBeVisible();
 const mutation=calls.mock.calls.find(([,options])=>options?.method==='PATCH');const body=JSON.parse(String(mutation?.[1]?.body));expect(body.revision).toBe(2);expect(body.title).toBe('Prepare a practical approach');expect(body.assigned_to).toBe('owner@example.test');expect(body.priority).toBe('HIGH');expect(calls.mock.calls.some(([path])=>path.includes('send')||path.includes('outreach'))).toBe(false);
});

it('guides users to ICP setup instead of showing an empty recommendations selector',async()=>{
 calls.mockResolvedValue({items:[],role:'OWNER'});mount(<Recommendations/>);
 expect(await screen.findByRole('heading',{name:'Create your first targeting profile'})).toBeVisible();expect(screen.queryByRole('combobox')).not.toBeInTheDocument();expect(screen.getByRole('link',{name:'Generate with AI'})).toHaveAttribute('href','/settings/icp');expect(calls.mock.calls.some(([path])=>path.startsWith('/qualification/'))).toBe(false);
});

it('provides searchable real product guidance and a support workflow',async()=>{
 mount(<Help/>);
 expect(await screen.findByRole('heading',{name:'How can we help?'})).toBeVisible();
 fireEvent.change(screen.getByLabelText('Search help articles'),{target:{value:'monitors'}});
 expect(screen.getByText(/Creating monitors, schedules & notification preferences/i)).toBeVisible();
 expect(screen.getAllByRole('button',{name:/Contact Support/i}).length).toBeGreaterThanOrEqual(1);
});
