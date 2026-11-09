import type {Metadata} from 'next';
import Link from 'next/link';
import {AuthState} from '@/components/auth/auth-state';
import {GoogleForm} from '@/components/auth/google-form';
import {googleSignIn} from '../login/actions';
import {currentUser} from '@/lib/server/session';
import {brand} from '@/lib/brand';
import {serverEnv} from '@/lib/server/env';
import {signupWithGoogle} from './actions';
export const metadata:Metadata={title:'Request access · PlaneByte'};
export default async function Signup({searchParams}:{searchParams:Promise<{error?:string}>}){
  const user=await currentUser(),env=serverEnv();
  const registration=(env.publicRegistration||env.invitedRegistration)&&env.customerAccess&&!!env.termsVersion;
  const error=(await searchParams)?.error;
  return <AuthState eyebrow="YOUR NEXT WORKSPACE" title="Join PlaneByte" description={registration?(env.publicRegistration?'Create your independent account using your verified Google identity.':'Public registration remains closed. Use your private invitation code and the Google account named in your invitation.'):'Public self-service registration is not available yet. Request access from our team or continue with an already approved Google account.'}>
    {error==='terms_required'&&<p role="alert">Accept the current terms before continuing with Google.</p>}
    {error==='registration_unavailable'&&<p role="alert">Registration is not enabled. Your existing approved account remains available.</p>}
    {error==='invitation_required'&&<p role="alert">Enter a valid private invitation code before continuing.</p>}
    {user&&process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED==='true'?<div className="auth-information"><strong>You’re signed in as {user.email}.</strong><Link className="auth-primary-button mt-4" href="/settings/workspaces">Create your company workspace</Link></div>:registration?<form action={signupWithGoogle} className="space-y-5"><label className="block text-sm">Private invitation code{env.publicRegistration?' (optional)':''}<input className="control mt-2 w-full" name="invitation_token" autoComplete="off" minLength={40} maxLength={100} required={!env.publicRegistration}/></label><label className="flex gap-3 text-sm"><input type="checkbox" name="accept_terms" value="accepted" required/><span>I accept the <Link href="/terms" className="underline">Terms of Service</Link> and have reviewed the <Link href="/privacy" className="underline">Privacy Policy</Link>.</span></label><button className="auth-primary-button" type="submit">Create account with Google</button><p className="auth-fineprint">Only your verified Google account is admitted. No workspace or mailbox access is inherited. Invitations require a separate acceptance after sign-in.</p></form>:<><a className="auth-primary-button" href={'mailto:'+brand.supportEmail+'?subject=PlaneByte%20workspace%20access'}>Request workspace access <span aria-hidden="true">↗</span></a><p className="auth-fineprint">Opens your email app. No request or account is submitted automatically.</p><div className="auth-access-divider"><span>Already approved?</span></div><GoogleForm action={googleSignIn}/></>}
    {user&&env.customerAccess&&env.termsVersion&&<form action={signupWithGoogle} className="space-y-4"><label className="flex gap-3 text-sm"><input type="checkbox" name="accept_terms" value="accepted" required/><span>I accept the current <Link href="/terms" className="underline">Terms of Service</Link> and have reviewed the <Link href="/privacy" className="underline">Privacy Policy</Link>.</span></label><button className="auth-primary-button" type="submit">Confirm current terms with Google</button></form>}
    <p className="auth-fineprint">Signing in never grants access to another company’s workspace. An invitation and your authorized account are required to join a team.</p>
  </AuthState>;
}
