import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {IntelligenceAction} from '@/components/intelligence/job-action';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const job={id:'job-one',status:'COMPLETED',total:1,counts:{UNAVAILABLE:1},attempts:1,items:[{id:'item',status:'UNAVAILABLE',result:{reason:'NO_BUSINESS_EMAIL'}}],usage:{monetary_cost:null,cost_state:'NOT_REPORTED'}};
beforeEach(()=>{vi.mocked(request).mockReset();});
afterEach(cleanup);
function setup(onComplete=vi.fn()){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><IntelligenceAction kind="CONTACT_VERIFY" resourceIds={['person-one']} label="Check contact" onComplete={onComplete}/></QueryClientProvider>);return onComplete}
it('starts only on an explicit click and shows honest unavailable results',async()=>{vi.mocked(request).mockResolvedValue(job);const completed=setup();expect(request).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Check contact'}));expect(await screen.findByText('no business email')).toBeVisible();await waitFor(()=>expect(completed).toHaveBeenCalledTimes(1));expect(screen.getByText(/DNS checks do not verify deliverability/)).toBeVisible();expect(screen.getByRole('link',{name:'View job history'})).toHaveAttribute('href','/enrichment/job-one');const body=JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body));expect(body).toMatchObject({kind:'CONTACT_VERIFY',resource_ids:['person-one']})});
it('keeps the request key after an uncertain start error instead of creating duplicate work',async()=>{vi.mocked(request).mockRejectedValue(new Error('Connection interrupted'));setup();fireEvent.click(screen.getByRole('button',{name:'Check contact'}));expect(await screen.findByRole('alert')).toHaveTextContent('Connection interrupted');fireEvent.click(screen.getByRole('button',{name:'Check contact'}));await waitFor(()=>expect(request).toHaveBeenCalledTimes(2));expect(JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body)).request_id).toBe(JSON.parse(String(vi.mocked(request).mock.calls[1][1]?.body)).request_id);});
