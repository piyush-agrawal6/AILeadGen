"use client";
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {useSearchParams,useRouter} from 'next/navigation';
import {useRadarMutation} from './provider';
import {ErrorState,PageHeading} from './ui';

export function GitHubOAuthCallbackView(){
  const params=useSearchParams(),router=useRouter(),mutation=useRadarMutation();
  const [status,setStatus]=useState<'pending'|'done'|'error'>('pending');
  const [message,setMessage]=useState('Verifying GitHub authorization with PlaneByte…');
  const started=useRef(false);

  useEffect(()=>{
    if(started.current)return;
    started.current=true;
    const code=params.get('code')||'',state=params.get('state')||'',installationId=params.get('installation_id')||undefined,oauthError=params.get('error_description')||params.get('error');
    if(oauthError){setStatus('error');setMessage('GitHub authorization was cancelled or denied: '+oauthError);return;}
    if(!code||!state){setStatus('error');setMessage('Missing required GitHub OAuth code or state parameter.');return;}
    mutation.mutateAsync({path:'/sources/github/oauth/callback',method:'POST',body:{code,state,installation_id:installationId}})
      .then(()=>{setStatus('done');setMessage('GitHub installation connected to your workspace. Redirecting…');setTimeout(()=>router.replace('/intent-radar/integrations'),900);})
      .catch((e:Error)=>{setStatus('error');setMessage(e.message||'Could not complete GitHub authorization.');});
  },[params,mutation,router]);

  return <div className="ir-page"><PageHeading title="GitHub Connection" description="Completing secure workspace-scoped GitHub App authorization."/><section className="ir-panel ir-form-section">{status==='error'?<ErrorState message={message}/>:<p role="status">{message}</p>}<div className="ir-actions"><Link className="ir-button ir-primary" href="/intent-radar/integrations">Return to Integrations</Link></div></section></div>;
}
