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
  Bot,
  Bug,
  CheckCircle2,
  Code2,
  CreditCard,
  ExternalLink,
  HelpCircle,
  LifeBuoy,
  Lightbulb,
  Mail,
  Plug,
  Radio,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import {
  HELP_ARTICLES,
  HELP_CATEGORY_METAS,
  type HelpArticle,
  type HelpCategoryMeta,
} from "@/lib/help-articles";
import { request } from "@/lib/intelligence";
import { brand } from "@/lib/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type SupportKind = "support" | "bug" | "billing" | "feature";

function CategoryMetaIcon({ name }: { name: HelpCategoryMeta["iconName"] }) {
  switch (name) {
    case "sparkles":
      return <Sparkles size={20} className="text-primary" />;
    case "search":
      return <Search size={20} className="text-primary" />;
    case "target":
      return <Target size={20} className="text-primary" />;
    case "radio":
      return <Radio size={20} className="text-primary" />;
    case "bot":
      return <Bot size={20} className="text-primary" />;
    case "plug":
      return <Plug size={20} className="text-primary" />;
    case "code":
      return <Code2 size={20} className="text-primary" />;
    case "credit-card":
      return <CreditCard size={20} className="text-primary" />;
    case "shield":
      return <ShieldCheck size={20} className="text-primary" />;
    case "help":
      return <HelpCircle size={20} className="text-primary" />;
    default:
      return <BookOpen size={20} className="text-primary" />;
  }
}

