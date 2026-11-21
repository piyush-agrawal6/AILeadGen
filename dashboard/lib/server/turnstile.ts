import 'server-only';

export function challengeSiteKey(): string|undefined {
  return process.env.TURNSTILE_ENFORCED==='true' ? process.env.TURNSTILE_SITE_KEY || '' : undefined;
}

export async function verifyChallenge(form:FormData,action:'signup'|'recovery'):Promise<boolean>{
  if(process.env.TURNSTILE_ENFORCED!=='true')return true;
  const token=form.get('cf-turnstile-response'), secret=process.env.TURNSTILE_SECRET_KEY;
  if(!secret||!challengeSiteKey()||typeof token!=='string'||!token.trim()||token.length>2048)return false;
  try{
    const response=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',body:new URLSearchParams({secret,response:token}),redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)return false;
    const result=await response.json();
    return result.success===true && result.hostname==='app.planebyte.com' && result.action===action;
  }catch{return false;}
}
