import {render,screen,fireEvent} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {ConversationChart,growthQuery} from '@/components/intent-radar/growth-experience';
import {emptyGrowthScope} from '@/lib/growth';
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn()}),useSearchParams:()=>new URLSearchParams()}));
vi.mock('@/components/intent-radar/provider',()=>({useRadarRead:()=>({}),useRadarCapabilities:()=>({}),useRadarMutation:()=>({})}));
it('does not fabricate missing history and provides keyboard-accessible exact chart counts',()=>{
 const rendered=render(<ConversationChart rows={[]}/>);expect(screen.getByText('No conversation history yet')).toBeVisible();
 rendered.rerender(<ConversationChart rows={[{day:'2026-11-13',conversations:3},{day:'2026-11-12',conversations:2}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'2026-11-13: 3 conversations'}));expect(screen.getByRole('status')).toHaveTextContent('2026-11-13: 3 collected conversations');expect(screen.getByText(/Missing days are not proof of zero market activity/)).toBeVisible();
});
it('keeps selected evidence filters in the request without adding workspace authority',()=>{
 const query=new URLSearchParams(growthQuery({...emptyGrowthScope(),search:'C++ & workflow',sources:['Hacker News'],competitor_id:'reviewed-id'}));
 expect(query.get('search')).toBe('C++ & workflow');expect(query.getAll('source')).toEqual(['Hacker News']);expect(query.get('competitor_id')).toBe('reviewed-id');expect(query.has('organization_id')).toBe(false);
});
