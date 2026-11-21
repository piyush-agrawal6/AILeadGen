"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  Info,
  Loader2,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Target,
  Trash2,
  Undo2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ICPProfile } from "./ICPDashboard";

const COMMON_INDUSTRIES = [
  "B2B SaaS",
  "Fintech",
  "Healthcare & Life Sciences",
  "E-commerce & Retail",
  "Developer Tools & Infrastructure",
  "Marketing & Advertising",
  "Cybersecurity",
  "Education & Edtech",
  "Logistics & Supply Chain",
  "Professional Services & Agencies",
];

const COMPANY_SIZES = [
  "1-10 (Seed / Early)",
  "11-50 (Small / Series A)",
  "51-200 (Mid-Market / Growth)",
  "201-500 (Scale-Up)",
  "501-1000 (Large)",
  "1000+ (Enterprise)",
];

const SENIORITY_LEVELS = [
  "C-Level (CEO, CTO, CIO, CMO, CRO)",
  "VP / Head of Department",
  "Director",
  "Lead / Principal",
  "Senior Manager",
  "Individual Contributor / Practitioner",
];

const EXAMPLE_AI_PROMPTS = [
  "We sell custom software development services to small businesses in the US and UK.",
  "B2B SaaS companies struggling with high customer churn and poor user onboarding.",
  "Security and compliance officers looking for automated SOC 2 or ISO 27001 readiness.",
  "Founders comparing CRM tools and looking for affordable HubSpot alternatives.",
];

interface BuyerPersona {
  title: string;
  seniority?: string;
  department?: string;
  responsibility?: string;
}

interface ICPFormData {
  name: string;
  description: string;
  status: "ACTIVE" | "INACTIVE" | "ARCHIVED";
  objective: string;
  product_service: string;
  industries: string[];
  company_sizes: string[];
  geographies: string[];
  technologies: string[];
  buyer_personas: BuyerPersona[];
  pain_points: string[];
  buying_triggers: string[];
  keywords: string[];
  exclusions: string[];
  negative_keywords: string[];
}

