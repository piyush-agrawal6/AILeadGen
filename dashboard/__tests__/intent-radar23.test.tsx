import {render,screen,fireEvent} from '@testing-library/react';
import {describe,it,expect,vi,beforeEach} from 'vitest';
import {SourceSelection,ScheduleControls} from '@/components/intent-radar/advanced-controls';
import {emptyIntentSearch,type IntentMonitor} from '@/lib/intent-radar';
const mocks=vi.hoisted(()=>({mutate:vi.fn(),mutateAsync:vi.fn()}));
vi.mock('@/components/intent-radar/provider',()=>({useRadarCapabilities:()=>({data:{can_write:true,can_manage:true,sources:[{id:'hacker_news',name:'Hacker News',state:'Available',coverage:'Recent bounded feeds',request_limit_per_check:22},{id:'stack_exchange',name:'Stack Exchange',state:'Requires approval',coverage:'Not authorized'}],usage:{automatic_schedules_enabled:true,minimum_schedule_hours:12}}}),useRadarRead:()=>({data:{items:[]}}),useRadarMutation:()=>({...mocks,isPending:false})}));
describe('Phase 2 source capabilities and schedule controls',()=>{
 beforeEach(()=>vi.clearAllMocks());
 it('unapproved sources cannot be selected and removing HN updates structured criteria',()=>{
  const onChange=vi.fn();render(<SourceSelection value={emptyIntentSearch()} onChange={onChange}/>);
  expect(screen.getByRole('checkbox',{name:/Stack Exchange/})).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox',{name:/Hacker News Available/}));
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({sources:[]}));
 });
 it('frequency policy hides six-hour scheduling and malformed timezone input stays editable',()=>{
  const monitor={id:'id',name:'Monitor',status:'Active',revision:3,schedule:{frequency:'Daily',timezone:'UTC'},next_run_at:'2026-11-11T10:00:00+00:00'} as IntentMonitor;
  render(<ScheduleControls monitor={monitor}/>);
  expect(screen.queryByRole('option',{name:'6 hours'})).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Schedule timezone'),{target:{value:'Invalid/Zone'}});
  expect(screen.getByLabelText('Schedule timezone')).toHaveValue('Invalid/Zone');
  expect(mocks.mutateAsync).not.toHaveBeenCalled();
 });
});
