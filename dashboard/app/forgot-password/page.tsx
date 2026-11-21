import {challengeSiteKey} from '@/lib/server/turnstile';
import {AccountForm} from '@/components/auth/account-form';
import {recoverAccount} from '../account-actions';
import {serverEnv} from '@/lib/server/env';
import type { Metadata } from 'next';
import Link from 'next/link';
import {
  KeyRound,
  UsersRound,
  ShieldAlert,
  Mail,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { LegalDocument } from '@/components/auth/legal-document';
import { brand } from '@/lib/brand';

export const metadata: Metadata = {
  title: 'Sign-in & Access Help · PlaneByte',
  description: 'Recover account access and troubleshoot Google sign-in or workspace permissions.',
};

export default function ForgotPassword() {
  return (
    <LegalDocument
      title="Sign-in & access help"
      summary={serverEnv().accounts?"Recover your PlaneByte password or get help with Google sign-in and workspace access.":"PlaneByte uses verified Google OAuth for enterprise authentication. Review the scenarios below to resolve common access, invitation, or account issues."}
      activeTab="help"
    >
      {serverEnv().accounts&&<section className="mb-8 max-w-md"><h2 className="text-lg font-semibold mb-3">Recover your PlaneByte password</h2><AccountForm action={recoverAccount} kind="recovery" challengeKey={challengeSiteKey()}/></section>}
      <section className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-1">
            Common sign-in scenarios
          </h2>
          <p className="text-sm text-muted-foreground">
            Select the situation that best matches what you are experiencing.
          </p>
        </div>

        <div className="pb-troubleshoot-grid text-left">
          {/* Scenario 1: Google Account Access */}
          <div className="pb-troubleshoot-card">
            <div className="pb-troubleshoot-header">
              <KeyRound size={16} className="text-primary shrink-0" />
              <span>Google password issue</span>
            </div>
            <p className="pb-troubleshoot-desc">
              If your Google account is locked or you forgot your Google password, use Google’s official recovery tool to regain access.
            </p>
            <a
              className="pb-troubleshoot-action"
              href="https://accounts.google.com/signin/recovery"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span>Google Account Recovery</span>
              <ExternalLink size={12} />
            </a>
          </div>

          {/* Scenario 2: Multiple Profiles / Wrong Account */}
          <div className="pb-troubleshoot-card">
            <div className="pb-troubleshoot-header">
              <UsersRound size={16} className="text-primary shrink-0" />
              <span>Wrong Google profile</span>
            </div>
            <p className="pb-troubleshoot-desc">
              Your browser may be trying to sign in with a personal or inactive Google profile. Open PlaneByte in a private or incognito window to pick the correct corporate account.
            </p>
            <span className="text-[11px] text-muted-foreground/80 mt-auto pt-1 font-mono">
              Shortcut: Open Incognito window
            </span>
          </div>

          {/* Scenario 3: Workspace Authorization Denied */}
          <div className="pb-troubleshoot-card">
            <div className="pb-troubleshoot-header">
              <ShieldAlert size={16} className="text-amber-500 shrink-0" />
              <span>Access denied / No workspace</span>
            </div>
            <p className="pb-troubleshoot-desc">
              Google sign-in works, but your email isn’t authorized for this workspace yet. Ask your workspace administrator to grant access to your account.
            </p>
            <a
              className="pb-troubleshoot-action"
              href={`mailto:${brand.supportEmail}?subject=PlaneByte%20workspace%20authorization`}
            >
              <span>Ask workspace administrator</span>
              <ArrowRight size={12} />
            </a>
          </div>

          {/* Scenario 4: Need Invitation / New Account */}
          <div className="pb-troubleshoot-card">
            <div className="pb-troubleshoot-header">
              <Mail size={16} className="text-primary shrink-0" />
              <span>Need an invitation</span>
            </div>
            <p className="pb-troubleshoot-desc">
              Public self-service registration is closed during preview. You need an invitation from your team administrator or an approved corporate email.
            </p>
            <a
              className="pb-troubleshoot-action"
              href={`mailto:${brand.supportEmail}?subject=PlaneByte%20workspace%20access%20request`}
            >
              <span>Request workspace access</span>
              <ExternalLink size={12} />
            </a>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-2">
          <div className="flex flex-col sm:flex-row gap-3 max-w-md">
            <Link
              href="/login"
              className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium shadow-sm py-2.5"
            >
              <span>Try signing in again</span>
              <ArrowRight size={15} />
            </Link>
            <a
              href={`mailto:${brand.supportEmail}?subject=PlaneByte%20sign-in%20assistance`}
              className="pb-auth-google-btn justify-center border-border bg-card text-foreground hover:bg-muted/50 text-center font-medium py-2.5"
            >
              <span>Contact support</span>
            </a>
          </div>
        </div>
      </section>

      {/* Security & Access Notice */}
      <section className="pb-legal-section mt-10">
        <h2>Enterprise security and session lifetime</h2>
        <p>
          PlaneByte authentication sessions automatically expire after 8 hours.
          Workspace permissions, role assignments, and team memberships are managed server-side and never leak across tenant boundaries.
          Signing in with Google does not grant PlaneByte access to your personal files, Google Drive, or Gmail inbox without separate explicit integration consent.
        </p>
      </section>
    </LegalDocument>
  );
}
