import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { PlaneByteBrand } from './brand';
import { AuthThemeToggle } from './theme-toggle';
import { AuthBackgroundScene } from './auth-background-scene';
import { leadEngineEnabled } from '@/lib/product-availability';

export function AuthFrame({ children }: { children: React.ReactNode }) {
  const leadAvailable = leadEngineEnabled(process.env.LEAD_ENGINE_AVAILABLE);

  return (
    <div className="heysow-auth pb-auth-ambient-wrapper">
      <a
        className="auth-skip sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 z-50 px-4 py-2 bg-background border border-primary rounded-md shadow-md text-sm font-medium"
        href="#authentication"
      >
        Skip to sign in
      </a>

      {/* Ambient background glows and grid texture */}
      <div className="pb-auth-glow-container" aria-hidden="true">
        <div className="pb-auth-glow-1" />
        <div className="pb-auth-glow-2" />
        <div className="pb-auth-glow-3" />
        <div className="pb-auth-grid-pattern" />
      </div>

      {/* Floating 3D Geometric Cubes & Scattered Pixel-Word Background Scene */}
      <AuthBackgroundScene variant="auth" />

      {/* Minimal Top Header */}
      <header className="pb-auth-header">
        <Link className="pb-auth-brand" href="/login" aria-label="PlaneByte home">
          <PlaneByteBrand />
        </Link>
        <div className="pb-auth-header-actions">
          <a
            href="https://planebyte.com"
            target="_blank"
            rel="noopener noreferrer"
            className="pb-auth-nav-link hidden sm:inline-flex"
          >
            <span>planebyte.com</span>
            <ArrowUpRight size={13} className="opacity-70" />
          </a>
          <AuthThemeToggle />
        </div>
      </header>

      {/* Hidden mobile brand header for test and responsive fallback */}
      <header className="auth-mobile-brand" style={{ display: 'none' }}>
        <Link href="/login" aria-label="PlaneByte home">
          <PlaneByteBrand />
        </Link>
      </header>

      {/* Main Centered Content */}
      <main id="authentication" className="pb-auth-main" tabIndex={-1}>
        <div className="pb-auth-trust-pill" aria-hidden="true">
          <span className="pb-auth-trust-dot" />
          <span>
            {leadAvailable ? 'Pipeline Discovery & Outreach' : 'Intent Radar · Growth Intelligence'}
          </span>
        </div>

        <div className="pb-auth-card">{children}</div>

        <div className="text-xs text-muted-foreground mt-5 text-center max-w-sm leading-relaxed pb-auth-discovery-hint">
          {leadAvailable ? (
            <span>Discover relevant companies</span>
          ) : (
            <span>Discover relevant conversations</span>
          )}
          <span className="block mt-1 text-[11px] opacity-75">
            Understand customer needs. Find opportunities worth pursuing.
          </span>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="pb-auth-footer auth-footer">
        <span>© {new Date().getFullYear()} PlaneByte, Inc. All rights reserved.</span>
        <nav aria-label="Legal" className="pb-auth-footer-links">
          <a href="https://planebyte.com" target="_blank" rel="noopener noreferrer">
            Website
          </a>
          <Link href="/terms">Terms of Service</Link>
          <Link href="/privacy">Privacy Policy</Link>
          <Link href="/forgot-password">Sign-in Help</Link>
        </nav>
      </footer>
    </div>
  );
}
