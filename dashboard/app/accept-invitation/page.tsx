import type {Metadata} from 'next';
import {AuthState} from '@/components/auth/auth-state';
import Link from 'next/link';
import {cookies} from 'next/headers';
import {currentUser} from '@/lib/server/session';
import {serverEnv} from '@/lib/server/env';
import {decodeConsent,invitationCookie} from '@/lib/server/admission';
import {InvitationResponse} from '@/components/workspaces/invitations';
export const metadata:Metadata={title:'Workspace invitation · PlaneByte'};
export default async function Invitation(){
 const enabled=process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED==='true';
 const user=enabled?await currentUser():null,env=serverEnv();
 const ticket=user?decodeConsent((await cookies()).get(invitationCookie)?.value||'',env.secret):null;
 if(enabled&&user?.email)return <AuthState eyebrow="WORK BETTER, TOGETHER" title="Join your team" description="Review your workspace invitation using your signed-in account."><InvitationResponse email={user.email} initialToken={ticket?.invitation_token}/><a className="auth-back" href="/">Open workspace</a></AuthState>;
 if(enabled&&env.invitedRegistration&&env.customerAccess&&env.termsVersion)return <AuthState eyebrow="WORK BETTER, TOGETHER" title="Join your team" description="Keep your private invitation code. Create your account using the verified Google identity named in your invitation, then explicitly accept the workspace invitation."><Link href="/signup" className="auth-primary-button">Continue with your invitation</Link></AuthState>;
 return <AuthState eyebrow="WORK BETTER, TOGETHER" title="Let’s find your workspace" description={enabled?'Sign in with the Google account named in your invitation, then reopen your invitation link.':'We can’t accept this invitation in the current deployment.'}><div className="auth-information" role="status"><strong>{enabled?'Sign in to review your invitation.':'Invitation acceptance isn’t enabled yet.'}</strong><p>Ask your workspace administrator to confirm your access, then sign in with the Google account associated with your workspace.</p></div><p className="auth-fineprint">No workspace membership has been changed. Public registration remains unavailable in this deployment.</p></AuthState>;
}
