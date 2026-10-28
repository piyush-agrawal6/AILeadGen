import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
test('live preview requires explicit Send Live Email and respects message tracking choices',async({page,context})=>{
 const token=await encode({token:{sub:'founder@leadengine.example',email:'founder@leadengine.example'},secret:'brand-local-preview-secret-not-for-production-123456789',salt:'authjs.session-token',maxAge:900});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13001',httpOnly:true,sameSite:'Lax'}]);
 let sends=0;const business={id:1,name:'Live flow fixture',city:'London',country:'United Kingdom',vertical:'hospitality',public_email:'public@qa.example',website:'https://qa.example'};
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;let data:unknown={};
  if(path==='/api/sales/outreach')data={items:[],counts:{ready:1,today:0,overdue:0,replied:0,meeting:0,proposal:0},total:0,total_pages:1};
  else if(path==='/api/leads/1')data={business,profile:null,lighthouse:null,findings:[],contacts:[]};
  else if(path==='/api/leads/1/workspace')data={id:'qa',lead_status:'READY_TO_CONTACT',notes:[],opportunity:null,social_profiles:[]};
  else if(path==='/api/sales/leads/1')data={suppressed:false,currency:'GBP',followups:[],activities:[],lists:[],threads:[]};
  else if(path==='/api/sales/lists'||path==='/api/users')data=[];
  else if(path==='/api/client-reports')data={items:[]};
  else if(path==='/api/email/leads/1/compose')data={recipients:['public@qa.example'],reports:[],templates:[],suppressed:false,test_mode:false,from_address:'rajendra@planebyte.com',effective_test_recipient:null,sending_enabled:true,can_send:true,tracking:{track_opens:true,track_clicks:true}};
  else if(path==='/api/email/leads/1/preview'){const payload=route.request().postDataJSON();expect(payload.track_opens).toBe(false);expect(payload.track_clicks).toBe(true);data={...payload,preview_token:'b'.repeat(64),from_address:'rajendra@planebyte.com',to_address:'public@qa.example',intended_to:'public@qa.example',test_mode:false};}
  else if(path==='/api/email/leads/1/send'){sends++;const payload=route.request().postDataJSON();expect(payload.confirmation).toBe('SEND');expect(payload.to_address).toBe('public@qa.example');data={status:'SENT',test_mode:false};}
  await route.fulfill({json:data});
 });
 await page.goto('/leads/1');await page.getByRole('button',{name:'Compose email',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('LIVE OUTREACH');
 await page.getByLabel('Subject',{exact:true}).fill('A factual review');await page.getByLabel('Body',{exact:true}).fill('A reviewed message with https://planebyte.com');await page.getByRole('checkbox',{name:'Open signals',exact:true}).uncheck();
 await page.getByRole('button',{name:'Preview email',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('To: public@qa.example');await expect(page.getByRole('button',{name:'Send Live Email',exact:true})).toBeVisible();expect(sends).toBe(0);
 await page.getByRole('button',{name:'Send Live Email',exact:true}).click();await expect(page.getByRole('status')).toContainText('Sent.');expect(sends).toBe(1);
});

test('opaque tracking surface is public while the workspace remains private',async({request})=>{
 const publicResponse=await request.get('/t/o/'+'a'.repeat(43)+'.gif');expect(publicResponse.url()).not.toContain('/login');expect([200,503]).toContain(publicResponse.status());
 const privateResponse=await request.get('/outreach');expect(privateResponse.url()).toContain('/login');
});
