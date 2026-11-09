import {beforeEach,describe,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import Limits from '@/app/settings/limits/page';
const fetchMock=vi.hoisted(()=>vi.fn());
beforeEach(()=>{vi.stubGlobal('fetch',fetchMock);fetchMock.mockReset()});
const targets={daily_qualified_lead_target:100,daily_email_target:100,max_hour:10,max_day:100,followup_days:3,automation_timezone:'Asia/Kolkata'};
describe('workflow repair acceptance',()=>{
 it('saves the owner requested 500/500/50/500 limits with no activation fields',async()=>{
  fetchMock.mockImplementation(async(url:string,options?:RequestInit)=>new Response(JSON.stringify(url.includes('/workflow/safety')?{bounce_pause_threshold:.2,bounce_min_sample:10}:options?.method==='PUT'?JSON.parse(String(options.body)):targets),{headers:{'content-type':'application/json'}}));
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Limits/></QueryClientProvider>);
  await screen.findByLabelText('Hourly email limit');
  for(const [label,value] of [['Daily qualified lead target','500'],['Daily email target','500'],['Hourly email limit','50'],['Daily email limit','500']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
  fireEvent.click(screen.getByRole('button',{name:'Save Limits'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(([,o])=>o?.method==='PUT')).toBe(true));
  const call=fetchMock.mock.calls.find(([,o])=>o?.method==='PUT');
  expect(JSON.parse(call?.[1].body)).toEqual({...targets,daily_qualified_lead_target:500,daily_email_target:500,max_hour:50,max_day:500});
 });
 it('renders field validation errors without echoing rejected input',async()=>{
  const {request}=await import('@/lib/intelligence');
  fetchMock.mockResolvedValue(new Response(JSON.stringify({detail:[{loc:['body','max_hour'],msg:'Input should be less than or equal to 50',input:'private-input-not-for-display'}]}),{status:422}));
  await expect(request('/automation/targets',{method:'PUT',body:'{}'})).rejects.toThrow('Hourly limit: Input should be less than or equal to 50');
 });
});
