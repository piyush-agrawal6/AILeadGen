"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  Archive,
  ArchiveRestore,
  ArrowUpRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  CreditCard,
  History,
  Loader2,
  MessageSquarePlus,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Pin,
  PinOff,
  Plug,
  Radio,
  RefreshCw,
  Search,
  SendHorizontal,
  ShieldCheck,
  Sparkles,
  Square,
  Target,
  Trash2,
  Users,
  Wrench,
  X,
  XCircle,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConversationItem {
  id: string;
  title: string;
  preview: string;
  pinned: boolean;
  archived: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
  status: string;
}

interface ToolCallItem {
  tool: string;
  label: string;
  status: "running" | "completed" | "error";
  error?: string;
}

interface ActionProposal {
  action_id: string;
  tool: string;
  title: string;
  description: string;
  quota_note?: string;
  status: "pending" | "executed" | "failed" | "declined";
  error?: string | null;
  preview?: {
    keywords?: string[];
    sources?: string[];
    icp_name?: string;
    min_relevance?: number;
    destination?: string;
  };
  params: Record<string, unknown>;
  result?: {
    summary?: string;
    resource_url?: string;
    entity_type?: string;
    entity_id?: string;
    dispatch_note?: string;
  };
}

interface QuotaInfo {
  exceeded?: boolean;
  reason?: string;
  daily_used?: number | null;
  daily_limit?: number | null;
  monthly_used?: number | null;
  monthly_limit?: number | null;
  monthly_remaining?: number | null;
  reset_at_utc?: string | null;
  billing_url?: string;
  settings_url?: string;
}

interface StructuredCard {
  kind:
    | "metrics"
    | "signals"
    | "icp_comparison"
    | "icps"
    | "monitors"
    | "opportunities"
    | "sources"
    | "billing"
    | "discoveries";
  title: string;
  recommendation?: string;
  view_all_href?: string;
  is_trial?: boolean;
  cancel_at_period_end?: boolean;
  period_end?: string | null;
  enabled_custom_feeds?: number;
  youtube_ai_analytics_enabled?: boolean;
  items: Record<string, unknown>[];
}

interface AssistantMessage {
  id: string;
  question: string;
  status: string;
  created_at: string;
  markdown: string;
  tool_calls: ToolCallItem[];
  cards: StructuredCard[];
  proposals: ActionProposal[];
  followups: string[];
  citations: { label: string; url: string }[];
  limitations: string[];
  mode: string;
  model?: string | null;
  ai_consumed?: boolean;
  quota_info?: QuotaInfo | null;
  streaming?: boolean;
}

