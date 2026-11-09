import "server-only";
import {cookies} from "next/headers";
import {createHash,createHmac,randomUUID,timingSafeEqual} from "node:crypto";
import {serverEnv} from "./env";

export const signupCookie="planebyte-signup-consent";
export const invitationCookie="planebyte-invitation-review";
type Consent={version:string;accepted_at:number;nonce:string;invitation_token?:string};
export function encodeConsent(value:Consent,secret:string){const data=Buffer.from(JSON.stringify(value)).toString("base64url");return data+"."+createHmac("sha256",secret).update(data).digest("hex");}
export function decodeConsent(value:string,secret:string):Consent|null{
  try{
    if(value.length>2000||secret.length<32)return null;
    const [data,signature,...extra]=value.split(".");if(extra.length||!data||!signature||!/^[a-f0-9]{64}$/.test(signature))return null;
    const expected=createHmac("sha256",secret).update(data).digest();if(!timingSafeEqual(expected,Buffer.from(signature,"hex")))return null;
    const result=JSON.parse(Buffer.from(data,"base64url").toString());
    const age=Math.floor(Date.now()/1000)-result.accepted_at;
    if(result.invitation_token!==undefined&&(typeof result.invitation_token!=="string"||! /^[A-Za-z0-9_-]{40,100}$/.test(result.invitation_token)))return null;
    return typeof result.version==="string"&&result.version.length>0&&result.version.length<=100&&Number.isInteger(result.accepted_at)&&age>=0&&age<=600&&typeof result.nonce==="string"&&/^[a-f0-9-]{36}$/.test(result.nonce)?result:null;
  }catch{return null;}
}

export async function admitGoogle(profile:{email:string;sub:string;email_verified:unknown;name?:string}){
  const env=serverEnv();if(!env.customerAccess||!env.termsVersion||env.secret.length<32||profile.email_verified!==true)return false;
  const jar=await cookies(),ticket=decodeConsent(jar.get(signupCookie)?.value||"",env.secret);
  const actor=profile.email.trim().toLowerCase(),path="/api/organization/admission/google";
  const body=JSON.stringify({email:actor,google_subject:profile.sub,client_id:process.env.AUTH_GOOGLE_ID||"",email_verified:true,name:profile.name||"",...(ticket?{terms_version:ticket.version,accepted_at:ticket.accepted_at,acceptance_nonce:ticket.nonce,...(ticket.invitation_token?{invitation_token:ticket.invitation_token}:{})}:{})});
  const timestamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID();
  const canonical=[timestamp,nonce,"POST",path,createHash("sha256").update(body).digest("hex"),actor].join("\n");
  try{
    const response=await fetch(env.apiUrl.replace(/\/$/,"")+path,{method:"POST",body,headers:{"content-type":"application/json","x-le-user":actor,"x-le-timestamp":timestamp,"x-le-nonce":nonce,"x-le-signature":createHmac("sha256",env.secret).update(canonical).digest("hex")},cache:"no-store",redirect:"error",signal:AbortSignal.timeout(5000)});
    if(!response.ok)return false;const result=await response.json();
    if(result.user_id!==actor||result.status!=="ACTIVE")return false;
    if(ticket){
      if(ticket.invitation_token)jar.set(invitationCookie,encodeConsent(ticket,env.secret),{httpOnly:true,secure:env.production,sameSite:"lax",path:"/accept-invitation",maxAge:600});
      jar.delete(signupCookie);
    }
    return true;
  }catch{return false;}
}
