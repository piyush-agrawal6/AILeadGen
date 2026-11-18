'use client';
import React, { useEffect, useRef, useState } from 'react';
import { Bot, Check, RefreshCw, Send, Sparkles, Wand2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  deriveJobStatus,
  STEP_LABELS,
  type CopilotMessage,
  type ProposedUpdate,
  type Review,
  type StepKey
} from './types';

const STEP_PROMPT_CHIPS: Record<StepKey, string[]> = {
  welcome: [
    'What will you extract from my website?',
    'How does Intent Radar find buying signals?'
  ],
  company: [
    'Improve my company description',
    'Make my positioning more specific',
    'Suggest target industries'
  ],
  icp: [
    'Which of these 5 ICPs should I prioritize?',
    'Explain the difference between these segments',
    'Generate buying triggers for my primary ICP'
  ],
  research: [
    'Suggest 5 better buying-intent phrases',
    'Suggest negative keywords',
    'Explain why these keywords match my ICP'
  ],
  plan: [
    'Which plan fits an early-stage B2B team?',
    'How does the 3-day free trial work?'
  ],
  ready: []
};

export function CopilotSuggestion({
  msgId,
  index,
  update,
  applied,
  discarded,
  onApply,
  onDiscard
}: {
  msgId: string;
  index: number;
  update: ProposedUpdate;
  applied: boolean;
  discarded: boolean;
  onApply: () => void;
  onDiscard: () => void;
}) {
  if (discarded) return null;
  const previewText = Array.isArray(update.value) ? update.value.join(' · ') : update.value;
  return (
    <div key={`${msgId}:${index}`} className="rounded-lg bg-background/90 border border-border/80 p-2.5 space-y-2">
      <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">{previewText}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          disabled={applied}
          className={`ai-chat-action-btn ${applied ? 'is-applied' : ''}`}
          onClick={onApply}
        >
          {applied ? (
            <>
              <Check size={12} aria-hidden="true" /> Applied to form
            </>
          ) : (
            <>
              <Wand2 size={12} aria-hidden="true" /> {update.label || 'Apply to form'}
            </>
          )}
        </button>
        {!applied && (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
            onClick={onDiscard}
            aria-label={`Discard suggestion: ${update.label || 'update'}`}
          >
            <X size={11} aria-hidden="true" /> Discard
          </button>
        )}
      </div>
    </div>
  );
}

