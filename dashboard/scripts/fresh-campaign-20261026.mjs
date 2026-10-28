import {chromium} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import {randomUUID} from 'node:crypto';
import fs from 'node:fs/promises';
const origin='https://leads.planebyte.com',file='../docs/fresh-campaign-20261026.json';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext(),salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 const token=await encode({token:{sub:email,email,name:'PlaneByte'},secret:process.env.AUTH_SECRET,salt,maxAge:900});
 await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const api=async(path,method='GET',data)=>{const response=await context.request.fetch(origin+'/api'+path,{method,data,headers:{Origin:origin},timeout:180000});const body=await response.json();if(!response.ok())throw new Error('Request failed '+response.status()+': '+(typeof body.detail==='string'?body.detail:'check server'));return body;};
 let state=await fs.readFile(file,'utf8').then(JSON.parse).catch(()=>null);
 if(!state){const reset=JSON.parse(await fs.readFile('../docs/workspace-reset-20261026.json','utf8'));if(!reset.completed)throw new Error('Reset has not completed');state={configuration:{cities:['London, United Kingdom','Manchester, United Kingdom'],verticals:['hospitality'],opportunities:['WEBSITE','SEO','SECURITY'],quality:'balanced',business_scales:['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL'],results:'new',target:200,lighthouse_enabled:true,social_enrichment_enabled:true,social_activity_enabled:true,request_id:randomUUID()}};await fs.writeFile(file,JSON.stringify(state,null,2));}
 if(!state.campaign)state.campaign=await api('/campaigns','POST',state.configuration);
 state.campaign=await api('/campaigns/'+state.configuration.request_id);state.checked_at=new Date().toISOString();await fs.writeFile(file,JSON.stringify(state,null,2));
 console.log(JSON.stringify({campaign_id:state.campaign.id,status:state.campaign.status,target:state.campaign.target_total,runs:state.campaign.runs}));
}catch(e){console.error(e.name+': '+String(e.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
