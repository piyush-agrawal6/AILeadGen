"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bug,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  HelpCircle,
  LifeBuoy,
  Lightbulb,
  Mail,
  Search,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import {
  HELP_ARTICLES,
  HELP_CATEGORIES,
  searchHelpArticles,
  type HelpArticle,
} from "@/lib/help-articles";
import { request } from "@/lib/intelligence";
import { brand } from "@/lib/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const AI_HELP_QUESTIONS = [
  "Why is my search not working?",
  "How do I create a monitor?",
  "Why is an integration unavailable?",
  "What does my current plan include?",
  "How do I configure the Developer API?",
  "Why is my workspace access restricted?",
];

const QUICK_SETTINGS_LINKS = [
  { label: "Billing & Usage", href: "/settings?category=billing&tab=overview" },
  { label: "Research Sources", href: "/settings?category=integrations&tab=sources" },
  { label: "Developer API & MCP", href: "/settings?category=integrations&tab=developer" },
  { label: "Notifications & Alerts", href: "/settings?category=preferences&tab=notifications" },
  { label: "Team & Audit Log", href: "/settings?category=team&tab=members" },
  { label: "Manage Workspaces", href: "/settings/workspaces" },
];

type SupportKind = "support" | "bug" | "billing" | "feature";

export function HelpCenterClient() {
  const searchParams = useSearchParams();
  const articleParam = searchParams?.get("article") ?? null;

  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeArticleId, setActiveArticleId] = useState<string | null>(articleParam);
  const [helpfulVote, setHelpfulVote] = useState<Record<string, "yes" | "no">>({});

  // Support dialog state
  const [supportOpen, setSupportOpen] = useState(false);
  const [supportKind, setSupportKind] = useState<SupportKind>("support");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [affectedPage, setAffectedPage] = useState("");
  const [includeDiagnostics, setIncludeDiagnostics] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [supportResult, setSupportResult] = useState<{
    delivered: boolean;
    message: string;
    reference_id?: string;
    fallback_mailto?: string;
  } | null>(null);
  const [supportError, setSupportError] = useState("");

  useEffect(() => {
    if (articleParam) setActiveArticleId(articleParam);
  }, [articleParam]);

  const activeArticle: HelpArticle | null = useMemo(
    () => (activeArticleId ? HELP_ARTICLES.find((a) => a.id === activeArticleId) || null : null),
    [activeArticleId]
  );

  const filteredArticles = useMemo(() => {
    const base = searchHelpArticles(query);
    if (selectedCategory === "all") return base;
    return base.filter((a) => a.category === selectedCategory);
  }, [query, selectedCategory]);

  const popularArticles = useMemo(() => HELP_ARTICLES.filter((a) => a.popular), []);

  function openSupport(kind: SupportKind) {
    setSupportKind(kind);
    setSupportResult(null);
    setSupportError("");
    setSubject("");
    setDescription("");
    if (typeof window !== "undefined") {
      setAffectedPage(window.location.pathname);
    }
    setSupportOpen(true);
  }

  async function handleSubmitSupport(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setSupportError("");
    setSupportResult(null);
    try {
      const res = await request<{
        delivered: boolean;
        message: string;
        reference_id?: string;
        fallback_mailto?: string;
      }>("/help/support", {
        method: "POST",
        body: JSON.stringify({
          category: supportKind,
          subject: subject.trim(),
          description: description.trim(),
          affected_page: affectedPage.trim() || null,
          include_diagnostics: includeDiagnostics,
          diagnostics: includeDiagnostics
            ? {
                request_id: crypto.randomUUID(),
                app_version: "3.0.0",
                timestamp: new Date().toISOString(),
                viewport:
                  typeof window !== "undefined"
                    ? `${window.innerWidth}x${window.innerHeight}`
                    : null,
              }
            : null,
        }),
      });
      setSupportResult(res);
      if (res.delivered) {
        setSubject("");
        setDescription("");
      }
    } catch (err) {
      setSupportError(
        err instanceof Error
          ? err.message
          : "Could not submit your request. You can email contact@planebyte.com directly."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 py-2">
      {/* Hero & Search */}
      <section className="rounded-2xl border border-border bg-card p-6 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
              <LifeBuoy size={14} />
              <span>PlaneByte Help Center</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              How can we help?
            </h1>
            <p className="text-xs text-muted-foreground">
              Search verified product guides, ask the AI Assistant about your workspace, or contact support.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => openSupport("support")} className="h-8 text-xs gap-1.5">
              <Mail size={13} />
              Contact Support
            </Button>
            <Button size="sm" variant="outline" onClick={() => openSupport("bug")} className="h-8 text-xs gap-1.5">
              <Bug size={13} />
              Report a Bug
            </Button>
          </div>
        </div>

        <div className="relative max-w-2xl">
          <Search size={15} className="absolute left-3.5 top-3 text-muted-foreground" />
          <Input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (activeArticleId) setActiveArticleId(null);
            }}
            placeholder="Search guides: monitors, GitHub webhooks, Starter Trial, DNS verification, API keys…"
            aria-label="Search help articles"
            className="h-10 pl-10 text-sm"
          />
        </div>

        {/* Popular Topics */}
        {!query && !activeArticle && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[11px] font-medium text-muted-foreground mr-1">Popular:</span>
            {popularArticles.map((art) => (
              <button
                key={art.id}
                type="button"
                onClick={() => setActiveArticleId(art.id)}
                className="rounded-full border border-border bg-muted/35 px-2.5 py-1 text-[11px] font-medium text-foreground hover:border-primary/40 hover:bg-primary/5 transition-colors cursor-pointer"
              >
                {art.title}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ARTICLE READER VIEW */}
      {activeArticle ? (
        <article className="rounded-2xl border border-border bg-card p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-4">
            <button
              type="button"
              onClick={() => setActiveArticleId(null)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              <ArrowLeft size={13} />
              All Help Articles
            </button>
            <span className="text-[11px] text-muted-foreground">
              {activeArticle.category} · Updated {activeArticle.updatedAt}
            </span>
          </div>

          <header className="space-y-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              {activeArticle.title}
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {activeArticle.summary}
            </p>
          </header>

          {/* Step-by-step Guidance */}
          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Step-by-step guide
            </h3>
            <div className="space-y-2.5">
              {activeArticle.steps.map((step, idx) => (
                <div key={idx} className="rounded-xl border border-border/70 bg-muted/15 p-4 space-y-1">
                  <p className="text-xs font-semibold text-foreground">{step.title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{step.detail}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Troubleshooting */}
          {activeArticle.troubleshooting.length > 0 && (
            <section className="space-y-2.5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Troubleshooting
              </h3>
              <div className="space-y-2">
                {activeArticle.troubleshooting.map((item, idx) => (
                  <div key={idx} className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-3.5 space-y-1 text-xs">
                    <p className="font-semibold text-foreground">{item.symptom}</p>
                    <p className="text-muted-foreground leading-relaxed">{item.resolution}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Direct Settings Links + Ask AI */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-muted/20 p-4">
            <div className="flex flex-wrap items-center gap-2">
              {activeArticle.settingsLinks.map((lnk) => (
                <Link
                  key={lnk.href}
                  href={lnk.href}
                  className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2.5 text-xs font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
                >
                  {lnk.label} <ExternalLink size={11} />
                </Link>
              ))}
            </div>
            <Link
              href={`/intelligence/assistant?prompt=${encodeURIComponent(activeArticle.aiPrompt)}&context=overview`}
              className="inline-flex h-7 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
            >
              <Sparkles size={12} />
              Ask AI Assistant
            </Link>
          </div>

          {/* Feedback & Related Articles */}
          <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-border/70 pt-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Was this helpful?</span>
              <Button
                size="sm"
                variant={helpfulVote[activeArticle.id] === "yes" ? "default" : "outline"}
                onClick={() => setHelpfulVote({ ...helpfulVote, [activeArticle.id]: "yes" })}
                className="h-7 px-2.5 text-xs gap-1"
              >
                <ThumbsUp size={12} /> Yes
              </Button>
              <Button
                size="sm"
                variant={helpfulVote[activeArticle.id] === "no" ? "default" : "outline"}
                onClick={() => setHelpfulVote({ ...helpfulVote, [activeArticle.id]: "no" })}
                className="h-7 px-2.5 text-xs gap-1"
              >
                <ThumbsDown size={12} /> No
              </Button>
              {helpfulVote[activeArticle.id] === "no" && (
                <button
                  type="button"
                  onClick={() => openSupport("support")}
                  className="text-primary hover:underline ml-1 cursor-pointer"
                >
                  Contact Support
                </button>
              )}
            </div>

            {activeArticle.relatedIds.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground">Related:</span>
                {activeArticle.relatedIds.map((rid) => {
                  const rel = HELP_ARTICLES.find((a) => a.id === rid);
                  if (!rel) return null;
                  return (
                    <button
                      key={rid}
                      type="button"
                      onClick={() => setActiveArticleId(rid)}
                      className="font-medium text-primary hover:underline cursor-pointer"
                    >
                      {rel.title}
                    </button>
                  );
                })}
              </div>
            )}
          </footer>
        </article>
      ) : (
        /* KNOWLEDGE BASE DIRECTORY */
        <div className="space-y-6">
          {/* Category Filter Chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setSelectedCategory("all")}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors cursor-pointer ${
                selectedCategory === "all"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              All Categories ({HELP_ARTICLES.length})
            </button>
            {HELP_CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
                  selectedCategory === cat
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Articles Grid */}
          {filteredArticles.length === 0 ? (
            <div className="rounded-2xl border border-border bg-card p-8 text-center space-y-3">
              <HelpCircle className="mx-auto h-6 w-6 text-muted-foreground/60" />
              <p className="text-sm font-semibold text-foreground">
                No articles matched &ldquo;{query}&rdquo;
              </p>
              <p className="text-xs text-muted-foreground">
                Try broader terms, ask the PlaneByte AI Assistant, or contact support directly.
              </p>
              <div className="flex justify-center gap-2 pt-1">
                <Link
                  href={`/intelligence/assistant?prompt=${encodeURIComponent(query)}&context=overview`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
                >
                  <Sparkles size={13} /> Ask AI Assistant
                </Link>
                <Button size="sm" variant="outline" onClick={() => openSupport("support")} className="h-8 text-xs">
                  Contact Support
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {filteredArticles.map((article) => (
                <button
                  key={article.id}
                  type="button"
                  onClick={() => setActiveArticleId(article.id)}
                  className="group flex flex-col justify-between rounded-xl border border-border bg-card p-4 text-left hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                        {article.category}
                      </span>
                      <BookOpen size={13} className="text-muted-foreground/60 group-hover:text-primary" />
                    </div>
                    <h2 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                      {article.title}
                    </h2>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                      {article.summary}
                    </p>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-[11px] font-medium text-primary">
                    <span>Read guide</span>
                    <ArrowRight size={12} />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* AI-Powered Product Help */}
          <section className="rounded-2xl border border-primary/25 bg-primary/[0.03] p-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles size={15} className="text-primary" />
                <h2 className="text-sm font-semibold text-foreground">
                  Ask PlaneByte AI Assistant
                </h2>
              </div>
              <Link
                href="/intelligence/assistant"
                className="text-xs font-medium text-primary hover:underline"
              >
                Open full assistant →
              </Link>
            </div>
            <p className="text-xs text-muted-foreground">
              Get answers grounded in your active workspace&apos;s actual plan, sources, monitors, and settings.
            </p>
            <div className="flex flex-wrap gap-2">
              {AI_HELP_QUESTIONS.map((q) => (
                <Link
                  key={q}
                  href={`/intelligence/assistant?prompt=${encodeURIComponent(q)}&context=overview`}
                  className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground hover:border-primary/40 hover:text-primary transition-colors"
                >
                  {q}
                </Link>
              ))}
            </div>
          </section>

          {/* Support Options + Quick Links */}
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="lg:col-span-2 rounded-2xl border border-border bg-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-foreground">Need direct assistance?</h2>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {[
                  { kind: "support" as SupportKind, title: "Contact Support", desc: "General product & workspace questions", icon: Mail },
                  { kind: "bug" as SupportKind, title: "Report a Bug", desc: "Include affected page & optional diagnostics", icon: Bug },
                  { kind: "billing" as SupportKind, title: "Billing Assistance", desc: "Subscriptions, Creem invoices & plans", icon: CreditCard },
                  { kind: "feature" as SupportKind, title: "Feature Request", desc: "Suggest new sources or workflow improvements", icon: Lightbulb },
                ].map(({ kind, title, desc, icon: Icon }) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => openSupport(kind)}
                    className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-muted/15 p-3 text-left hover:border-primary/40 hover:bg-primary/[0.03] transition-colors cursor-pointer"
                  >
                    <Icon size={15} className="text-primary shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-foreground">{title}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-foreground">Quick Settings Links</h2>
              <ul className="space-y-1.5 text-xs">
                {QUICK_SETTINGS_LINKS.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
                    >
                      <span>{item.label}</span>
                      <ArrowRight size={12} />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>
      )}

      {/* Contact Support & Issue Reporting Dialog */}
      <Dialog.Root open={supportOpen} onOpenChange={setSupportOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Dialog.Title className="text-base font-semibold text-foreground">
                  {supportKind === "bug"
                    ? "Report a Bug"
                    : supportKind === "billing"
                      ? "Billing Assistance"
                      : supportKind === "feature"
                        ? "Feature Request"
                        : "Contact PlaneByte Support"}
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground mt-0.5">
                  Delivered to {brand.supportEmail}. Never include passwords, API keys, or card numbers.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className="rounded-lg p-1 text-muted-foreground hover:bg-muted" aria-label="Close">
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            {supportResult ? (
              <div className="space-y-3">
                <div
                  role="status"
                  className={`flex items-start gap-2 rounded-xl border p-3.5 text-xs ${
                    supportResult.delivered
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300"
                  }`}
                >
                  {supportResult.delivered ? (
                    <CheckCircle2 size={15} className="shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                  )}
                  <span>{supportResult.message}</span>
                </div>
                <div className="flex justify-end gap-2">
                  {!supportResult.delivered && supportResult.fallback_mailto && (
                    <a
                      href={supportResult.fallback_mailto}
                      className="inline-flex h-8 items-center justify-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
                    >
                      Open Email Client
                    </a>
                  )}
                  <Button size="sm" variant="outline" onClick={() => setSupportOpen(false)}>
                    Close
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={(e) => void handleSubmitSupport(e)} className="space-y-3.5">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1">
                    <span className="text-xs font-medium text-foreground">Request type</span>
                    <select
                      value={supportKind}
                      onChange={(e) => setSupportKind(e.target.value as SupportKind)}
                      className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                    >
                      <option value="support">Contact Support</option>
                      <option value="bug">Report a Bug</option>
                      <option value="billing">Billing Assistance</option>
                      <option value="feature">Feature Request</option>
                    </select>
                  </label>

                  <label className="space-y-1">
                    <span className="text-xs font-medium text-foreground">Affected page (optional)</span>
                    <Input
                      value={affectedPage}
                      onChange={(e) => setAffectedPage(e.target.value)}
                      placeholder="/intent-radar/discover"
                      className="h-8 text-xs"
                    />
                  </label>
                </div>

                <label className="block space-y-1">
                  <span className="text-xs font-medium text-foreground">Subject *</span>
                  <Input
                    required
                    minLength={4}
                    maxLength={160}
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Brief summary of your question or issue"
                    className="h-8 text-xs"
                  />
                </label>

                <label className="block space-y-1">
                  <span className="text-xs font-medium text-foreground">Description *</span>
                  <textarea
                    required
                    minLength={10}
                    maxLength={3000}
                    rows={4}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Include what you expected to happen and what occurred instead…"
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>

                <label className="flex items-start gap-2 text-[11px] text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeDiagnostics}
                    onChange={(e) => setIncludeDiagnostics(e.target.checked)}
                    className="mt-0.5 accent-primary"
                  />
                  <span>
                    Attach safe diagnostic metadata (request ID, app version, viewport, timestamp). No API keys, tokens, or private content are ever included.
                  </span>
                </label>

                {supportError && (
                  <p role="alert" className="text-xs text-destructive">
                    {supportError}
                  </p>
                )}

                <div className="flex justify-end gap-2 pt-1">
                  <Button type="button" size="sm" variant="outline" onClick={() => setSupportOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={submitting || subject.trim().length < 4 || description.trim().length < 10}
                  >
                    {submitting ? "Sending…" : "Send Request"}
                  </Button>
                </div>
              </form>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
