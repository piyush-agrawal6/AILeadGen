import {randomUUID} from 'node:crypto';
import {AccountForm} from '@/components/auth/account-form';
import {readAccountCookie} from '@/lib/server/account-cookies';
import {createAccount} from '../account-actions';
import type { Metadata } from 'next';
import Link from 'next/link';
import { ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';
import { AuthState } from '@/components/auth/auth-state';
import { GoogleForm } from '@/components/auth/google-form';
import { googleSignIn } from '../login/actions';
import { currentUser } from '@/lib/server/session';
import { brand } from '@/lib/brand';
import { serverEnv } from '@/lib/server/env';
import { signupWithGoogle } from './actions';

export const metadata: Metadata = {
  title: 'Request access · PlaneByte',
  description: 'Request access to PlaneByte Intent Radar or join an existing workspace.',
};

export default async function Signup({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const user = await currentUser();
  const env = serverEnv();
  const pendingInvite=env.accounts?await readAccountCookie('planebyte-pending-invitation'):null;
  const initialInvitation=typeof pendingInvite?.invitation==='string'?pendingInvite.invitation:'';
  const registration =
    (env.publicRegistration || env.invitedRegistration) &&
    env.customerAccess &&
    !!env.termsVersion;
  const error = (await searchParams)?.error;

  return (
    <AuthState
      eyebrow="YOUR WORKSPACE"
      title="Join PlaneByte"
      description={
        registration
          ? env.publicRegistration
            ? env.accounts?'Create a workspace with your company email or verified work Google account.':'Create your independent workspace account using your verified Google identity.'
            : 'Public registration is closed. Use your private invitation code and the Google account named in your invitation.'
          : 'Public self-service registration is currently closed. Request workspace access from our team or continue with an already approved Google account.'
      }
    >
      {error === 'terms_required' && (
        <div className="pb-auth-alert" role="alert">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <span>Accept the current terms before continuing with Google.</span>
        </div>
      )}
      {error === 'registration_unavailable' && (
        <div className="pb-auth-alert" role="alert">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <span>Registration is not enabled. Your existing approved account remains available.</span>
        </div>
      )}
      {error === 'invitation_required' && (
        <div className="pb-auth-alert" role="alert">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <span>Enter a valid private invitation code before continuing.</span>
        </div>
      )}

      {user && process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED === 'true' ? (
        <div className="rounded-xl border border-border/80 bg-muted/40 p-4 text-left text-xs space-y-3">
          <div className="flex items-center gap-2 font-medium text-foreground">
            <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
            <span>Signed in as {user.email}</span>
          </div>
          <Link
            className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium shadow-sm py-2.5"
            href="/settings/workspaces"
          >
            Create company workspace
          </Link>
        </div>
      ) : registration ? (
        <><form action={signupWithGoogle} className="space-y-4 text-left">
          <label className="block text-xs font-medium text-foreground">
            Private invitation code{env.publicRegistration ? ' (optional)' : ''}
            <input
              className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 font-mono"
              name="invitation_token"
              defaultValue={initialInvitation}
              autoComplete="off"
              minLength={40}
              maxLength={100}
              placeholder="inv_..."
              required={!env.publicRegistration}
            />
          </label>
          <label className="flex items-start gap-2.5 text-xs text-muted-foreground cursor-pointer pt-1">
            <input
              type="checkbox"
              name="accept_terms"
              value="accepted"
              required
              className="mt-0.5 rounded border-border"
            />
            <span>
              I accept the{' '}
              <Link href="/terms" className="text-foreground underline underline-offset-2">
                Terms of Service
              </Link>{' '}
              and have reviewed the{' '}
              <Link href="/privacy" className="text-foreground underline underline-offset-2">
                Privacy Policy
              </Link>
              .
            </span>
          </label>
          <button
            className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium shadow-sm py-2.5 w-full mt-2"
            type="submit"
          >
            Create account with Google
          </button>
          <p className="pb-auth-fineprint text-[11px] text-muted-foreground text-center">
            Only your verified Google account is admitted. No workspace or mailbox access is inherited.
          </p>
        </form>{env.accounts&&<><div className="pb-auth-divider"><span>or use company email</span></div><AccountForm action={createAccount} kind="signup" requestId={randomUUID()} initialInvitation={initialInvitation} invitationRequired={!env.publicRegistration}/><p className="text-xs text-muted-foreground">Seven-day trial. No card or automatic renewal. Includes five searches, three AI operations and one manual monitor.</p></>}</>
      ) : (
        <div className="space-y-4">
          <a
            className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium shadow-sm py-2.5"
            href={`mailto:${brand.supportEmail}?subject=PlaneByte%20workspace%20access`}
          >
            <span>Request workspace access</span>
            <ExternalLink size={14} />
          </a>
          <p className="text-[11px] text-muted-foreground text-center">
            Opens your default email client. No account is created automatically.
          </p>

          <div className="pb-auth-divider">
            <span>Already have an approved account?</span>
          </div>

          <GoogleForm action={googleSignIn} />
        </div>
      )}

      {user && env.customerAccess && env.termsVersion && (
        <form action={signupWithGoogle} className="space-y-3 pt-3 text-left">
          <label className="flex items-start gap-2 text-xs text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              name="accept_terms"
              value="accepted"
              required
              className="mt-0.5 rounded border-border"
            />
            <span>
              I accept the current{' '}
              <Link href="/terms" className="text-foreground underline underline-offset-2">
                Terms of Service
              </Link>{' '}
              and have reviewed the{' '}
              <Link href="/privacy" className="text-foreground underline underline-offset-2">
                Privacy Policy
              </Link>
              .
            </span>
          </label>
          <button
            className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium py-2.5 w-full"
            type="submit"
          >
            Confirm current terms with Google
          </button>
        </form>
      )}

      <p className="pb-auth-fineprint text-[11px] text-muted-foreground text-center">
        Signing in never grants access to another company’s workspace. An invitation and authorized account are required.
      </p>
    </AuthState>
  );
}
