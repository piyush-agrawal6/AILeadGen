'use client';
import Script from 'next/script';
import {useEffect,useRef,useState} from 'react';

type Widget={render:(el:HTMLElement,options:Record<string,unknown>)=>string;remove:(id:string)=>void};
export function Turnstile({siteKey,action,result}:{siteKey:string;action:string;result:unknown}){
  const el=useRef<HTMLDivElement>(null),[ready,setReady]=useState(false),[error,setError]=useState(false),[attempt,setAttempt]=useState(0);
  useEffect(()=>{
    const api=(window as Window & {turnstile?:Widget}).turnstile;
    if(!ready||!el.current||!api||!siteKey)return;
    const id=api.render(el.current,{sitekey:siteKey,action,size:'flexible',theme:'auto','refresh-expired':'auto',callback:()=>setError(false),'error-callback':()=>setError(true)});
    return ()=>api.remove(id);
  },[ready,siteKey,action,attempt,result]);
  return <section aria-label="Account security check"><Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onReady={()=>setReady(true)} onError={()=>setError(true)}/><div ref={el}/>{(!siteKey||error)&&<p role="alert">Security check unavailable. {ready?<button type="button" className="underline" onClick={()=>setAttempt(n=>n+1)}>Retry</button>:<button type="button" className="underline" onClick={()=>location.reload()}>Reload page</button>}</p>}</section>;
}
