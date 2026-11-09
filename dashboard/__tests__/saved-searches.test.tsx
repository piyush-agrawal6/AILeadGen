import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {useState} from 'react';
import {SavedSearches} from '@/components/workflows/saved-searches';
import {SearchFilters} from '@/components/workflows/search-criteria';
import {initialPlan} from '@/components/workflows/types';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const saved={id:'search-1',name:'International clinics',revision:1,configuration:{...initialPlan(),countries:['United States','United Kingdom'],target:10}};
beforeEach(()=>{vi.mocked(request).mockReset();vi.mocked(request).mockImplementation(async path=>path==='/foundation/me'?{role:'OWNER'}:path.startsWith('/discovery/searches?')?{items:[saved],total:1}:saved)});
function Harness(){const [plan,setPlan]=useState(initialPlan());return <><SavedSearches value={plan} onChange={setPlan}/><SearchFilters value={plan} onChange={setPlan}/><div data-testid="plan">{JSON.stringify(plan)}</div></>}
function setup(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Harness/></QueryClientProvider>)}
it('loads reviewed targeting without creating or starting a discovery job',async()=>{setup();await screen.findByRole('option',{name:saved.name});fireEvent.change(screen.getByLabelText('Load saved search'),{target:{value:saved.id}});expect(screen.getByTestId('plan')).toHaveTextContent('United States');expect(screen.getByRole('status')).toHaveTextContent('loaded as a draft');expect(vi.mocked(request).mock.calls.filter(([path])=>path.includes('/workflow/'))).toHaveLength(0)});
it('saves selected criteria and keeps missing measurements explicit',async()=>{setup();fireEvent.click(screen.getByText('Company targeting filters'));fireEvent.change(screen.getByLabelText('Include keywords'),{target:{value:'clinic, independent'}});fireEvent.blur(screen.getByLabelText('Include keywords'));fireEvent.change(screen.getByLabelText('Minimum employees'),{target:{value:'10'}});fireEvent.change(screen.getByLabelText('Previously discovered companies'),{target:{value:'EXCLUDE'}});fireEvent.change(screen.getByLabelText('Search name'),{target:{value:'Clinics'}});fireEvent.click(screen.getByRole('button',{name:'Save as new search'}));await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('No discovery was started'));const call=vi.mocked(request).mock.calls.find(([path,options])=>path==='/discovery/searches'&&options?.method==='POST');const body=JSON.parse(String(call?.[1]?.body));expect(body.configuration.search_criteria).toMatchObject({keywords:['clinic','independent'],employee_min:10,existing_companies:'EXCLUDE'});expect(screen.getByText(/missing values are marked unknown/)).toBeVisible()});
