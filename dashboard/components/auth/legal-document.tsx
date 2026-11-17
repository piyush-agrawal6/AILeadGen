import Link from 'next/link';
import { ArrowLeft, ArrowUpRight, ShieldAlert, HelpCircle } from 'lucide-react';
import { PlaneByteBrand } from './brand';
import { AuthThemeToggle } from './theme-toggle';
import { AuthBackgroundScene } from './auth-background-scene';

export function LegalDocument({
  title,
  summary,
  activeTab: propActiveTab,
  eyebrow,
  publishedVersion,
  children,
}: {
  title: string;
  summary: string;
  activeTab?: 'terms' | 'privacy' | 'refund' | 'cancellation' | 'help';
  eyebrow?: string;
  publishedVersion?: string;
  children: React.ReactNode;
}) {
  const activeTab =
    propActiveTab ||
    (title.toLowerCase().includes('terms')
      ? 'terms'
      : title.toLowerCase().includes('privacy')
      ? 'privacy'
      : 'help');

  const defaultEyebrow =
    eyebrow ||
    (activeTab === 'help'
      ? 'PlaneByte · Access & Authentication'
      : 'PlaneByte · Legal Information');

  return (
    <div className="pb-auth-ambient-wrapper min-h-screen bg-background text-foreground flex flex-col">
      {/* Ambient background glows */}
      <div className="pb-auth-glow-container" aria-hidden="true">
        <div className="pb-auth-glow-1" />
        <div className="pb-auth-glow-2" />
        <div className="pb-auth-glow-3" />
        <div className="pb-auth-grid-pattern" />
      </div>

      {/* Floating 3D Geometric Cubes & Scattered Pixel-Word Background Scene */}
      <AuthBackgroundScene variant="legal" />

      {/* Sticky Header with Navigation Tabs */}
      <header className="sticky top-0 z-30 w-full border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-4">
          <Link href="/login" aria-label="PlaneByte home" className="pb-auth-brand">
            <PlaneByteBrand />
          </Link>

          {/* Center Tabs: Terms of Service | Privacy Policy | Sign-in Help */}
          <nav aria-label="Legal & assistance selection" className="pb-legal-header-tabs hidden sm:flex">
            <Link
              href="/terms"
              className={`pb-legal-tab ${activeTab === 'terms' ? 'is-active' : ''}`}
            >
              Terms of Service
            </Link>
            <Link
              href="/privacy"
              className={`pb-legal-tab ${activeTab === 'privacy' ? 'is-active' : ''}`}
            >
              Privacy Policy
            </Link>
            <Link
              href="/forgot-password"
              className={`pb-legal-tab ${activeTab === 'help' ? 'is-active' : ''}`}
            >
              Sign-in Help
            </Link>
          </nav>

          {/* Right Actions: Back to sign in + Theme Toggle */}
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground py-1.5 px-3 rounded-lg border border-border/70 hover:bg-muted/50 transition-colors"
            >
              <ArrowLeft size={14} />
              <span>Back to sign in</span>
            </Link>
            <AuthThemeToggle />
          </div>
        </div>

        {/* Mobile Tab Selector */}
        <div className="sm:hidden px-6 pb-3 pt-1 flex justify-center">
          <nav aria-label="Legal & assistance selection" className="pb-legal-header-tabs w-full justify-center">
            <Link
              href="/terms"
              className={`pb-legal-tab flex-1 text-center ${activeTab === 'terms' ? 'is-active' : ''}`}
            >
              Terms
            </Link>
            <Link
              href="/privacy"
              className={`pb-legal-tab flex-1 text-center ${activeTab === 'privacy' ? 'is-active' : ''}`}
            >
              Privacy
            </Link>
            <Link
              href="/forgot-password"
              className={`pb-legal-tab flex-1 text-center ${activeTab === 'help' ? 'is-active' : ''}`}
            >
              Sign-in Help
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Document / Content Container */}
      <main className="pb-legal-container relative z-10 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-primary">
          {defaultEyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl text-foreground">
          {title}
        </h1>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground">
          {summary}
        </p>

        {/* Notice Banner */}
        {activeTab === 'help' ? (
          <div className="pb-legal-notice-banner flex items-start gap-3">
            <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <strong className="block text-xs font-semibold text-foreground mb-1">
                Google Single Sign-On (SSO) Authentication
              </strong>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Your PlaneByte workspace credentials are authenticated directly through your verified Google account.
                PlaneByte never requests, manages, or stores your Google account password.
              </p>
            </div>
          </div>
        ) : publishedVersion ? (
          <div className="pb-legal-notice-banner text-xs text-muted-foreground">
            Published version: {publishedVersion}. Review all applicable policies before creating an account or purchasing access.
          </div>
        ) : (
          <div className="pb-legal-notice-banner flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-xs font-semibold text-foreground mb-1">
                Development Review Copy · Updated 7 November 2026
              </strong>
              <p className="text-xs text-muted-foreground leading-relaxed">
                This document provides product information for review during development and is not an approved public-launch legal agreement.
                For official company policies, visit{' '}
                <a
                  href="https://planebyte.com/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-primary"
                >
                  planebyte.com/terms
                </a>{' '}
                and{' '}
                <a
                  href="https://planebyte.com/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-primary"
                >
                  planebyte.com/privacy
                </a>
                .
              </p>
            </div>
          </div>
        )}

        {/* Document Body / Content */}
        <article className="pb-legal-article mt-8">{children}</article>

        {/* Document Footer */}
        <footer className="mt-16 pt-8 border-t border-border/80 flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-foreground hover:underline inline-flex items-center gap-1 font-medium"
            >
              <ArrowLeft size={13} />
              <span>Back to sign in</span>
            </Link>
            <span>•</span>
            <a
              href="https://planebyte.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
            >
              <span>PlaneByte website</span>
              <ArrowUpRight size={12} />
            </a>
          </div>
          <div>
            <span>Questions? </span>
            <a
              href="mailto:contact@planebyte.com"
              className="text-primary hover:underline"
            >
              contact@planebyte.com
            </a>
          </div>
        </footer>
      </main>
    </div>
  );
}