export function HelpCenterClient() {
  const searchParams = useSearchParams();
  const articleParam = searchParams?.get("article") ?? null;
  const categoryParam = searchParams?.get("category") ?? null;

  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>(categoryParam || "all");
  const [activeArticleId, setActiveArticleId] = useState<string | null>(articleParam);
  const [helpfulVote, setHelpfulVote] = useState<Record<string, "yes" | "no">>({});

  // Sync with searchParams
  useEffect(() => {
    if (articleParam && articleParam !== activeArticleId) {
      setActiveArticleId(articleParam);
    }
  }, [articleParam]);

  useEffect(() => {
    if (categoryParam && categoryParam !== selectedCategory) {
      setSelectedCategory(categoryParam);
    }
  }, [categoryParam]);

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

  const activeArticle = useMemo(() => {
    return HELP_ARTICLES.find((a) => a.id === activeArticleId) ?? null;
  }, [activeArticleId]);

  // Articles filtered by search query
  const searchResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return HELP_ARTICLES.filter((a) => {
      return (
        a.title.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q) ||
        a.category.toLowerCase().includes(q) ||
        a.steps.some((s) => s.title.toLowerCase().includes(q) || s.detail.toLowerCase().includes(q)) ||
        a.troubleshooting.some(
          (t) => t.symptom.toLowerCase().includes(q) || t.resolution.toLowerCase().includes(q)
        )
      );
    });
  }, [query]);

  // Articles filtered by category
  const categoryArticles = useMemo(() => {
    if (selectedCategory === "all") return [];
    return HELP_ARTICLES.filter(
      (a) => a.category.toLowerCase() === selectedCategory.toLowerCase()
    );
  }, [selectedCategory]);

  const activeCategoryMeta = useMemo(() => {
    if (selectedCategory === "all") return null;
    return (
      HELP_CATEGORY_METAS.find(
        (m) => m.name.toLowerCase() === selectedCategory.toLowerCase()
      ) ?? null
    );
  }, [selectedCategory]);

  function handleSelectArticle(id: string) {
    setActiveArticleId(id);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("article", id);
      window.history.pushState(null, "", url.toString());
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function handleBackToCategory() {
    setActiveArticleId(null);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("article");
      window.history.pushState(null, "", url.toString());
    }
  }

  function handleBackToAllCategories() {
    setSelectedCategory("all");
    setActiveArticleId(null);
    setQuery("");
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("article");
      url.searchParams.delete("category");
      window.history.pushState(null, "", url.toString());
    }
  }

  function handleOpenSupport(kind: SupportKind) {
    setSupportKind(kind);
    setSupportError("");
    setSupportResult(null);
    setSubject("");
    setDescription("");
    setAffectedPage(typeof window !== "undefined" ? window.location.pathname : "");
    setSupportOpen(true);
  }

  async function handleSubmitSupport(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) {
      setSupportError("Please provide both a subject and a description.");
      return;
    }
    setSubmitting(true);
    setSupportError("");
    try {
      const payload = {
        kind: supportKind,
        subject: subject.trim(),
        description: description.trim(),
        affected_page: affectedPage.trim() || undefined,
        diagnostics: includeDiagnostics
          ? {
              user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
              href: typeof window !== "undefined" ? window.location.href : "unknown",
              screen:
                typeof window !== "undefined"
                  ? `${window.innerWidth}x${window.innerHeight}`
                  : "unknown",
            }
          : undefined,
      };
      const res = await request<{
        delivered: boolean;
        message: string;
        reference_id?: string;
        fallback_mailto?: string;
      }>("/organization/support/request", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSupportResult(res);
    } catch (err) {
      setSupportError(
        err instanceof Error ? err.message : "Could not submit support request. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      {/* 1. HERO SECTION (Subtle white/purple gradient, clear search) */}
      <div className="relative overflow-hidden rounded-3xl border border-border/70 bg-gradient-to-b from-card via-card/90 to-muted/20 px-6 py-10 sm:px-10 sm:py-12 text-center space-y-4 shadow-xs">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-xs">
          <LifeBuoy size={24} />
        </div>
        <div className="space-y-1.5 max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            How can we help?
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Find answers, explore guides, or get support from the PlaneByte team.
          </p>
        </div>

        {/* Prominent Search Bar */}
        <div className="max-w-xl mx-auto pt-2">
          <div className="relative">
            <Search
              size={17}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            />
            <input
              type="search"
              aria-label="Search help articles"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (activeArticleId) setActiveArticleId(null);
              }}
              placeholder="Search help articles, features, and troubleshooting…"
              className="h-12 w-full rounded-2xl border border-border/80 bg-background/95 pl-11 pr-10 text-sm text-foreground shadow-sm placeholder:text-muted-foreground/70 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. STATE A: SEARCH ACTIVE */}
      {query.trim().length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">
              Search results for &quot;{query}&quot; ({searchResults.length})
            </h2>
            <button
              type="button"
              onClick={() => setQuery("")}
              className="text-xs text-primary hover:underline cursor-pointer"
            >
              Clear search
            </button>
          </div>

          {searchResults.length > 0 ? (
            <div className="grid gap-3">
              {searchResults.map((art) => (
                <button
                  key={art.id}
                  type="button"
                  onClick={() => handleSelectArticle(art.id)}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left rounded-2xl border border-border/80 bg-card p-4 hover:border-primary/40 hover:shadow-xs transition-all cursor-pointer"
                >
                  <div className="space-y-1 min-w-0 pr-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        {art.category}
                      </span>
                      <h3 className="text-sm font-semibold text-foreground truncate">{art.title}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                      {art.summary}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-xs font-semibold text-primary shrink-0">
                    <span>Read guide</span>
                    <ArrowRight size={13} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center space-y-2">
              <HelpCircle size={24} className="mx-auto text-muted-foreground" />
              <h3 className="text-sm font-semibold text-foreground">No articles match &quot;{query}&quot;</h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Try searching with different terms, or explore the category guides below.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 3. STATE B: ARTICLE DETAILS VIEW */}
      {!query && activeArticle && (
        <article className="space-y-6 animate-in fade-in-50 duration-200">
          {/* Breadcrumb & Back */}
          <nav aria-label="Article breadcrumb" className="flex items-center gap-2 text-xs text-muted-foreground">
            <button
              type="button"
              onClick={handleBackToAllCategories}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Help Center
            </button>
            <span>/</span>
            <button
              type="button"
              onClick={handleBackToCategory}
              className="hover:text-foreground transition-colors cursor-pointer font-medium"
            >
              {activeArticle.category}
            </button>
            <span>/</span>
            <span className="text-foreground font-semibold truncate max-w-xs">{activeArticle.title}</span>
          </nav>

          {/* Article Header Card */}
          <div className="rounded-2xl border border-border/80 bg-card p-6 space-y-3">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                {activeArticle.category}
              </span>
              <span className="text-xs text-muted-foreground">Updated {activeArticle.updatedAt}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {activeArticle.title}
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {activeArticle.summary}
            </p>
          </div>

          {/* Step-by-Step Instructions */}
          {activeArticle.steps.length > 0 && (
            <div className="rounded-2xl border border-border/80 bg-card p-6 space-y-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                Step-by-Step Instructions
              </h2>
              <div className="space-y-4">
                {activeArticle.steps.map((st, idx) => (
                  <div key={st.title} className="flex gap-3">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <div className="space-y-1 min-w-0">
                      <h3 className="text-sm font-semibold text-foreground">{st.title}</h3>
                      <p className="text-xs text-muted-foreground leading-relaxed">{st.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Troubleshooting Section (if present) */}
          {activeArticle.troubleshooting.length > 0 && (
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6 space-y-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400" />
                <h2 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                  Troubleshooting &amp; Common Issues
                </h2>
              </div>
              <div className="space-y-3 pt-1">
                {activeArticle.troubleshooting.map((tr) => (
                  <div key={tr.symptom} className="space-y-1 text-xs">
                    <p className="font-semibold text-foreground">&bull; {tr.symptom}</p>
                    <p className="text-muted-foreground pl-3 leading-relaxed">{tr.resolution}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings & Related Links */}
          <div className="grid sm:grid-cols-2 gap-4">
            {activeArticle.settingsLinks.length > 0 && (
              <div className="rounded-2xl border border-border/80 bg-card p-5 space-y-2.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Quick Settings Shortcuts
                </h3>
                <div className="space-y-1.5">
                  {activeArticle.settingsLinks.map((lk) => (
                    <Link
                      key={lk.href}
                      href={lk.href}
                      className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-xs font-medium text-foreground hover:border-primary/40 hover:bg-muted/40 transition-colors"
                    >
                      <span>{lk.label}</span>
                      <ExternalLink size={12} className="text-muted-foreground" />
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Helpful Feedback Vote */}
            <div className="rounded-2xl border border-border/80 bg-card p-5 flex flex-col justify-between space-y-3">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Was this guide helpful?
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Your feedback helps us improve our documentation for all workspaces.
                </p>
              </div>

              {helpfulVote[activeArticle.id] ? (
                <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 size={15} />
                  <span>Thank you for your feedback!</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setHelpfulVote({ ...helpfulVote, [activeArticle.id]: "yes" })}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors cursor-pointer"
                  >
                    <ThumbsUp size={13} />
                    <span>Yes, helpful</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setHelpfulVote({ ...helpfulVote, [activeArticle.id]: "no" })}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors cursor-pointer"
                  >
                    <ThumbsDown size={13} />
                    <span>No</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Back button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={handleBackToCategory}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline cursor-pointer"
            >
              <ArrowLeft size={13} />
              <span>Back to {activeArticle.category}</span>
            </button>
          </div>
        </article>
      )}

      {/* 4. STATE C: CATEGORY DETAILS VIEW */}
      {!query && !activeArticle && selectedCategory !== "all" && (
        <div className="space-y-6 animate-in fade-in-50 duration-200">
          {/* Breadcrumb */}
          <nav aria-label="Category breadcrumb" className="flex items-center gap-2 text-xs text-muted-foreground">
            <button
              type="button"
              onClick={handleBackToAllCategories}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Help Center
            </button>
            <span>/</span>
            <span className="text-foreground font-semibold">{selectedCategory}</span>
          </nav>

          {/* Category Header */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-xl font-bold tracking-tight text-foreground">
                {selectedCategory}
              </h2>
              <p className="text-xs text-muted-foreground">
                {activeCategoryMeta?.description || "Browse guides and troubleshooting for this category."}
              </p>
            </div>
            <button
              type="button"
              onClick={handleBackToAllCategories}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer shrink-0"
            >
              <ArrowLeft size={12} />
              <span>All Categories</span>
            </button>
          </div>

          {/* Article Rows */}
          <div className="grid gap-3">
            {categoryArticles.map((art) => (
              <button
                key={art.id}
                type="button"
                onClick={() => handleSelectArticle(art.id)}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left rounded-2xl border border-border/80 bg-card p-5 hover:border-primary/40 hover:shadow-xs transition-all cursor-pointer group"
              >
                <div className="space-y-1 min-w-0 pr-3">
                  <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                    {art.title}
                  </h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {art.summary}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs font-semibold text-primary shrink-0">
                  <span>Read guide</span>
                  <ArrowRight size={13} />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 5. STATE D: LANDING PAGE — 10 CATEGORY CARDS FIRST */}
      {!query && !activeArticle && selectedCategory === "all" && (
        <div className="space-y-10 animate-in fade-in-50 duration-200">
          {/* Section: Category Cards Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold tracking-tight text-foreground">
                Browse by Category
              </h2>
              <span className="text-xs text-muted-foreground">
                10 topic directories
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {HELP_CATEGORY_METAS.map((meta) => {
                const count = HELP_ARTICLES.filter(
                  (a) => a.category.toLowerCase() === meta.name.toLowerCase()
                ).length;
                return (
                  <button
                    key={meta.id}
                    type="button"
                    onClick={() => setSelectedCategory(meta.name)}
                    className="flex flex-col justify-between text-left rounded-2xl border border-border/80 bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer group space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
                          <CategoryMetaIcon name={meta.iconName} />
                        </div>
                        <span className="rounded-full bg-muted/80 px-2 py-0.5 text-[11px] font-medium text-muted-foreground tabular-nums">
                          {count} {count === 1 ? "guide" : "guides"}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                          {meta.name}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {meta.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 text-xs font-medium text-primary pt-1">
                      <span>Explore guides</span>
                      <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Section: Still Need Help? (Compact Contact Support) */}
      {!activeArticle && (
        <div className="space-y-6 pt-4">
          <div className="rounded-2xl border border-border/80 bg-card p-6 sm:p-8 space-y-5">
            <div className="space-y-1 text-center sm:text-left">
              <h2 className="text-base sm:text-lg font-bold tracking-tight text-foreground">
                Still need help?
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Our support team is available to assist with billing, technical questions, bug reports, and features.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <button
                type="button"
                onClick={() => handleOpenSupport("support")}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border/80 bg-muted/20 p-4 text-center hover:border-primary/40 hover:bg-muted/40 transition-colors cursor-pointer group"
              >
                <Mail size={18} className="text-primary group-hover:scale-110 transition-transform" />
                <span className="text-xs font-semibold text-foreground">Contact Support</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenSupport("bug")}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border/80 bg-muted/20 p-4 text-center hover:border-primary/40 hover:bg-muted/40 transition-colors cursor-pointer group"
              >
                <Bug size={18} className="text-amber-500 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-semibold text-foreground">Report a Bug</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenSupport("billing")}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border/80 bg-muted/20 p-4 text-center hover:border-primary/40 hover:bg-muted/40 transition-colors cursor-pointer group"
              >
                <CreditCard size={18} className="text-primary group-hover:scale-110 transition-transform" />
                <span className="text-xs font-semibold text-foreground">Billing Assistance</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenSupport("feature")}
                className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border/80 bg-muted/20 p-4 text-center hover:border-primary/40 hover:bg-muted/40 transition-colors cursor-pointer group"
              >
                <Lightbulb size={18} className="text-indigo-500 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-semibold text-foreground">Request a Feature</span>
              </button>
            </div>
          </div>

          {/* Section: Ask PlaneByte AI */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-primary/20 bg-primary/5 p-6 shadow-xs">
            <div className="flex items-start gap-3.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shrink-0 shadow-xs">
                <Sparkles size={18} />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-sm font-bold text-foreground">Ask PlaneByte AI</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Get help understanding your workspace, sources, settings, and research workflows.
                </p>
              </div>
            </div>

            <Link
              href="/intent-radar/assistant"
              className="inline-flex h-9 items-center justify-center gap-1.5 rounded-xl bg-primary px-4 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shrink-0 shadow-xs"
            >
              <span>Open AI Assistant</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      )}

      {/* Support Dialog (Radix Dialog) */}
      <Dialog.Root open={supportOpen} onOpenChange={setSupportOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs animate-in fade-in-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in-50 zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <Dialog.Title className="text-base font-bold text-foreground">
                {supportKind === "bug"
                  ? "Report a Bug"
                  : supportKind === "billing"
                  ? "Billing Assistance"
                  : supportKind === "feature"
                  ? "Request a Feature"
                  : "Contact Support"}
              </Dialog.Title>
              <Dialog.Close asChild>
                <button
                  type="button"
                  aria-label="Close"
                  className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            {supportResult ? (
              <div className="py-6 text-center space-y-3">
                <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600">
                  <CheckCircle2 size={24} />
                </div>
                <h3 className="text-sm font-bold text-foreground">
                  {supportResult.delivered ? "Request Submitted" : "Request Prepared"}
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto leading-relaxed">
                  {supportResult.message}
                </p>
                {supportResult.reference_id && (
                  <p className="text-[11px] font-mono text-muted-foreground">
                    Reference ID: {supportResult.reference_id}
                  </p>
                )}
                <div className="pt-2">
                  <Button
                    type="button"
                    onClick={() => setSupportOpen(false)}
                    className="h-8 px-4 text-xs"
                  >
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitSupport} className="space-y-4 pt-4 text-xs">
                {supportError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-destructive">
                    {supportError}
                  </div>
                )}

                <div className="space-y-1">
                  <label htmlFor="sup-subject" className="font-medium text-foreground">
                    Subject *
                  </label>
                  <Input
                    id="sup-subject"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Brief summary of your inquiry"
                    className="h-8 text-xs"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label htmlFor="sup-desc" className="font-medium text-foreground">
                    Description *
                  </label>
                  <textarea
                    id="sup-desc"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide details so our team can help you promptly…"
                    rows={4}
                    className="w-full rounded-lg border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label htmlFor="sup-page" className="font-medium text-muted-foreground">
                    Affected page (optional)
                  </label>
                  <Input
                    id="sup-page"
                    value={affectedPage}
                    onChange={(e) => setAffectedPage(e.target.value)}
                    placeholder="/intent-radar/monitors"
                    className="h-8 text-xs text-muted-foreground"
                  />
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="sup-diag"
                    checked={includeDiagnostics}
                    onChange={(e) => setIncludeDiagnostics(e.target.checked)}
                    className="rounded border-border accent-primary"
                  />
                  <label htmlFor="sup-diag" className="text-muted-foreground cursor-pointer">
                    Include browser metadata &amp; diagnostics to help resolve issues faster
                  </label>
                </div>

                <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setSupportOpen(false)}
                    className="h-8 text-xs"
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="h-8 text-xs">
                    {submitting ? "Submitting…" : "Submit Request"}
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
