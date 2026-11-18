'use client';
import React from 'react';
import { Check, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ONBOARDING_STEPS, type SaveStatus, type StepKey } from './types';

const HERO_COPY: Record<Exclude<StepKey, 'ready'>, { heading: string; subheading: string }> = {
  welcome: {
    heading: "Let's understand your business",
    subheading: "Add your website and we'll prepare a business profile you can review."
  },
  company: {
    heading: 'Review your business profile',
    subheading: 'Confirm your company details, offerings, positioning, and target market.'
  },
  icp: {
    heading: 'Choose your ideal customers',
    subheading: 'Select the customer segments that fit best and choose one primary ICP.'
  },
  research: {
    heading: 'Set up your research signals',
    subheading: 'Review buying-intent phrases, exclusions, and available signal sources.'
  },
  plan: {
    heading: 'Choose your plan',
    subheading: 'Start with a 3-day free trial ($0 today) or subscribe directly to enter Intent Radar.'
  }
};

export function StepProgress({
  currentView,
  currentStepNum,
  onSelectStep
}: {
  currentView: StepKey;
  currentStepNum: number;
  onSelectStep: (step: StepKey) => void;
}) {
  return (
    <nav aria-label="Onboarding Progress" className="ai-onboarding-rail-container">
      <ol className="ai-onboarding-rail">
        {ONBOARDING_STEPS.map(s => {
          const isCompleted = currentStepNum > s.stepNum;
          const isCurrent = currentView === s.key;
          return (
            <li
              key={s.key}
              className={`ai-rail-step ${isCurrent ? 'is-active' : ''} ${isCompleted ? 'is-done' : ''}`}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <button
                type="button"
                className="ai-rail-btn"
                disabled={!isCompleted && !isCurrent}
                onClick={() => {
                  if (isCompleted) onSelectStep(s.key);
                }}
              >
                <span className="ai-rail-indicator" aria-hidden="true">
                  {isCompleted ? <Check size={12} strokeWidth={3} /> : s.stepNum}
                </span>
                <span className="ai-rail-label">
                  <span className="ai-rail-num">Step {s.stepNum}</span>
                  <span className="ai-rail-text">{s.title}</span>
                </span>
              </button>
              {s.stepNum < 5 && <div className="ai-rail-divider" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function OnboardingHero({
  view,
  currentStepNum,
  canEdit,
  pending,
  saveStatus,
  onSelectStep,
  onSkip
}: {
  view: Exclude<StepKey, 'ready'>;
  currentStepNum: number;
  canEdit: boolean;
  pending: boolean;
  saveStatus: SaveStatus;
  onSelectStep: (step: StepKey) => void;
  onSkip: () => void;
}) {
  const copy = HERO_COPY[view];
  return (
    <div className="pb-onb-hero">
      <div className="pb-onb-hero-inner">
        <header className="ai-onboarding-topbar">
          <div className="min-w-0">
            <div className="ai-brand-badge">
              <Sparkles size={12} aria-hidden="true" />
              <span>Workspace Setup</span>
            </div>
            <h1>{copy.heading}</h1>
            <p>{copy.subheading}</p>
          </div>

          {canEdit && (
            <div className="flex items-center gap-3 flex-shrink-0 pt-1">
              {saveStatus === 'saving' && (
                <span role="status" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                  Saving…
                </span>
              )}
              {saveStatus === 'saved' && (
                <span role="status" className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Check size={12} className="text-primary" aria-hidden="true" />
                  Saved
                </span>
              )}
              <Button variant="ghost" size="sm" disabled={pending} onClick={onSkip} className="text-muted-foreground hover:text-foreground">
                Skip onboarding
              </Button>
            </div>
          )}
        </header>

        <StepProgress currentView={view} currentStepNum={currentStepNum} onSelectStep={onSelectStep} />
      </div>
    </div>
  );
}
