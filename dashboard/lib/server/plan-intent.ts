import 'server-only';
import {createHmac,timingSafeEqual} from 'node:crypto';
import {cookies} from 'next/headers';
import {approvedPlan,type PlanCode} from '@/lib/plan-intent';
export const intentCookie='planebyte-plan-intent';
export function encodeIntent(plan:PlanCode,secret:string){const payload=Buffer.from(JSON.stringify({product:'intent-radar',plan,expires:Math.floor(Date.now()/1000)+7200})).toString('base64url');return payload+'.'+createHmac('sha256',secret).update(payload).digest('hex');}
export function decodeIntent(value:string|undefined,secret:string):PlanCode|null{if(!value||value.length>500||!secret)return null;const[payload,mac,...rest]=value.split('.');if(rest.length||!mac||!/^[a-f0-9]{64}$/.test(mac))return null;const expected=createHmac('sha256',secret).update(payload).digest();if(!timingSafeEqual(expected,Buffer.from(mac,'hex')))return null;try{const data=JSON.parse(Buffer.from(payload,'base64url').toString());return data.product==='intent-radar'&&Number.isInteger(data.expires)&&data.expires>Math.floor(Date.now()/1000)&&data.expires<=Math.floor(Date.now()/1000)+7200?approvedPlan(data.plan):null;}catch{return null;}}
export async function selectedPlan(){return decodeIntent((await cookies()).get(intentCookie)?.value,process.env.AUTH_SECRET||'');}