interface ActionHistoryEntry {
  id: string;
  actor: string;
  action: string;
  tool: string;
  result: string;
  summary: string;
  resource_url: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Safe XSS-Free Markdown Renderer (headings, lists, tables, code copy, bold)
// ---------------------------------------------------------------------------

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
          return (
            <strong key={i} className="font-semibold text-foreground">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
          return (
            <code
              key={i}
              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[12px] text-foreground"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
          return (
            <em key={i} className="italic">
              {part.slice(1, -1)}
            </em>
          );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </>
  );
}

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="my-3 overflow-hidden rounded-xl border border-border bg-muted/40">
      <div className="flex items-center justify-between border-b border-border/70 px-3 py-1.5 text-[11px] text-muted-foreground">
        <span className="font-mono uppercase">{lang || "code"}</span>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard?.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1800);
          }}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-muted hover:text-foreground"
        >
          {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-xs leading-6 text-foreground">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MarkdownView({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.trim().startsWith("```")) {
      const lang = line.trim().slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      blocks.push(<CodeBlock key={`code-${i}`} code={codeLines.join("\n")} lang={lang} />);
      continue;
    }

    // Markdown table
    if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?[\s:-]+\|/.test(lines[i + 1])) {
      const parseRow = (r: string) =>
        r
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => c.trim());
      const headers = parseRow(line);
      i += 2;
      const bodyRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        bodyRows.push(parseRow(lines[i]));
        i++;
      }
      blocks.push(
        <div key={`tbl-${i}`} className="my-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                {headers.map((h, idx) => (
                  <th key={idx} className="border-b border-border px-3 py-2 font-semibold">
                    <InlineMarkdown text={h} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-muted/20">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3 py-2 text-foreground">
                      <InlineMarkdown text={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Headings
    if (/^#{1,4}\s+/.test(line)) {
      const text = line.replace(/^#{1,4}\s+/, "");
      blocks.push(
        <h3 key={`h-${i}`} className="mt-4 mb-1.5 text-sm font-semibold tracking-tight text-foreground first:mt-0">
          <InlineMarkdown text={text} />
        </h3>,
      );
      i++;
      continue;
    }

    // Blockquote
    if (line.trim().startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      blocks.push(
        <blockquote
          key={`bq-${i}`}
          className="my-2.5 border-l-2 border-primary/50 bg-muted/30 px-3.5 py-2 text-xs italic text-muted-foreground"
        >
          <InlineMarkdown text={quoteLines.join(" ")} />
        </blockquote>,
      );
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="my-2 space-y-1.5 pl-4 text-sm leading-relaxed text-foreground/90 list-disc">
          {items.map((item, idx) => (
            <li key={idx}>
              <InlineMarkdown text={item} />
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      blocks.push(
        <ol key={`ol-${i}`} className="my-2 space-y-1.5 pl-5 text-sm leading-relaxed text-foreground/90 list-decimal">
          {items.map((item, idx) => (
            <li key={idx}>
              <InlineMarkdown text={item} />
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    if (!line.trim()) {
      i++;
      continue;
    }

    blocks.push(
      <p key={`p-${i}`} className="my-2 text-sm leading-relaxed text-foreground/90 first:mt-0">
        <InlineMarkdown text={line} />
      </p>,
    );
    i++;
  }

  return <div className="space-y-0.5">{blocks}</div>;
}

// ---------------------------------------------------------------------------
// Rich Structured Result Cards
// ---------------------------------------------------------------------------

function StructuredCardView({ card }: { card: StructuredCard }) {
  if (card.kind === "metrics") {
    return (
      <div className="rounded-xl border border-border bg-card/80 p-3.5">
        <div className="mb-2.5 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {card.items.map((m, idx) => (
            <Link
              key={idx}
              href={String(m.href || "/intent-radar")}
              className="rounded-lg border border-border/70 bg-background/80 px-3 py-2 transition-colors hover:border-primary/40"
            >
              <span className="block text-[11px] text-muted-foreground">{String(m.label)}</span>
              <span className="mt-0.5 block text-lg font-semibold text-foreground">{String(m.value)}</span>
            </Link>
          ))}
        </div>
      </div>
    );
  }

  if (card.kind === "signals") {
    return (
      <div className="rounded-xl border border-border bg-card/80 p-3.5">
        <div className="mb-2.5 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
          {card.view_all_href && (
            <Link href={card.view_all_href} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              Open signals <ArrowUpRight size={12} />
            </Link>
          )}
        </div>
        <div className="space-y-2">
          {card.items.slice(0, 5).map((s, idx) => (
            <Link
              key={String(s.id || idx)}
              href={String(s.href || "/intent-radar/signals")}
              className="block rounded-lg border border-border/70 bg-background/70 p-2.5 transition-colors hover:border-primary/40"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold text-foreground line-clamp-1">{String(s.title)}</span>
                <span className="inline-flex items-center gap-1.5 shrink-0">
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                    {String(s.score ?? 0)}/100
                  </span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
                    {String(s.source || "public")}
                  </span>
                </span>
              </div>
              {Boolean(s.excerpt) && (
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{String(s.excerpt)}</p>
              )}
            </Link>
          ))}
        </div>
      </div>
    );
  }

  if (card.kind === "icp_comparison") {
    return (
      <div className="rounded-xl border border-border bg-card/80 p-3.5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
          {card.view_all_href && (
            <Link href={card.view_all_href} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              Manage ICPs <ArrowUpRight size={12} />
            </Link>
          )}
        </div>
        {card.recommendation && (
          <p className="mb-2.5 rounded-lg bg-primary/5 px-3 py-2 text-xs text-foreground">{card.recommendation}</p>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-1.5 pr-3 font-medium">ICP</th>
                <th className="py-1.5 px-2 font-medium text-right">Signals</th>
                <th className="py-1.5 px-2 font-medium text-right">High-Intent</th>
                <th className="py-1.5 pl-2 font-medium text-right">Complete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {card.items.map((row, idx) => (
                <tr key={String(row.id || idx)}>
                  <td className="py-2 pr-3 font-medium text-foreground">
                    {String(row.name)}{" "}
                    {Boolean(row.is_primary) && (
                      <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary">
                        Primary
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-right">{String(row.matched_signals ?? row.matching_signals ?? 0)}</td>
                  <td className="py-2 px-2 text-right">{String(row.high_intent_matches ?? row.high_intent_signals ?? 0)}</td>
                  <td className="py-2 pl-2 text-right">{String(row.completeness_score ?? row.completeness ?? 0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (card.kind === "sources") {
    return (
      <div className="rounded-xl border border-border bg-card/80 p-3.5">
        <div className="mb-2.5 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
          {card.view_all_href && (
            <Link href={card.view_all_href} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              Configure sources <ArrowUpRight size={12} />
            </Link>
          )}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {card.items.map((src, idx) => (
            <div key={String(src.id || idx)} className="flex items-center justify-between rounded-lg border border-border/70 bg-background/70 px-3 py-2 text-xs">
              <div>
                <p className="font-medium text-foreground">{String(src.name)}</p>
                <p className="text-[11px] text-muted-foreground">{String(src.ai_policy || "Eligible")}</p>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  src.selectable ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-muted text-muted-foreground"
                }`}
              >
                {String(src.state)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (card.kind === "billing") {
    return (
      <div className="rounded-xl border border-border bg-card/80 p-3.5">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
            {card.is_trial && (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                Trial
              </span>
            )}
          </div>
          {card.view_all_href && (
            <Link href={card.view_all_href} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              Billing & Usage <ArrowUpRight size={12} />
            </Link>
          )}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {card.items.slice(0, 4).map((u, idx) => {
            const used = Number(u.used || 0);
            const limit = Number(u.limit || 0);
            const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
            return (
              <div key={idx} className="rounded-lg border border-border/70 bg-background/70 p-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">{String(u.label)}</span>
                  <span className="text-muted-foreground">
                    {used}/{limit}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Generic compact list for icps, monitors, opportunities, discoveries
  return (
    <div className="rounded-xl border border-border bg-card/80 p-3.5">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{card.title}</p>
        {card.view_all_href && (
          <Link href={card.view_all_href} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            View all <ArrowUpRight size={12} />
          </Link>
        )}
      </div>
      <ul className="space-y-1.5 text-xs">
        {card.items.slice(0, 5).map((item, idx) => (
          <li key={String(item.id || idx)} className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-background/70 px-3 py-2">
            <Link href={String(item.href || card.view_all_href || "/intent-radar")} className="font-medium text-foreground hover:text-primary truncate">
              {String(item.name || item.title || item.signal_title || "Record")}
            </Link>
            <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              {String(item.status || item.priority || `${item.matched_count ?? 0} matches`)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action Approval Card
// ---------------------------------------------------------------------------

function ActionProposalCard({
  proposal,
  onExecuted,
}: {
  proposal: ActionProposal;
  onExecuted: (
    actionId: string,
    status: "executed" | "failed" | "declined",
    result?: ActionProposal["result"],
    error?: string | null,
  ) => void;
}) {
  const [busy, setBusy] = useState<"approve" | "decline" | null>(null);
  const [localError, setLocalError] = useState<string | null>(proposal.error || null);
  const queryClient = useQueryClient();

  async function handleApprove() {
    if (busy !== null) return;
    setBusy("approve");
    setLocalError(null);
    try {
      const res = await request<{ status: "executed"; result: ActionProposal["result"] }>(
        `/intent-radar/assistant/actions/${proposal.action_id}/execute`,
        { method: "POST" },
      );
      onExecuted(proposal.action_id, "executed", res.result, null);
      toast.success(res.result?.summary || "Action executed successfully.");
      setBusy(null);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ["intent-radar"] }),
        queryClient.invalidateQueries({ queryKey: ["icps"] }),
        queryClient.invalidateQueries({ queryKey: ["workspace-notifications"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications-page"] }),
        queryClient.invalidateQueries({ queryKey: ["assistant-action-history"] }),
        queryClient.invalidateQueries({ queryKey: ["assistant-conversations-v2"] }),
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not execute action.";
      setLocalError(msg);
      onExecuted(proposal.action_id, "failed", undefined, msg);
      toast.error(msg);
      void queryClient.invalidateQueries({ queryKey: ["assistant-action-history"] });
      setBusy(null);
    }
  }

  async function handleDecline() {
    if (busy !== null) return;
    setBusy("decline");
    setLocalError(null);
    try {
      await request(`/intent-radar/assistant/actions/${proposal.action_id}/decline`, { method: "POST" });
      onExecuted(proposal.action_id, "declined", undefined, null);
      toast.info("Action proposal declined.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not decline action.";
      setLocalError(msg);
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  }

  const effectiveError = localError || proposal.error;
  const preview = proposal.preview;
  const statusLabel =
    busy === "approve"
      ? "Executing…"
      : proposal.status === "executed"
        ? "Completed"
        : proposal.status === "failed"
          ? "Failed"
          : proposal.status === "declined"
            ? "Declined"
            : "Awaiting approval";

  const statusTone =
    busy === "approve"
      ? "bg-blue-500/15 text-blue-600 dark:text-blue-400"
      : proposal.status === "executed"
        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
        : proposal.status === "failed"
          ? "bg-destructive/15 text-destructive"
          : proposal.status === "declined"
            ? "bg-muted text-muted-foreground"
            : "bg-primary/15 text-primary";

  return (
    <div
      className={
        "rounded-xl border p-4 " +
        (proposal.status === "failed"
          ? "border-destructive/35 bg-destructive/[0.04]"
          : proposal.status === "executed"
            ? "border-emerald-500/30 bg-emerald-500/[0.03]"
            : "border-primary/30 bg-primary/[0.04]")
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <ShieldCheck size={15} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">{proposal.title}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{proposal.description}</p>
            {preview && (
              <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                {preview.keywords && preview.keywords.length > 0 && (
                  <div>
                    <dt className="inline font-medium text-foreground">Keywords: </dt>
                    <dd className="inline">{preview.keywords.join(", ")}</dd>
                  </div>
                )}
                {preview.sources && preview.sources.length > 0 && (
                  <div>
                    <dt className="inline font-medium text-foreground">Sources: </dt>
                    <dd className="inline">{preview.sources.join(", ")}</dd>
                  </div>
                )}
                {preview.icp_name && (
                  <div>
                    <dt className="inline font-medium text-foreground">ICP: </dt>
                    <dd className="inline">{preview.icp_name}</dd>
                  </div>
                )}
                {preview.destination && (
                  <div>
                    <dt className="inline font-medium text-foreground">Destination: </dt>
                    <dd className="inline">{preview.destination}</dd>
                  </div>
                )}
              </dl>
            )}
            {proposal.quota_note && (
              <p className="mt-1.5 text-[11px] font-medium text-amber-700 dark:text-amber-300">
                {proposal.quota_note}
              </p>
            )}
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${statusTone}`}>
          {statusLabel}
        </span>
      </div>

      {(proposal.status === "pending" || proposal.status === "failed") && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void handleApprove()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-foreground shadow-xs hover:opacity-95 disabled:opacity-50 cursor-pointer"
          >
            {busy === "approve" ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
            {busy === "approve"
              ? "Executing…"
              : proposal.status === "failed"
                ? "Retry Execution"
                : "Approve & Execute"}
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void handleDecline()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer"
          >
            {busy === "decline" ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
            Decline
          </button>
        </div>
      )}

      {proposal.status === "failed" && effectiveError && (
        <div role="alert" className="mt-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          <strong className="font-semibold">Execution failed:</strong> {effectiveError}
        </div>
      )}

      {proposal.status === "executed" && proposal.result && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-xs">
          <div className="space-y-0.5">
            <span className="font-medium text-emerald-700 dark:text-emerald-300 block">
              {proposal.result.summary || "Action completed."}
            </span>
            {proposal.result.dispatch_note && (
              <span className="text-[11px] text-muted-foreground block">
                {proposal.result.dispatch_note}
              </span>
            )}
          </div>
          {proposal.result.resource_url && (
            <Link
              href={proposal.result.resource_url}
              className="inline-flex items-center gap-1 font-semibold text-primary hover:underline shrink-0"
            >
              Open in workspace <ArrowUpRight size={12} />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helper: Group Conversations by Recency
// ---------------------------------------------------------------------------

function groupConversations(items: ConversationItem[]) {
  const pinned: ConversationItem[] = [];
  const today: ConversationItem[] = [];
  const yesterday: ConversationItem[] = [];
  const week: ConversationItem[] = [];
  const older: ConversationItem[] = [];

  const nowDate = new Date();
  const startToday = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate()).getTime();
  const startYesterday = startToday - 86_400_000;
  const startWeek = startToday - 7 * 86_400_000;

  for (const item of items) {
    if (item.pinned) {
      pinned.push(item);
      continue;
    }
    const ts = new Date(item.updated_at || item.created_at).getTime();
    if (ts >= startToday) today.push(item);
    else if (ts >= startYesterday) yesterday.push(item);
    else if (ts >= startWeek) week.push(item);
    else older.push(item);
  }

  return [
    { label: "Pinned", items: pinned },
    { label: "Today", items: today },
    { label: "Yesterday", items: yesterday },
    { label: "Previous 7 Days", items: week },
    { label: "Older", items: older },
  ].filter((g) => g.items.length > 0);
}

const STARTER_PROMPTS = [
  {
    title: "Workspace daily briefing",
    description: "Summarize activity today across signals, monitors, and alerts.",
    prompt: "Summarize what is happening in my workspace today across signals, monitors, ICPs, and alerts.",
    category: "Briefing",
    icon: Sparkles,
  },
  {
    title: "Top high-relevance signals",
    description: "Review top intent signals and explain priority opportunities.",
    prompt: "Show my top high-relevance signals and explain which ones deserve immediate follow-up.",
    category: "Signals",
    icon: Activity,
  },
  {
    title: "Compare & prioritize ICPs",
    description: "Evaluate buyer profiles against observed conversation intent.",
    prompt: "Compare my Ideal Customer Profiles against collected signals and recommend which ICP to prioritize.",
    category: "Targeting",
    icon: Target,
  },
  {
    title: "Connected sources & policies",
    description: "Check source health, feed status, and AI ingestion policies.",
    prompt: "Check my connected sources, custom feeds, and current YouTube and Discourse AI processing policies.",
    category: "Sources",
    icon: Plug,
  },
  {
    title: "Plan & remaining allowance",
    description: "Inspect trial status, subscription tier, and monthly quotas.",
    prompt: "What is my current subscription plan, trial status, and remaining monthly search and AI allowance?",
    category: "Account",
    icon: CreditCard,
  },
  {
    title: "Create an intent monitor",
    description: "Configure automated checks for buying discussions.",
    prompt: "Create an active monitor tracking SaaS teams evaluating alternatives to legacy tools.",
    category: "Monitors",
    icon: Radio,
  },
];

// ---------------------------------------------------------------------------
// Main Full-Page AI Assistant Component
// ---------------------------------------------------------------------------

export function AssistantPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspace = useWorkspace();
  const activeOrgId = workspace.data?.active_organization_id || "";
  const draftStorageKey = activeOrgId ? `pb_ai_assistant_draft:${activeOrgId}` : "pb_ai_assistant_draft";

  const initialContextType = searchParams.get("context") || "overview";
  const initialEntityId = searchParams.get("entityId") || "";
  const initialPromptParam = searchParams.get("prompt") || "";
  const initialThreadParam = searchParams.get("thread") || "";

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const [actionHistoryOpen, setActionHistoryOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  const [activeThreadId, setActiveThreadId] = useState<string | null>(initialThreadParam || null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState<string>(() => {
    if (initialPromptParam) return initialPromptParam;
    if (typeof window !== "undefined") {
      return window.sessionStorage.getItem(draftStorageKey) || "";
    }
    return "";
  });
  const [contextBadge, setContextBadge] = useState<{ type: string; entityId: string } | null>(
    initialContextType !== "overview" ? { type: initialContextType, entityId: initialEntityId } : null,
  );

  // Sync URL ?prompt= changes (e.g. from Global Search / Help Center deep-links)
  useEffect(() => {
    if (initialPromptParam) {
      setDraft(initialPromptParam);
    }
  }, [initialPromptParam]);

  // Reset active thread/messages if active workspace switches in-place
  const prevOrgRef = useRef<string>(activeOrgId);
  useEffect(() => {
    if (prevOrgRef.current && activeOrgId && prevOrgRef.current !== activeOrgId) {
      abortRef.current?.abort();
      setActiveThreadId(null);
      setMessages([]);
      setDraft(typeof window !== "undefined" ? window.sessionStorage.getItem(draftStorageKey) || "" : "");
    }
    prevOrgRef.current = activeOrgId;
  }, [activeOrgId, draftStorageKey]);

  const [streaming, setStreaming] = useState(false);
  const [statusLabel, setStatusLabel] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const scrollEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  // Conversations list (strictly scoped by active workspace ID)
  const conversationsQuery = useQuery({
    queryKey: ["assistant-conversations-v2", activeOrgId, searchQuery, showArchived],
    queryFn: ({ signal }) =>
      request<{ items: ConversationItem[] }>(
        `/intent-radar/assistant/conversations?archived=${showArchived ? "true" : "false"}&search=${encodeURIComponent(searchQuery)}`,
        { signal },
      ),
    enabled: Boolean(activeOrgId),
    retry: false,
    staleTime: 10_000,
  });

  // Action history query (fetched when drawer opens, strictly workspace-scoped)
  const actionHistoryQuery = useQuery({
    queryKey: ["assistant-action-history", activeOrgId],
    queryFn: ({ signal }) =>
      request<{ items: ActionHistoryEntry[] }>("/intent-radar/assistant/action-history?limit=40", { signal }),
    enabled: actionHistoryOpen && Boolean(activeOrgId),
    retry: false,
  });

  // Load selected conversation messages
  const loadThread = useCallback(async (threadId: string) => {
    try {
      const detail = await request<{ id: string; title: string; messages: AssistantMessage[] }>(
        `/intent-radar/assistant/conversations/${threadId}`,
      );
      setActiveThreadId(detail.id);
      setMessages(detail.messages || []);
      setMobileHistoryOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load conversation.");
    }
  }, []);

  useEffect(() => {
    if (initialThreadParam) {
      void loadThread(initialThreadParam);
    }
  }, [initialThreadParam, loadThread]);

  // Persist draft in workspace-scoped sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(draftStorageKey, draft);
    }
  }, [draft, draftStorageKey]);

  // Auto-resize composer textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [draft]);

  // Auto-scroll to latest content
  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, streaming]);

  const startNewConversation = () => {
    if (streaming) {
      abortRef.current?.abort();
      setStreaming(false);
    }
    setActiveThreadId(null);
    setMessages([]);
    setMobileHistoryOpen(false);
    router.replace("/intelligence/assistant");
  };

  const stopGeneration = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setStatusLabel("");
  };

  const sendMessage = useCallback(
    async (promptOverride?: string) => {
      const text = (promptOverride ?? draft).trim();
      if (!text || streaming) return;

      const requestId = crypto.randomUUID();
      const tempId = `temp-${requestId}`;
      const optimisticMsg: AssistantMessage = {
        id: tempId,
        question: text,
        status: "STREAMING",
        created_at: new Date().toISOString(),
        markdown: "",
        tool_calls: [],
        cards: [],
        proposals: [],
        followups: [],
        citations: [],
        limitations: [],
        mode: "Analyzing workspace…",
        streaming: true,
      };

      setMessages((prev) => [...prev, optimisticMsg]);
      if (!promptOverride) setDraft("");
      setStreaming(true);
      setStatusLabel("Understanding workspace context…");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const resp = await fetch("/api/intent-radar/assistant/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({
            prompt: text,
            thread_id: activeThreadId,
            context_type: contextBadge?.type || "overview",
            entity_id: contextBadge?.entityId || null,
            request_id: requestId,
          }),
          signal: controller.signal,
        });

        if (!resp.ok || !resp.body) {
          let detail = `Assistant request failed (${resp.status})`;
          try {
            const errJson = (await resp.json()) as { detail?: string };
            if (errJson?.detail) detail = errJson.detail;
          } catch {
            // ignore
          }
          throw new Error(detail);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let resolvedThreadId = activeThreadId;

        const patchCurrent = (updater: (m: AssistantMessage) => AssistantMessage) => {
          setMessages((prev) => prev.map((m) => (m.id === tempId ? updater(m) : m)));
        };

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() || "";

          for (const frame of frames) {
            if (!frame.trim()) continue;
            let eventName = "message";
            const dataLines: string[] = [];
            for (const line of frame.split("\n")) {
              if (line.startsWith("event:")) eventName = line.slice(6).trim();
              else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
            }
            if (!dataLines.length) continue;
            let parsed: Record<string, unknown>;
            try {
              parsed = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
            } catch {
              continue;
            }

            if (eventName === "status") {
              if (typeof parsed.label === "string") setStatusLabel(parsed.label);
              if (typeof parsed.thread_id === "string" && !resolvedThreadId) {
                resolvedThreadId = parsed.thread_id;
                setActiveThreadId(parsed.thread_id);
              }
            } else if (eventName === "tool_start") {
              const tool = String(parsed.tool || "");
              const label = String(parsed.label || tool);
              setStatusLabel(`Running ${label}…`);
              patchCurrent((m) => ({
                ...m,
                tool_calls: [...m.tool_calls, { tool, label, status: "running" }],
              }));
            } else if (eventName === "tool_done") {
              const tool = String(parsed.tool || "");
              const st = parsed.status === "error" ? "error" : "completed";
              patchCurrent((m) => ({
                ...m,
                tool_calls: m.tool_calls.map((t) => (t.tool === tool ? { ...t, status: st } : t)),
              }));
            } else if (eventName === "cards") {
              patchCurrent((m) => ({
                ...m,
                cards: (parsed.cards as StructuredCard[]) || [],
                citations: (parsed.citations as { label: string; url: string }[]) || [],
              }));
            } else if (eventName === "proposals") {
              patchCurrent((m) => ({
                ...m,
                proposals: (parsed.proposals as ActionProposal[]) || [],
              }));
            } else if (eventName === "delta") {
              const chunk = String(parsed.text || "");
              patchCurrent((m) => ({ ...m, markdown: m.markdown + chunk }));
            } else if (eventName === "followups") {
              patchCurrent((m) => ({
                ...m,
                followups: (parsed.followups as string[]) || [],
              }));
            } else if (eventName === "done") {
              const finalMsg = parsed.message as AssistantMessage & { thread_id?: string };
              if (finalMsg?.thread_id) setActiveThreadId(finalMsg.thread_id);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempId
                    ? {
                        ...finalMsg,
                        question: text,
                        status: "COMPLETE",
                        streaming: false,
                      }
                    : m,
                ),
              );
            }
          }
        }

        await queryClient.invalidateQueries({ queryKey: ["assistant-conversations-v2"] });
      } catch (err) {
        if ((err as Error)?.name === "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempId
                ? {
                    ...m,
                    streaming: false,
                    status: "STOPPED",
                    markdown: m.markdown || "_Generation stopped._",
                  }
                : m,
            ),
          );
        } else {
          const msg = err instanceof Error ? err.message : "Assistant could not respond.";
          toast.error(msg);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempId
                ? {
                    ...m,
                    streaming: false,
                    status: "ERROR",
                    markdown: `Unable to complete this request: ${msg}`,
                  }
                : m,
            ),
          );
        }
      } finally {
        setStreaming(false);
        setStatusLabel("");
        abortRef.current = null;
      }
    },
    [activeThreadId, contextBadge, draft, queryClient, streaming],
  );

  // Thread mutations
  async function handlePatchConversation(id: string, body: { title?: string; pinned?: boolean; archived?: boolean }) {
    try {
      await request(`/intent-radar/assistant/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setMenuOpenId(null);
      setRenamingId(null);
      await queryClient.invalidateQueries({ queryKey: ["assistant-conversations-v2"] });
      if (body.title) toast.success("Conversation renamed.");
      else if (body.pinned !== undefined) toast.success(body.pinned ? "Conversation pinned." : "Conversation unpinned.");
      else if (body.archived !== undefined) toast.success(body.archived ? "Conversation archived." : "Conversation restored.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not update conversation.");
    }
  }

  async function handleDeleteConversation(id: string) {
    try {
      await request(`/intent-radar/assistant/conversations/${id}`, { method: "DELETE" });
      setConfirmDeleteId(null);
      setMenuOpenId(null);
      if (activeThreadId === id) startNewConversation();
      await queryClient.invalidateQueries({ queryKey: ["assistant-conversations-v2"] });
      toast.success("Conversation deleted.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete conversation.");
    }
  }

  const handleProposalUpdate = (
    actionId: string,
    status: "executed" | "failed" | "declined",
    result?: ActionProposal["result"],
    error?: string | null,
  ) => {
    setMessages((prev) =>
      prev.map((m) => ({
        ...m,
        proposals: m.proposals.map((p) =>
          p.action_id === actionId
            ? { ...p, status, result: result ?? p.result, error: error ?? null }
            : p,
        ),
      })),
    );
  };

  const grouped = useMemo(
    () => groupConversations(conversationsQuery.data?.items || []),
    [conversationsQuery.data?.items],
  );

  const sidebarContent = (
    <div className="flex h-full flex-col bg-card/60">
      <div className="flex items-center justify-between gap-2 border-b border-border p-3">
        <button
          type="button"
          onClick={startNewConversation}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow-xs transition-opacity hover:opacity-95"
        >
          <MessageSquarePlus size={15} />
          New conversation
        </button>
        <button
          type="button"
          aria-label="Collapse conversations"
          onClick={() => {
            setSidebarOpen(false);
            setMobileHistoryOpen(false);
          }}
          className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="space-y-2 border-b border-border p-3">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-2.5 text-muted-foreground" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations…"
            className="w-full rounded-lg border border-border bg-background py-1.5 pl-8 pr-3 text-xs text-foreground outline-none focus:border-primary"
          />
        </div>
        <div className="flex gap-1 rounded-lg bg-muted/60 p-0.5 text-[11px]">
          <button
            type="button"
            onClick={() => setShowArchived(false)}
            className={`flex-1 rounded-md py-1 font-medium transition-colors ${
              !showArchived ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Active
          </button>
          <button
            type="button"
            onClick={() => setShowArchived(true)}
            className={`flex-1 rounded-md py-1 font-medium transition-colors ${
              showArchived ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Archived
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {conversationsQuery.isPending ? (
          <div className="space-y-2 p-2">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-9 animate-pulse rounded-lg bg-muted/60" />
            ))}
          </div>
        ) : grouped.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">
            {showArchived ? "No archived conversations." : "No conversations yet. Start asking about your workspace."}
          </div>
        ) : (
          <div className="space-y-4">
            {grouped.map((group) => (
              <div key={group.label}>
                <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.label}
                </p>
                <ul className="space-y-0.5">
                  {group.items.map((item) => {
                    const isSelected = activeThreadId === item.id;
                    return (
                      <li key={item.id} className="relative">
                        {renamingId === item.id ? (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              if (renameValue.trim()) {
                                void handlePatchConversation(item.id, { title: renameValue.trim() });
                              }
                            }}
                            className="flex items-center gap-1 rounded-lg border border-primary bg-background px-2 py-1"
                          >
                            <input
                              type="text"
                              autoFocus
                              value={renameValue}
                              onChange={(e) => setRenameValue(e.target.value)}
                              className="w-full bg-transparent text-xs outline-none"
                            />
                            <button type="submit" aria-label="Save title" className="text-primary">
                              <Check size={13} />
                            </button>
                            <button
                              type="button"
                              aria-label="Cancel rename"
                              onClick={() => setRenamingId(null)}
                              className="text-muted-foreground"
                            >
                              <X size={13} />
                            </button>
                          </form>
                        ) : confirmDeleteId === item.id ? (
                          <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-2 text-xs">
                            <p className="font-medium text-foreground">Delete this thread?</p>
                            <div className="mt-1.5 flex gap-1.5">
                              <button
                                type="button"
                                onClick={() => void handleDeleteConversation(item.id)}
                                className="rounded bg-destructive px-2 py-0.5 text-[11px] font-medium text-destructive-foreground"
                              >
                                Delete
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirmDeleteId(null)}
                                className="rounded border border-border px-2 py-0.5 text-[11px]"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div
                            className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 transition-colors ${
                              isSelected ? "bg-primary/10 text-foreground" : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => void loadThread(item.id)}
                              className="min-w-0 flex-1 text-left"
                            >
                              <span className="flex items-center gap-1.5 truncate text-xs font-medium text-foreground">
                                {item.pinned && <Pin size={11} className="shrink-0 text-primary" />}
                                <span className="truncate">{item.title}</span>
                              </span>
                            </button>
                            <button
                              type="button"
                              aria-label="Conversation options"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenId((prev) => (prev === item.id ? null : item.id));
                              }}
                              className="rounded p-1 opacity-70 hover:bg-background hover:opacity-100"
                            >
                              <MoreHorizontal size={13} />
                            </button>
                          </div>
                        )}

                        {menuOpenId === item.id && (
                          <div className="absolute right-1 top-8 z-30 w-40 rounded-xl border border-border bg-card p-1 shadow-lg text-xs">
                            <button
                              type="button"
                              onClick={() => {
                                setRenamingId(item.id);
                                setRenameValue(item.title);
                                setMenuOpenId(null);
                              }}
                              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 hover:bg-muted"
                            >
                              <Pencil size={12} /> Rename
                            </button>
                            <button
                              type="button"
                              onClick={() => void handlePatchConversation(item.id, { pinned: !item.pinned })}
                              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 hover:bg-muted"
                            >
                              {item.pinned ? <PinOff size={12} /> : <Pin size={12} />}
                              {item.pinned ? "Unpin" : "Pin"}
                            </button>
                            <button
                              type="button"
                              onClick={() => void handlePatchConversation(item.id, { archived: !item.archived })}
                              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 hover:bg-muted"
                            >
                              {item.archived ? <ArchiveRestore size={12} /> : <Archive size={12} />}
                              {item.archived ? "Restore" : "Archive"}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setConfirmDeleteId(item.id);
                                setMenuOpenId(null);
                              }}
                              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-border p-3">
        <button
          type="button"
          onClick={() => setActionHistoryOpen(true)}
          className="flex w-full items-center justify-between rounded-lg border border-border bg-background px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted"
        >
          <span className="inline-flex items-center gap-2">
            <History size={14} className="text-primary" />
            Action History
          </span>
          <ChevronRight size={14} className="text-muted-foreground" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-[calc(100vh-6.75rem)] min-h-[520px] w-full overflow-hidden rounded-2xl border border-border bg-background shadow-xs">
      {/* Desktop Collapsible Conversation Sidebar */}
      {sidebarOpen && (
        <aside className="hidden w-72 shrink-0 border-r border-border md:block" aria-label="AI Conversations">
          {sidebarContent}
        </aside>
      )}

      {/* Mobile Slide-Out Conversation Drawer */}
      {mobileHistoryOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setMobileHistoryOpen(false)} />
          <div className="relative z-10 h-full w-72 max-w-[85vw] border-r border-border bg-card shadow-2xl">
            {sidebarContent}
          </div>
        </div>
      )}

      {/* Main Full-Page Chat Workspace */}
      <section className="flex min-w-0 flex-1 flex-col bg-background">
        {/* Compact Top Toolbar */}
        <header className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
          <div className="flex min-w-0 items-center gap-2">
            {!sidebarOpen && (
              <button
                type="button"
                aria-label="Open conversation sidebar"
                onClick={() => setSidebarOpen(true)}
                className="hidden rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground md:inline-flex"
              >
                <PanelLeftOpen size={17} />
              </button>
            )}
            <button
              type="button"
              aria-label="Open conversation history"
              onClick={() => setMobileHistoryOpen(true)}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground md:hidden"
            >
              <PanelLeftOpen size={17} />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Sparkles size={15} />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-sm font-semibold text-foreground">PlaneByte AI Assistant</h1>
                <p className="truncate text-[11px] text-muted-foreground">
                  Context-aware workspace copilot · Reads use 0 AI quota
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setActionHistoryOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
            >
              <History size={13} />
              <span className="hidden sm:inline">Actions</span>
            </button>
            <button
              type="button"
              onClick={startNewConversation}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
            >
              <MessageSquarePlus size={13} />
              <span className="hidden sm:inline">New chat</span>
            </button>
          </div>
        </header>

        {/* Scrollable Message Canvas */}
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.length === 0 ? (
              <div className="py-6 sm:py-10">
                <div className="mx-auto max-w-xl text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-xs">
                    <Sparkles size={24} />
                  </div>
                  <h2 className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
                    How can I help with your workspace?
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Ask about live signals, compare ICPs, inspect sources and allowances, or prepare monitors and discoveries with explicit approval.
                  </p>
                </div>

                <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {STARTER_PROMPTS.map((sp) => {
                    const Icon = sp.icon;
                    return (
                      <button
                        key={sp.title}
                        type="button"
                        onClick={() => void sendMessage(sp.prompt)}
                        className="group flex flex-col justify-between rounded-xl border border-border bg-card p-3.5 text-left transition-all hover:border-primary/40 hover:shadow-xs cursor-pointer"
                      >
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                              <Icon size={14} />
                            </span>
                            <span className="rounded-full bg-muted/80 px-2 py-0.5 text-[10px] font-medium text-muted-foreground whitespace-nowrap">
                              {sp.category}
                            </span>
                          </div>
                          <div>
                            <span className="text-xs font-semibold text-foreground group-hover:text-primary block truncate">
                              {sp.title}
                            </span>
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground line-clamp-2">
                              {sp.description}
                            </p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => {
                const isLatest = idx === messages.length - 1;
                return (
                  <div key={msg.id} className="space-y-4">
                    {/* User Prompt */}
                    <div className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-xs">
                        {msg.question}
                      </div>
                    </div>

                    {/* Assistant Response */}
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border bg-card text-primary shadow-2xs">
                        <Bot size={16} />
                      </div>
                      <div className="min-w-0 flex-1 space-y-3">
                        {/* Tool Execution Trace (live while streaming, collapsible once done) */}
                        {msg.tool_calls.length > 0 && msg.streaming && (
                          <div className="flex flex-wrap gap-1.5">
                            {msg.tool_calls.map((tc, tIdx) => (
                              <span
                                key={`${tc.tool}-${tIdx}`}
                                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground"
                              >
                                {tc.status === "running" ? (
                                  <Loader2 size={11} className="animate-spin text-primary" />
                                ) : (
                                  <Wrench size={11} className="text-primary" />
                                )}
                                {tc.label}
                                {tc.status === "completed" && <Check size={11} className="text-emerald-500" />}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Streaming Status */}
                        {msg.streaming && !msg.markdown && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 size={13} className="animate-spin text-primary" />
                            <span>{statusLabel || "Thinking…"}</span>
                          </div>
                        )}

                        {/* Clear Quota Banner when AI synthesis limit was hit */}
                        {!msg.streaming && msg.quota_info?.exceeded && (
                          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-800 dark:text-amber-200 space-y-1">
                            <p className="font-semibold">
                              AI analysis limit reached — answered with direct workspace data (0 AI quota used)
                            </p>
                            <p className="text-[11px] opacity-90">
                              {msg.quota_info.daily_limit != null && (
                                <span>
                                  Daily AI calls: {msg.quota_info.daily_used ?? 0}/{msg.quota_info.daily_limit}.{" "}
                                </span>
                              )}
                              {msg.quota_info.monthly_limit != null && (
                                <span>
                                  Monthly AI allowance: {msg.quota_info.monthly_used ?? 0}/{msg.quota_info.monthly_limit}.{" "}
                                </span>
                              )}
                              {msg.quota_info.reset_at_utc && (
                                <span>Daily reset: {new Date(msg.quota_info.reset_at_utc).toLocaleString()}.</span>
                              )}
                            </p>
                            <div className="flex flex-wrap gap-3 pt-0.5 text-[11px] font-semibold">
                              <Link href={msg.quota_info.billing_url || "/settings?category=billing&tab=overview"} className="underline">
                                View Billing &amp; Usage
                              </Link>
                              <Link href={msg.quota_info.settings_url || "/settings?category=preferences&tab=ai"} className="underline">
                                AI Preferences
                              </Link>
                            </div>
                          </div>
                        )}

                        {/* Markdown Body */}
                        {msg.markdown && (
                          <div className="rounded-2xl border border-border/70 bg-card/40 px-4 py-3.5">
                            <MarkdownView content={msg.markdown} />
                          </div>
                        )}

                        {/* Structured Cards */}
                        {msg.cards.length > 0 && (
                          <div className="space-y-3">
                            {msg.cards.map((card, cIdx) => (
                              <StructuredCardView key={`${card.kind}-${cIdx}`} card={card} />
                            ))}
                          </div>
                        )}

                        {/* Action Proposals */}
                        {msg.proposals.length > 0 && (
                          <div className="space-y-2.5">
                            {msg.proposals.map((prop) => (
                              <ActionProposalCard
                                key={prop.action_id}
                                proposal={prop}
                                onExecuted={handleProposalUpdate}
                              />
                            ))}
                          </div>
                        )}

                        {/* Collapsible Tool Trace & Workspace References */}
                        {!msg.streaming && (msg.tool_calls.length > 0 || msg.citations.length > 0) && (
                          <details className="rounded-xl border border-border/60 bg-muted/20 px-3 py-2 text-xs">
                            <summary className="cursor-pointer list-none font-medium text-muted-foreground flex items-center gap-1.5">
                              <ChevronDown size={13} />
                              <span>
                                Sources &amp; tool trace ({msg.tool_calls.length} tool{msg.tool_calls.length === 1 ? "" : "s"}
                                {msg.citations.length > 0 ? ` · ${msg.citations.length} link${msg.citations.length === 1 ? "" : "s"}` : ""})
                              </span>
                            </summary>
                            <div className="mt-2 space-y-2">
                              {msg.tool_calls.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {msg.tool_calls.map((tc, tIdx) => (
                                    <span
                                      key={`${tc.tool}-${tIdx}`}
                                      className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground"
                                    >
                                      <Wrench size={10} className="text-primary" />
                                      {tc.label}
                                      {tc.status === "completed" && <Check size={10} className="text-emerald-500" />}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {msg.citations.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {msg.citations.map((ci, ciIdx) => (
                                    <Link
                                      key={ciIdx}
                                      href={ci.url}
                                      className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-[11px] text-foreground hover:border-primary/50"
                                    >
                                      {ci.label}
                                      <ArrowUpRight size={11} className="text-muted-foreground" />
                                    </Link>
                                  ))}
                                </div>
                              )}
                            </div>
                          </details>
                        )}

                        {/* Footer Metadata & Actions */}
                        {!msg.streaming && (
                          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-full bg-muted px-2 py-0.5 font-medium">
                                {msg.mode}
                              </span>
                              {msg.model && <span>· {msg.model}</span>}
                              {msg.limitations[0] && (
                                <span className="line-clamp-1 max-w-md">{msg.limitations[0]}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                aria-label="Copy response"
                                onClick={() => {
                                  void navigator.clipboard?.writeText(msg.markdown);
                                  setCopiedMsgId(msg.id);
                                  setTimeout(() => setCopiedMsgId(null), 1600);
                                }}
                                className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-muted hover:text-foreground"
                              >
                                {copiedMsgId === msg.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                                {copiedMsgId === msg.id ? "Copied" : "Copy"}
                              </button>
                              <button
                                type="button"
                                aria-label="Regenerate response"
                                disabled={streaming}
                                onClick={() => void sendMessage(msg.question)}
                                className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-muted hover:text-foreground disabled:opacity-50"
                              >
                                <RefreshCw size={12} />
                                Retry
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Dynamic Contextual Follow-Up Chips (Latest Message) */}
                        {isLatest && !msg.streaming && msg.followups.length > 0 && (
                          <div className="pt-1">
                            <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">
                              Suggested follow-ups
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {msg.followups.slice(0, 4).map((fup, fIdx) => (
                                <button
                                  key={fIdx}
                                  type="button"
                                  onClick={() => void sendMessage(fup)}
                                  className="rounded-full border border-border bg-card px-3 py-1.5 text-left text-xs font-medium text-foreground transition-colors hover:border-primary/50 hover:bg-primary/5 hover:text-primary"
                                >
                                  {fup}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={scrollEndRef} />
          </div>
        </div>

        {/* Sticky Bottom Auto-Resizing Composer */}
        <div className="border-t border-border bg-card/60 px-4 py-3 sm:px-6">
          <div className="mx-auto max-w-3xl">
            {contextBadge && (
              <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                <span>
                  Context: {contextBadge.type}
                  {contextBadge.entityId ? ` · ${contextBadge.entityId.slice(0, 8)}…` : ""}
                </span>
                <button
                  type="button"
                  aria-label="Clear context"
                  onClick={() => setContextBadge(null)}
                  className="hover:opacity-75"
                >
                  <X size={11} />
                </button>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void sendMessage();
              }}
              className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-xs focus-within:border-primary/60"
            >
              <textarea
                ref={textareaRef}
                rows={1}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void sendMessage();
                  }
                }}
                placeholder="Ask about your signals, ICPs, discoveries, monitors, or request an action…"
                className="max-h-44 min-h-[40px] flex-1 resize-none bg-transparent px-2.5 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              {streaming ? (
                <button
                  type="button"
                  onClick={stopGeneration}
                  aria-label="Stop generating"
                  className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-xl bg-destructive px-3 text-xs font-semibold text-destructive-foreground hover:opacity-90"
                >
                  <Square size={12} />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!draft.trim()}
                  aria-label="Send message"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity hover:opacity-95 disabled:opacity-40"
                >
                  <SendHorizontal size={16} />
                </button>
              )}
            </form>
            <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
              PlaneByte AI uses verified workspace records only. Write actions always require your explicit confirmation.
            </p>
          </div>
        </div>
      </section>

      {/* Action History Slide-Over Drawer */}
      {actionHistoryOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="fixed inset-0 bg-black/50" onClick={() => setActionHistoryOpen(false)} />
          <div className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-border bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <History size={16} className="text-primary" />
                <h2 className="text-sm font-semibold text-foreground">AI Action History</h2>
              </div>
              <button
                type="button"
                aria-label="Close action history"
                onClick={() => setActionHistoryOpen(false)}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {actionHistoryQuery.isPending ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="h-16 animate-pulse rounded-xl bg-muted/60" />
                  ))}
                </div>
              ) : (actionHistoryQuery.data?.items || []).length === 0 ? (
                <div className="py-12 text-center text-xs text-muted-foreground">
                  No AI-executed actions yet. Approved workspace actions will appear here with audit timestamps.
                </div>
              ) : (
                <ul className="space-y-2.5">
                  {(actionHistoryQuery.data?.items || []).map((entry) => (
                    <li key={entry.id} className="rounded-xl border border-border bg-background p-3 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-foreground">{entry.summary}</span>
                        <span
                          className={
                            "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
                            (entry.result === "FAILED"
                              ? "bg-destructive/10 text-destructive"
                              : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400")
                          }
                        >
                          {entry.result}
                        </span>
                      </div>
                      <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Clock size={11} />
                          {new Date(entry.created_at).toLocaleString()}
                        </span>
                        <Link
                          href={entry.resource_url}
                          onClick={() => setActionHistoryOpen(false)}
                          className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                        >
                          Open <ArrowUpRight size={11} />
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