export function CopilotPanel({
  companyName,
  currentStep,
  messages,
  onAsk,
  onApplyUpdate,
  onDiscardUpdate,
  pending,
  adviceReview,
  onRefreshAdvice,
  onRetryAdvice,
  companyReview,
  icpReview
}: {
  companyName: string;
  currentStep: StepKey;
  messages: CopilotMessage[];
  onAsk: (q: string) => Promise<void>;
  onApplyUpdate: (msgId: string, idx: number, upd: ProposedUpdate) => void;
  onDiscardUpdate: (msgId: string, idx: number) => void;
  pending: boolean;
  adviceReview?: Review;
  onRefreshAdvice: () => void;
  onRetryAdvice: () => void;
  companyReview?: Review;
  icpReview?: Review;
}) {
  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages.length, pending]);

  const activeKind: 'company' | 'icp' = currentStep === 'icp' ? 'icp' : 'company';
  const activeJob = currentStep === 'icp' ? icpReview : currentStep === 'company' ? companyReview : undefined;
  const jobStatus = deriveJobStatus(activeJob, activeKind);

  const statusTone = pending || jobStatus.isBusy ? 'is-busy' : jobStatus.isFailed ? 'is-failed' : 'is-ready';
  const statusText = pending ? 'Thinking' : jobStatus.label;
  const chips = STEP_PROMPT_CHIPS[currentStep] || [];

  return (
    <div className="ai-copilot-inner flex flex-col h-full">
      {/* Compact Header with Synchronized Single Status (NO competing progress bar) */}
      <div className="ai-copilot-header px-4 py-3 border-b border-border flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-white/85 dark:bg-muted text-[#6b56a6] dark:text-[#c4b5fd] border border-border/70 flex items-center justify-center flex-shrink-0">
            <Bot size={16} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold text-xs text-foreground leading-tight truncate">PlaneByte Copilot</h2>
            <span className="text-[11px] text-muted-foreground block truncate">
              {companyName || 'Your workspace'} · {STEP_LABELS[currentStep]}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0" role="status" aria-live="polite">
          <span className={`ai-status-dot ${statusTone}`} aria-hidden="true" />
          <span className="text-[11px] font-medium text-muted-foreground">{statusText}</span>
        </div>
      </div>

      {/* Scrollable Conversation Area */}
      <div className="ai-copilot-messages flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {messages.map((m, idx) => {
          const prevStep = idx > 0 ? messages[idx - 1].step : null;
          const showStepDivider = idx > 0 && prevStep !== m.step;
          return (
            <React.Fragment key={m.id}>
              {showStepDivider && (
                <div className="flex items-center gap-2 py-1 text-[11px] font-medium text-muted-foreground">
                  <span className="h-px flex-1 bg-border/70" />
                  <span>{STEP_LABELS[m.step]}</span>
                  <span className="h-px flex-1 bg-border/70" />
                </div>
              )}
              <div className={`ai-message-bubble ${m.role === 'user' ? 'is-user' : 'is-assistant'}`}>
                {m.mode && <span className="ai-message-mode">{m.mode}</span>}
                <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.text}</p>

                {m.role === 'assistant' && m.updates && m.updates.length > 0 && (
                  <div className="mt-2.5 pt-2.5 border-t border-border/60 space-y-2">
                    {m.updates.map((upd, uIdx) => (
                      <CopilotSuggestion
                        key={uIdx}
                        msgId={m.id}
                        index={uIdx}
                        update={upd}
                        applied={Boolean(m.appliedKeys?.includes(`${m.id}:${uIdx}`))}
                        discarded={Boolean(m.discardedKeys?.includes(`${m.id}:${uIdx}`))}
                        onApply={() => onApplyUpdate(m.id, uIdx, upd)}
                        onDiscard={() => onDiscardUpdate(m.id, uIdx)}
                      />
                    ))}
                  </div>
                )}

                {m.role === 'assistant' && m.isError && (
                  <div className="mt-2 flex items-center gap-2">
                    {(m.canRetry || adviceReview?.can_retry) && (
                      <button type="button" className="ai-chat-action-btn" onClick={onRetryAdvice}>
                        <RefreshCw size={11} aria-hidden="true" /> Retry guidance
                      </button>
                    )}
                    <button type="button" className="text-xs text-muted-foreground underline" onClick={onRefreshAdvice}>
                      Refresh
                    </button>
                  </div>
                )}
              </div>
            </React.Fragment>
          );
        })}

        {pending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-1" role="status">
            <Sparkles size={13} className="pb-spin-gentle text-primary" aria-hidden="true" />
            <span>Drafting contextual guidance…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Context-Aware Quick Prompts */}
      {chips.length > 0 && (
        <div className="px-3.5 py-2.5 border-t border-border/60 bg-muted/15 flex flex-wrap gap-1.5">
          {chips.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              disabled={pending}
              className="ai-chip-btn"
              onClick={() => void onAsk(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Fixed Composer */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (inputVal.trim() && !pending) {
            void onAsk(inputVal);
            setInputVal('');
          }
        }}
        className="p-3 border-t border-border flex items-center gap-2 bg-card"
      >
        <input
          type="text"
          aria-label="Ask Copilot about your business"
          value={inputVal}
          onChange={e => setInputVal(e.target.value)}
          placeholder="Ask Copilot to draft, refine, or suggest…"
          className="ai-copilot-input flex-1 text-xs"
          disabled={pending}
        />
        <Button
          type="submit"
          size="sm"
          aria-label="Send question to Copilot"
          disabled={pending || !inputVal.trim()}
          className="h-9 px-3"
        >
          <Send size={13} aria-hidden="true" />
        </Button>
      </form>
    </div>
  );
}
