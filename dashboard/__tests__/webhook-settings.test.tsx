import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {WebhookSettings} from '@/components/workspaces/webhook-settings';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',async original=>({...await original<typeof import('@/lib/intelligence')>(),request:vi.fn()}));
const calls=vi.mocked(request);
const endpoint={id:'owned-hook',name:'Owner receiver',url:'https://receiver.example.com/events',topics:['company.created'],status:'ACTIVE',revision:1,last_error_code:null};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><WebhookSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());

it('creates a future-event subscription, shows the signing secret once and clears it explicitly',async()=>{
 calls.mockImplementation(async(path,options)=>options?.method==='POST'?{endpoint,signing_secret:'ephemeral-fixture-signing-secret'}:{items:[],configured:true,available_topics:['company.created','task.created']});mount();
 fireEvent.click(await screen.findByText('Add webhook endpoint'));fireEvent.change(screen.getByLabelText('Endpoint name'),{target:{value:'Owner receiver'}});fireEvent.change(screen.getByLabelText('Public HTTPS receiver'),{target:{value:endpoint.url}});fireEvent.click(screen.getByRole('button',{name:'Create webhook'}));
 expect(await screen.findByLabelText('Webhook signing secret')).toHaveTextContent('ephemeral-fixture-signing-secret');expect(screen.getByRole('button',{name:'Create webhook'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'I saved the signing secret'}));expect(screen.queryByLabelText('Webhook signing secret')).not.toBeInTheDocument();
 const mutation=calls.mock.calls.find(([,options])=>options?.method==='POST');const body=JSON.parse(String(mutation?.[1]?.body));expect(body.url).toBe(endpoint.url);expect(body.organization_id).toBeUndefined();expect(body.topics).toEqual(['company.created']);
 expect(calls.mock.calls.some(([path])=>path.includes('email')||path.includes('scan'))).toBe(false);
});

it('requires confirmation for endpoint changes and shows real bounded delivery history',async()=>{
 const delivery={id:'owned-delivery',event_id:'stable-event',topic:'company.created',status:'RETRY',attempts:1,next_attempt_at:'2026-11-07T12:00:00Z',last_http_status:503,last_error_code:'HTTP_503',created_at:'2026-11-07T11:00:00Z'};
 calls.mockImplementation(async(path,options)=>path.endsWith('/deliveries?page=1')?{items:[delivery],total:1}:options?.method==='POST'?{endpoint:{...endpoint,status:'PAUSED',revision:2}}:{items:[endpoint],configured:true,available_topics:['company.created']});mount();
 fireEvent.click(await screen.findByRole('button',{name:'Delivery history'}));expect(await screen.findByText(/company.created · Retry · 1\/5 attempts/)).toBeVisible();expect(screen.queryByRole('button',{name:'Previous deliveries'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Pause'}));expect(calls.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false);fireEvent.click(screen.getByRole('button',{name:'Confirm webhook change'}));
 await waitFor(()=>expect(calls.mock.calls.some(([path,options])=>path==='/organization/webhooks/owned-hook/control'&&options?.method==='POST')).toBe(true));
});

it('shows a clear configuration requirement instead of a nonfunctional create form',async()=>{
 calls.mockResolvedValue({items:[],configured:false,available_topics:[]});mount();expect(await screen.findByText('Webhook signing needs the server integration encryption key.')).toBeVisible();expect(screen.queryByRole('button',{name:'Create webhook'})).not.toBeInTheDocument();
});
