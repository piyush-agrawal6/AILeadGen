import {beforeEach,expect,it,vi} from 'vitest';
import {render,screen} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import Results from '@/components/legacy/intro-results';
import {EmailPreview} from '@/components/workflows/email-preview';
beforeEach(()=>vi.restoreAllMocks());
it('shows template attribution, permanent contacts and the shared PDF without inference',async()=>{
 const templates=Array.from({length:5},(_,i)=>({template_id:'PB_INTRO_0'+(i+1),sent:0,delivered:0,hard_bounced:0,replied:0,positive_reply:0,negative_reply:0,unsubscribe:0,meeting:0,positive_reply_rate:null}));
 const fetch=vi.fn(async()=>new Response(JSON.stringify({ready:true,contacted_recipients:32,pdf_version:'v1',templates,sources:[],delivery_note:'SMTP acceptance is not proof of delivery.'}),{headers:{'content-type':'application/json'}}));vi.stubGlobal('fetch',fetch);
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Results/></QueryClientProvider>);
 expect(await screen.findByText('PB_INTRO_05')).toBeTruthy();expect(screen.getByText('32')).toBeTruthy();expect(screen.getByRole('link',{name:/View PlaneByte/}).getAttribute('href')).toBe('/api/email/company-pdf/v1');expect(fetch.mock.calls.length).toBe(1);
});
it('previews the actual shared company attachment rather than claiming no PDF',()=>{
 render(<EmailPreview value={{from_name:'PlaneByte',from_address:'planebyte@gmail.com',to_address:'owner@example.com',subject:'A quick introduction from PlaneByte',rendered_html:'<p>Approved introduction</p>',rendered_text:'Approved introduction',report_id:null,pdf_attachment:{id:'PLANEBYTE_CAPABILITIES',version:'v1',filename:'PlaneByte Capabilities & Services.pdf',size_bytes:1000,url:'/api/email/company-pdf/v1'}}}/>);
 expect(screen.getByRole('link',{name:/View \/ Download Company PDF/}).getAttribute('href')).toBe('/api/email/company-pdf/v1');expect(screen.queryByText('No PDF attached')).toBeNull();
});