export function ICPBuilderPage({
  existingId,
  onClose,
}: {
  existingId?: string;
  onClose?: () => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Load existing ICP if editing
  const existingQuery = useQuery<ICPProfile>({
    queryKey: ["ideal-customer-profile", existingId],
    queryFn: ({ signal }) =>
      request<ICPProfile>(`/organization/icps/${existingId}`, { signal }),
    enabled: Boolean(existingId),
  });

  // Form State
  const [formData, setFormData] = useState<ICPFormData>({
    name: "",
    description: "",
    status: "ACTIVE",
    objective: "",
    product_service: "",
    industries: [],
    company_sizes: [],
    geographies: ["North America", "Europe"],
    technologies: [],
    buyer_personas: [
      { title: "VP of Engineering", seniority: "VP / Head of Department", department: "Engineering" },
    ],
    pain_points: [],
    buying_triggers: [],
    keywords: [],
    exclusions: ["Students", "Job seekers", "Non-profits"],
    negative_keywords: ["internship", "hiring", "course", "tutorial"],
  });

  // Input states for comma-separated chips
  const [industryInput, setIndustryInput] = useState("");
  const [geoInput, setGeoInput] = useState("");
  const [techInput, setTechInput] = useState("");
  const [painPointInput, setPainPointInput] = useState("");
  const [triggerInput, setTriggerInput] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [exclusionInput, setExclusionInput] = useState("");

  // AI Chat & Proposal State
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<
    { role: "assistant" | "user"; text: string; proposal?: Partial<ICPFormData> }[]
  >([
    {
      role: "assistant",
      text: "Hi! I am your ICP Intelligence Assistant. Tell me about your product, your target market, or what customer problems you solve, and I will generate an evidence-backed customer profile for you.",
    },
  ]);
  const [aiLoading, setAiLoading] = useState(false);
  const [pendingProposal, setPendingProposal] = useState<{
    proposal: Partial<ICPFormData>;
    summary: string;
  } | null>(null);
  const [historyStack, setHistoryStack] = useState<ICPFormData[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Populate existing data when loaded
  useEffect(() => {
    if (existingQuery.data) {
      const p = existingQuery.data;
      const c = p.criteria || {};
      const company = c.company || {};
      const contact = c.contact || {};
      const intent = c.intent || {};

      const titles = (contact.job_titles as string[]) || [];
      const personas: BuyerPersona[] = titles.map((t) => ({ title: t }));

      setFormData({
        name: p.name || "",
        description: p.description || "",
        status: p.status || "ACTIVE",
        objective: (company.business_objective as string) || "",
        product_service: (company.product_service as string) || "",
        industries: Array.isArray(company.industries) ? company.industries : [],
        company_sizes: Array.isArray(company.size) ? company.size : [],
        geographies: Array.isArray(company.geographies) ? company.geographies : ["North America", "Europe"],
        technologies: Array.isArray(company.technologies) ? company.technologies : [],
        buyer_personas: personas.length > 0 ? personas : [{ title: "Decision Maker" }],
        pain_points: Array.isArray(intent.pain_points) ? intent.pain_points : [],
        buying_triggers: Array.isArray(intent.buying_triggers) ? intent.buying_triggers : [],
        keywords: Array.isArray(intent.keywords) ? intent.keywords : [],
        exclusions: Array.isArray(company.exclusions) ? company.exclusions : [],
        negative_keywords: Array.isArray(intent.negative_keywords) ? intent.negative_keywords : [],
      });
    }
  }, [existingQuery.data]);

  // Handle Add Item to array
  function addItem<K extends keyof ICPFormData>(key: K, item: string) {
    if (!item.trim()) return;
    const current = (formData[key] as string[]) || [];
    if (!current.includes(item.trim())) {
      setFormData({ ...formData, [key]: [...current, item.trim()] });
    }
  }

  function removeItem<K extends keyof ICPFormData>(key: K, index: number) {
    const value=formData[key];if(!Array.isArray(value))return;
    const current = [...value];
    current.splice(index, 1);
    setFormData({ ...formData, [key]: current });
  }

  // AI Assistant Call
  async function handleSendAiMessage(customPrompt?: string) {
    const text = customPrompt || chatInput;
    if (!text.trim() || aiLoading) return;

    const userMsg = { role: "user" as const, text };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setAiLoading(true);

    try {
      // Call backend AI interpret / suggest endpoint
      const response = await request<{
        draft?: {
          name?: string;
          description?: string;
          company_criteria?: ICPProfile['criteria']['company'];
          contact_criteria?: ICPProfile['criteria']['contact'];
          intent_criteria?: ICPProfile['criteria']['intent'];
        };
      }>("/organization/icps/interpret", {
        method: "POST",
        body: JSON.stringify({
          description: text,
          request_id: crypto.randomUUID(),
        }),
      });

      const draft = response.draft;
      if (draft) {
        const company = draft.company_criteria || {};
        const contact = draft.contact_criteria || {};
        const intent = draft.intent_criteria || {};

        const proposed: Partial<ICPFormData> = {
          name: draft.name || formData.name || "Target Customer Profile",
          description: draft.description || formData.description,
          industries: company.industries || formData.industries,
          company_sizes: company.size || formData.company_sizes,
          buyer_personas: (contact.job_titles || []).map((t: string) => ({ title: t })),
          pain_points: intent.pain_points || formData.pain_points,
          buying_triggers: intent.buying_triggers || formData.buying_triggers,
          keywords: intent.keywords || formData.keywords,
          exclusions: company.exclusions || formData.exclusions,
        };

        const summaryText = `I have generated targeting recommendations based on your description:\n\n• **Industries**: ${(proposed.industries || []).join(", ") || "General"}\n• **Key Roles**: ${(proposed.buyer_personas || []).map((b) => b.title).join(", ") || "Decision makers"}\n• **Pain Points**: ${(proposed.pain_points || []).slice(0, 3).join(", ") || "Workflow inefficiency"}\n• **Buying Triggers**: ${(proposed.buying_triggers || []).slice(0, 3).join(", ") || "Software replacement"}\n\nYou can review and apply this proposal to your form below.`;

        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: summaryText, proposal: proposed },
        ]);

        setPendingProposal({
          proposal: proposed,
          summary: `AI suggested ${proposed.industries?.length || 0} industries, ${proposed.buyer_personas?.length || 0} roles, and ${proposed.buying_triggers?.length || 0} buying triggers.`,
        });
      } else {
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "I analyzed your request. I recommend adding specific industries (e.g. B2B SaaS, Fintech) and decision-maker job titles (e.g. VP Engineering, Head of IT) to ensure accurate conversation matching.",
          },
        ]);
      }
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Could not reach AI assistant: ${err instanceof Error ? err.message : "Please check your network connection."}. You can continue configuring manually.`,
        },
      ]);
    } finally {
      setAiLoading(false);
    }
  }

  // Apply AI Proposal
  function handleApplyProposal(prop: Partial<ICPFormData>) {
    setHistoryStack((prev) => [...prev, { ...formData }]);
    setFormData((prev) => ({
      ...prev,
      name: prop.name || prev.name,
      description: prop.description || prev.description,
      industries: prop.industries && prop.industries.length > 0 ? prop.industries : prev.industries,
      company_sizes: prop.company_sizes && prop.company_sizes.length > 0 ? prop.company_sizes : prev.company_sizes,
      buyer_personas: prop.buyer_personas && prop.buyer_personas.length > 0 ? prop.buyer_personas : prev.buyer_personas,
      pain_points: prop.pain_points && prop.pain_points.length > 0 ? prop.pain_points : prev.pain_points,
      buying_triggers: prop.buying_triggers && prop.buying_triggers.length > 0 ? prop.buying_triggers : prev.buying_triggers,
      keywords: prop.keywords && prop.keywords.length > 0 ? prop.keywords : prev.keywords,
      exclusions: prop.exclusions && prop.exclusions.length > 0 ? prop.exclusions : prev.exclusions,
    }));
    setPendingProposal(null);
    toast.success("AI targeting recommendations applied to form.");
  }

  function handleUndo() {
    if (historyStack.length === 0) return;
    const previous = historyStack[historyStack.length - 1];
    setHistoryStack((prev) => prev.slice(0, -1));
    setFormData(previous);
    toast.info("Reverted previous change.");
  }

  // Submit Handler
  async function handleSubmit(asDraft = false) {
    if (!formData.name.trim()) {
      toast.error("Please provide an ICP Name.");
      return;
    }

    setSubmitting(true);
    try {
      const criteriaPayload = {
        company: {
          industries: formData.industries,
          size: formData.company_sizes,
          geographies: formData.geographies,
          technologies: formData.technologies,
          business_objective: formData.objective,
          product_service: formData.product_service,
          exclusions: formData.exclusions,
        },
        contact: {
          job_titles: formData.buyer_personas.map((b) => b.title).filter(Boolean),
          seniority: formData.buyer_personas.map((b) => b.seniority).filter(Boolean),
          departments: formData.buyer_personas.map((b) => b.department).filter(Boolean),
        },
        intent: {
          pain_points: formData.pain_points,
          buying_triggers: formData.buying_triggers,
          keywords: formData.keywords,
          negative_keywords: formData.negative_keywords,
        },
      };

      if (existingId) {
        // PUT update
        await request(`/organization/icps/${existingId}`, {
          method: "PUT",
          body: JSON.stringify({
            name: formData.name.trim(),
            description: formData.description.trim(),
            status: asDraft ? "INACTIVE" : "ACTIVE",
            criteria: criteriaPayload,
            revision: existingQuery.data?.revision || 1,
          }),
        });
        toast.success("Ideal Customer Profile updated.");
      } else {
        // POST create
        await request("/organization/icps", {
          method: "POST",
          body: JSON.stringify({
            name: formData.name.trim(),
            description: formData.description.trim(),
            status: asDraft ? "INACTIVE" : "ACTIVE",
            criteria: criteriaPayload,
            request_id: crypto.randomUUID(),
          }),
        });
        toast.success("Ideal Customer Profile created.");
      }

      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
      if (onClose) {
        onClose();
      } else {
        router.push("/intent-radar/ideal-customers");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="ir-page w-full min-w-0 space-y-6 pb-20">
      {/* 1. Breadcrumb and Back Navigation */}
      <div className="flex items-center justify-between gap-3 border-b border-border/80 pb-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/intent-radar" className="hover:text-foreground transition-colors">
            PlaneByte
          </Link>
          <ChevronRight size={12} />
          <Link href="/intent-radar/ideal-customers" className="hover:text-foreground transition-colors">
            Ideal Customers
          </Link>
          <ChevronRight size={12} />
          <span className="font-medium text-foreground">
            {existingId ? "Edit Profile" : "Create ICP"}
          </span>
        </nav>

        <Link
          href="/intent-radar/ideal-customers"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Profiles</span>
        </Link>
      </div>

      {/* 2. Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          {existingId ? `Edit: ${formData.name || "Customer Profile"}` : "Create Ideal Customer Profile"}
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Define your target accounts, buyer personas, and buying signals. Use AI to refine targeting criteria in real time.
        </p>
      </div>

      {/* 3. 2-Panel Workspace: Left AI Assistant, Right Builder */}
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        {/* LEFT PANEL: Permanent AI ICP Assistant */}
        <aside className="space-y-4 lg:sticky lg:top-4">
          <section
            aria-label="AI ICP Assistant"
            className="rounded-2xl border border-primary/20 bg-card p-4 space-y-3.5 shadow-xs"
          >
            <div className="flex items-center justify-between border-b border-border/80 pb-3">
              <div className="flex items-center gap-2 text-primary font-semibold text-xs">
                <Sparkles size={15} />
                <span>ICP Assistant</span>
              </div>
              {historyStack.length > 0 && (
                <button
                  type="button"
                  onClick={handleUndo}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground cursor-pointer"
                  title="Undo previous change"
                >
                  <Undo2 size={12} />
                  <span>Undo</span>
                </button>
              )}
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Describe your target market, buyer roles, or customer problems to get instant recommendations.
            </p>

            {/* Chat Message Stream */}
            <div className="max-h-[300px] overflow-y-auto space-y-2.5 pr-1 text-xs">
              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-2.5 rounded-xl leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary/10 text-primary font-medium ml-4 border border-primary/20"
                      : "bg-muted/40 text-foreground border border-border/70 mr-2"
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-1 uppercase tracking-wider font-semibold">
                    {msg.role === "assistant" ? <Bot size={12} /> : <Target size={12} />}
                    <span>{msg.role === "assistant" ? "Assistant" : "You"}</span>
                  </div>
                  <div className="whitespace-pre-line text-[11px]">{msg.text}</div>
                  {msg.proposal && (
                    <div className="mt-2 pt-2 border-t border-border/70 flex items-center justify-end">
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => handleApplyProposal(msg.proposal!)}
                        className="h-6 text-[11px] px-2"
                      >
                        Apply Proposal
                      </Button>
                    </div>
                  )}
                </div>
              ))}
              {aiLoading && (
                <div className="p-2.5 rounded-xl bg-muted/40 border border-border/70 text-xs flex items-center gap-2 text-muted-foreground">
                  <Loader2 size={13} className="animate-spin text-primary" />
                  <span>Analyzing company context…</span>
                </div>
              )}
            </div>

            {/* Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSendAiMessage();
              }}
              className="space-y-2 pt-2 border-t border-border/80"
            >
              <div className="relative">
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="e.g. Focus on B2B SaaS founders looking for SOC 2 automation…"
                  rows={2}
                  className="w-full rounded-xl border border-border bg-background p-2.5 pr-9 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs resize-none"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void handleSendAiMessage();
                    }
                  }}
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || aiLoading}
                  className="absolute right-2.5 bottom-3.5 text-primary hover:text-primary/80 disabled:opacity-30 cursor-pointer"
                  aria-label="Send message"
                >
                  <Send size={14} />
                </button>
              </div>

              {/* Example Prompts */}
              <div className="space-y-1 pt-1">
                <span className="text-[10px] font-medium text-muted-foreground block">
                  Quick examples:
                </span>
                <div className="flex flex-col gap-1">
                  {EXAMPLE_AI_PROMPTS.slice(0, 2).map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void handleSendAiMessage(prompt)}
                      className="text-left rounded-lg border border-border/80 bg-background p-1.5 text-[10px] text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer truncate"
                      title={prompt}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </form>
          </section>
        </aside>

        {/* RIGHT PANEL: Structured ICP Configuration */}
        <main className="space-y-6 min-w-0">
          {/* Pending Proposal Banner */}
          {pendingProposal && (
            <div
              role="status"
              className="rounded-xl border border-primary/30 bg-primary/5 p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-xs"
            >
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-primary shrink-0" />
                <span className="text-xs font-semibold text-foreground">
                  {pendingProposal.summary}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPendingProposal(null)}
                  className="h-7 text-xs"
                >
                  Dismiss
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleApplyProposal(pendingProposal.proposal)}
                  className="h-7 text-xs font-semibold"
                >
                  Apply to Form
                </Button>
              </div>
            </div>
          )}

          {/* SECTION 1: Basic Information */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="border-b border-border/70 pb-3">
              <h2 className="text-sm font-bold text-foreground">1. Basic Information</h2>
              <p className="text-xs text-muted-foreground">
                Give your Ideal Customer Profile a descriptive name and business context.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-semibold text-foreground block">
                  ICP Name <span className="text-destructive">*</span>
                </label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Mid-Market B2B SaaS Founders &amp; CTOs"
                  className="h-9 text-xs"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-semibold text-foreground block">
                  Target Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Concise overview of this customer segment and who they are…"
                  rows={2}
                  className="w-full rounded-xl border border-border bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs resize-y"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground block">
                  Associated Product or Service
                </label>
                <Input
                  value={formData.product_service}
                  onChange={(e) => setFormData({ ...formData, product_service: e.target.value })}
                  placeholder="e.g. PlaneByte Lead Engine / Custom CRM"
                  className="h-9 text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground block">
                  Business Objective
                </label>
                <Input
                  value={formData.objective}
                  onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                  placeholder="e.g. Accelerate pipeline for outbound sales"
                  className="h-9 text-xs"
                />
              </div>
            </div>
          </section>

          {/* SECTION 2: Target Companies */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="border-b border-border/70 pb-3">
              <h2 className="text-sm font-bold text-foreground">2. Target Companies &amp; Market</h2>
              <p className="text-xs text-muted-foreground">
                Define the industries, sizes, and geographies that qualify for this segment.
              </p>
            </div>

            {/* Industries */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">
                Target Industries
              </label>
              <div className="flex flex-wrap gap-1.5">
                {formData.industries.map((ind, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs text-primary font-medium"
                  >
                    <span>{ind}</span>
                    <button
                      type="button"
                      onClick={() => removeItem("industries", idx)}
                      className="text-primary hover:text-foreground cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  value={industryInput}
                  onChange={(e) => setIndustryInput(e.target.value)}
                  placeholder="Type industry and press Add or pick below…"
                  className="h-8 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("industries", industryInput);
                      setIndustryInput("");
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    addItem("industries", industryInput);
                    setIndustryInput("");
                  }}
                  className="h-8 text-xs"
                >
                  Add
                </Button>
              </div>

              {/* Common Industry Badges */}
              <div className="flex flex-wrap gap-1 pt-1">
                {COMMON_INDUSTRIES.map((ind) => (
                  <button
                    key={ind}
                    type="button"
                    onClick={() => addItem("industries", ind)}
                    className="rounded-md border border-border/70 bg-background px-2 py-0.5 text-[10px] text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
                  >
                    + {ind}
                  </button>
                ))}
              </div>
            </div>

            {/* Company Sizes */}
            <div className="space-y-2 pt-2 border-t border-border/70">
              <label className="text-xs font-semibold text-foreground block">
                Company Size / Employee Ranges
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {COMPANY_SIZES.map((size) => {
                  const selected = formData.company_sizes.includes(size);
                  return (
                    <button
                      key={size}
                      type="button"
                      onClick={() => {
                        if (selected) {
                          setFormData({
                            ...formData,
                            company_sizes: formData.company_sizes.filter((s) => s !== size),
                          });
                        } else {
                          setFormData({
                            ...formData,
                            company_sizes: [...formData.company_sizes, size],
                          });
                        }
                      }}
                      className={`flex items-center gap-2 p-2 rounded-xl border text-xs font-medium text-left transition-colors cursor-pointer ${
                        selected
                          ? "border-primary bg-primary/10 text-primary font-semibold"
                          : "border-border bg-background text-foreground hover:bg-muted/40"
                      }`}
                    >
                      <div
                        className={`h-3.5 w-3.5 rounded border flex items-center justify-center shrink-0 ${
                          selected ? "bg-primary border-primary text-white" : "border-border"
                        }`}
                      >
                        {selected && <Check size={10} />}
                      </div>
                      <span className="truncate">{size}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Geographies */}
            <div className="space-y-2 pt-2 border-t border-border/70">
              <label className="text-xs font-semibold text-foreground block">
                Geographic Markets
              </label>
              <div className="flex flex-wrap gap-1.5">
                {formData.geographies.map((geo, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground"
                  >
                    <span>{geo}</span>
                    <button
                      type="button"
                      onClick={() => removeItem("geographies", idx)}
                      className="text-muted-foreground hover:text-foreground cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  value={geoInput}
                  onChange={(e) => setGeoInput(e.target.value)}
                  placeholder="e.g. North America, United Kingdom, APAC…"
                  className="h-8 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("geographies", geoInput);
                      setGeoInput("");
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    addItem("geographies", geoInput);
                    setGeoInput("");
                  }}
                  className="h-8 text-xs"
                >
                  Add
                </Button>
              </div>
            </div>
          </section>

          {/* SECTION 3: Decision Makers */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-border/70 pb-3">
              <div>
                <h2 className="text-sm font-bold text-foreground">3. Buyer Personas &amp; Decision Makers</h2>
                <p className="text-xs text-muted-foreground">
                  Specify the job titles and seniority levels of your target buyers.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  setFormData({
                    ...formData,
                    buyer_personas: [
                      ...formData.buyer_personas,
                      { title: "", seniority: "VP / Head of Department", department: "Engineering" },
                    ],
                  })
                }
                className="h-7 text-xs gap-1"
              >
                <Plus size={12} />
                <span>Add Persona</span>
              </Button>
            </div>

            <div className="space-y-3">
              {formData.buyer_personas.map((persona, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl border border-border bg-background space-y-2.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-foreground">
                      Persona #{idx + 1}
                    </span>
                    {formData.buyer_personas.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeItem("buyer_personas", idx)}
                        className="text-muted-foreground hover:text-destructive cursor-pointer"
                        title="Remove persona"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground block">
                        Job Title
                      </label>
                      <Input
                        value={persona.title}
                        onChange={(e) => {
                          const updated = [...formData.buyer_personas];
                          updated[idx].title = e.target.value;
                          setFormData({ ...formData, buyer_personas: updated });
                        }}
                        placeholder="e.g. CTO, VP Product, Head of RevOps"
                        className="h-8 text-xs"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground block">
                        Seniority Level
                      </label>
                      <select
                        aria-label={`Seniority Level for Persona #${idx + 1}`}
                        value={persona.seniority || ""}
                        onChange={(e) => {
                          const updated = [...formData.buyer_personas];
                          updated[idx].seniority = e.target.value;
                          setFormData({ ...formData, buyer_personas: updated });
                        }}
                        className="w-full h-8 rounded-lg border border-border bg-background px-2 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
                      >
                        {SENIORITY_LEVELS.map((lvl) => (
                          <option key={lvl} value={lvl}>
                            {lvl}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground block">
                        Department
                      </label>
                      <Input
                        value={persona.department || ""}
                        onChange={(e) => {
                          const updated = [...formData.buyer_personas];
                          updated[idx].department = e.target.value;
                          setFormData({ ...formData, buyer_personas: updated });
                        }}
                        placeholder="e.g. Engineering, Sales, Security"
                        className="h-8 text-xs"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* SECTION 4: Customer Problems & Pain Points */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="border-b border-border/70 pb-3">
              <h2 className="text-sm font-bold text-foreground">4. Customer Problems &amp; Pain Points</h2>
              <p className="text-xs text-muted-foreground">
                Define the recurring operational challenges and tool frustrations your buyers face.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {formData.pain_points.map((pt, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-md border border-amber-500/25 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700 dark:text-amber-300 font-medium"
                  >
                    <span>{pt}</span>
                    <button
                      type="button"
                      onClick={() => removeItem("pain_points", idx)}
                      className="text-amber-700 dark:text-amber-300 hover:text-foreground cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <Input
                  value={painPointInput}
                  onChange={(e) => setPainPointInput(e.target.value)}
                  placeholder="e.g. High cloud database costs, slow customer onboarding, SOC 2 audit overhead…"
                  className="h-8 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("pain_points", painPointInput);
                      setPainPointInput("");
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    addItem("pain_points", painPointInput);
                    setPainPointInput("");
                  }}
                  className="h-8 text-xs"
                >
                  Add
                </Button>
              </div>
            </div>
          </section>

          {/* SECTION 5: Buying Intent & Triggers */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="border-b border-border/70 pb-3">
              <h2 className="text-sm font-bold text-foreground">5. Buying Intent &amp; Triggers</h2>
              <p className="text-xs text-muted-foreground">
                Specify conversation patterns indicating potential commercial intent (alternatives, recommendations, evaluations).
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {formData.buying_triggers.map((trig, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-300 font-medium"
                  >
                    <span>{trig}</span>
                    <button
                      type="button"
                      onClick={() => removeItem("buying_triggers", idx)}
                      className="text-emerald-700 dark:text-emerald-300 hover:text-foreground cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <Input
                  value={triggerInput}
                  onChange={(e) => setTriggerInput(e.target.value)}
                  placeholder="e.g. Looking for an affordable alternative to HubSpot, evaluating Pinecone vs Qdrant…"
                  className="h-8 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("buying_triggers", triggerInput);
                      setTriggerInput("");
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    addItem("buying_triggers", triggerInput);
                    setTriggerInput("");
                  }}
                  className="h-8 text-xs"
                >
                  Add
                </Button>
              </div>

              {/* Predefined Trigger Chips */}
              <div className="flex flex-wrap gap-1 pt-1">
                {[
                  "Requesting software recommendations",
                  "Evaluating competitor alternatives",
                  "Complaining about existing tool pricing",
                  "Planning database migration",
                  "Seeking custom development partner",
                ].map((trig) => (
                  <button
                    key={trig}
                    type="button"
                    onClick={() => addItem("buying_triggers", trig)}
                    className="rounded-md border border-border/70 bg-background px-2 py-0.5 text-[10px] text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors cursor-pointer"
                  >
                    + {trig}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* SECTION 6: Exclusions */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="border-b border-border/70 pb-3">
              <h2 className="text-sm font-bold text-foreground">6. Exclusions &amp; Negative Filters</h2>
              <p className="text-xs text-muted-foreground">
                Filter out irrelevant discussions, hobbyists, or non-commercial queries.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {formData.exclusions.map((excl, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded-md border border-destructive/20 bg-destructive/10 px-2 py-0.5 text-xs text-destructive font-medium"
                  >
                    <span>{excl}</span>
                    <button
                      type="button"
                      onClick={() => removeItem("exclusions", idx)}
                      className="text-destructive hover:text-foreground cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <Input
                  value={exclusionInput}
                  onChange={(e) => setExclusionInput(e.target.value)}
                  placeholder="e.g. Students, recruitment, hobby projects, free open-source users…"
                  className="h-8 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("exclusions", exclusionInput);
                      setExclusionInput("");
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    addItem("exclusions", exclusionInput);
                    setExclusionInput("");
                  }}
                  className="h-8 text-xs"
                >
                  Add
                </Button>
              </div>
            </div>
          </section>

          {/* SECTION 7: Review & Sticky Action Bar */}
          <div className="sticky bottom-0 z-20 mt-6 rounded-xl border border-border bg-card/95 backdrop-blur-xs p-3.5 shadow-lg flex items-center justify-between gap-3">
            <Link
              href="/intent-radar/ideal-customers"
              className="inline-flex h-8 items-center rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </Link>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={submitting}
                onClick={() => void handleSubmit(true)}
                className="h-8 text-xs font-medium"
              >
                Save as Draft
              </Button>

              <Button
                type="button"
                variant="default"
                size="sm"
                disabled={submitting || !formData.name.trim()}
                onClick={() => void handleSubmit(false)}
                className="h-8 text-xs font-semibold"
              >
                {submitting ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Saving…</span>
                  </>
                ) : existingId ? (
                  <span>Update Profile</span>
                ) : (
                  <span>Create ICP Profile</span>
                )}
              </Button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
