"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  ExternalLink,
  Eye,
  Filter,
  History,
  Info,
  Loader2,
  Play,
  Plus,
  Radio,
  RotateCcw,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Undo2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  INTENT_CATEGORIES,
  emptyIntentSearch,
  type IntentCategory,
  type IntentJob,
  type IntentSearch,
  type SearchStrategy,
  type SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { SourceConfigDrawer } from "./SourceConfigDrawer";
import { DISCOVERY_PRELOAD_KEY } from "./DiscoveryCopilotPanel";

interface DraftReply { schema_version:1; draft:{name:string;configuration:IntentSearch;strategy?:SearchStrategy}; mode:string; fallback_reason?:string; }
interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
  timestamp: string;
  proposedChanges?: {
    setup?:IntentSearch; name?:string; base?:string;
    objective?: string;
    keywordsToAdd?: string[];
    keywordsToRemove?: string[];
    sourcesToEnable?: SourceId[];
    categories?: IntentCategory[];
    minRelevance?: number;
    dateRange?: string;
  };
  applied?: boolean;
}

const STARTER_PROMPTS = [
  "Founders complaining about CRM complexity & cost",
  "DevOps teams comparing Terraform vs Pulumi",
  "Security managers evaluating SOC 2 automation tools",
  "Companies seeking AI agent workflows & automation",
];

const INTENT_CATEGORY_DESCRIPTIONS: Record<IntentCategory, string> = {
  "Purchase consideration": "Actively looking to buy a solution",
  "Product comparison": "Comparing 2+ competing tools",
  "Tool / service evaluation": "Evaluating technical capabilities",
  "Problem / pain point": "Expressing frustration or dissatisfaction",
  "Recommendation request": "Asking community for tool suggestions",
  "Alternative search": "Seeking alternatives to a specific tool",
  "Feature request": "Requesting features or workarounds",
  "Competitor activity": "Discussions mentioning competitors",
  "Market / technology intelligence": "Trends and industry shifts",
  "General discussion": "Broad conversations in your space",
  "Uncertain": "Unclassified conversational signals",
};

export function CreateDiscoveryPage() {
  const router=useRouter();
  const [dateAnchor]=useState(()=>Date.now());

  let savedSearchId: string | null = null;
  let fromSetup=false;
  try {
    const sp = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    savedSearchId = sp?.get("saved_search_id") || null;
    fromSetup=sp?.get('from')==='onboarding'&&!savedSearchId;
  } catch {
    // ignore
  }

  const access = useRadarCapabilities();
  const setupDefaults=useRadarRead<{discovery_keywords?:string[];discovery_excluded?:string[];default_icp_id?:string|null}>('/settings',fromSetup);
  const prefilled=useRef(false);
  const mutation = useRadarMutation();
  const feedQuery=useRadarRead<{items:{id:string;family:SourceId;enabled:boolean}[]}>('/sources/configurations');
  const attempt=useRef<{payload:string;id:string}|null>(null);
  const sending=useRef(false);
  const canWrite = Boolean(access.data?.can_write);

  // ICPs Query
  const icpsQuery = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const icps = icpsQuery.data?.items || [];

  // Saved Search prefill
  const savedSearchQuery = useRadarRead<{
    id: string;
    name: string;
    original_prompt?: string;
    configuration: IntentSearch;
  }>(`/saved-searches/${savedSearchId}`, Boolean(savedSearchId));

  // 1. Core Form State
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [selectedIcpId, setSelectedIcpId] = useState<string>("");

  // 2. Search Criteria
  const [config, setConfig] = useState<IntentSearch>(() => emptyIntentSearch());
  const offerings=useRadarRead<{items:string[]}>('/discover/offerings',!!config.semantic);

  // Input fields for adding chips
  const [keywordInput, setKeywordInput] = useState("");
  const [phraseInput, setPhraseInput] = useState("");
  const [excludedInput, setExcludedInput] = useState("");
  const [topicInput, setTopicInput] = useState("");

  // Drawer for per-source configuration
  const [configuringSource, setConfiguringSource] = useState<SourceId | null>(null);

  // Undo / History Stack
  const [formHistory, setFormHistory] = useState<{
    name: string;
    objective: string;
    config: IntentSearch; icp:string;
  }[]>([]);

  // 3. AI Assistant State
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [mobileAssistantOpen, setMobileAssistantOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Describe the discussions you want to find. Describe the conversations, problems, or buyer signals you want to uncover. I'll automatically formulate keywords, select research sources, and configure filters for your research run.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Save Search Modal State
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveSearchName, setSaveSearchName] = useState("");
  const [savingSearch, setSavingSearch] = useState(false);

  // Submitting / Running State
  const [running, setRunning] = useState(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  // Pre-load from Saved Search or Preload Key
  useEffect(() => {
    if(fromSetup){
      if(!prefilled.current&&setupDefaults.data){prefilled.current=true;const prefs=setupDefaults.data;setConfig(v=>({...v,keywords:v.keywords.length?v.keywords:prefs.discovery_keywords||[],excluded:v.excluded.length?v.excluded:prefs.discovery_excluded||[]}));setSelectedIcpId(v=>v||prefs.default_icp_id||'');}
      return;
    }
    if (savedSearchQuery.data) {
      const item = savedSearchQuery.data;
      setName(item.name || "Saved Search Discovery");
      setObjective(item.original_prompt || "");
      if (item.configuration) {
        setConfig(item.configuration);
        if (item.configuration.icp_id) {
          setSelectedIcpId(String(item.configuration.icp_id));
        }
      }
      toast.info(`Loaded criteria from saved search "${item.name}".`);
      return;
    }

    try {
      const raw = sessionStorage.getItem(DISCOVERY_PRELOAD_KEY);
      if (raw) {
        sessionStorage.removeItem(DISCOVERY_PRELOAD_KEY);
        const parsed = JSON.parse(raw);
        if (parsed.title) setName(parsed.title);
        if (parsed.original_prompt) setObjective(parsed.original_prompt);
        if (parsed.configuration) {
          setConfig(parsed.configuration);
          if (parsed.configuration.icp_id) {
            setSelectedIcpId(String(parsed.configuration.icp_id));
          }
        }
        toast.info("Restored discovery parameters.");
      }
    } catch {
      // ignore
    }
  }, [savedSearchQuery.data,fromSetup,setupDefaults.data]);

  // Ensure default sources if empty
  useEffect(() => {
    if (!config.sources || config.sources.length === 0) {
      const available = access.data?.sources.filter(s=>['Available','Connected'].includes(s.state)).map(s=>s.id||'hacker_news');
      const defaults: SourceId[] = available && available.length > 0 ? [available[0]] : ["hacker_news"];
      setConfig((prev) => ({ ...prev, sources: defaults }));
    }
  }, [access.data]);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    if (typeof chatBottomRef.current?.scrollIntoView === "function") {
      chatBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, assistantLoading]);

  // Push state to undo stack
  const pushHistory = () => {
    setFormHistory((prev) => [
      ...prev.slice(-10),
      {
        name,
        objective,
        config: JSON.parse(JSON.stringify(config)),icp:selectedIcpId,
      },
    ]);
  };

  const handleUndo = () => {
    if (formHistory.length === 0) return;
    const last = formHistory[formHistory.length - 1];
    setFormHistory((prev) => prev.slice(0, -1));
    setName(last.name);
    setObjective(last.objective);
    setConfig(last.config);setSelectedIcpId(last.icp);
    toast.info("Undid last AI changes.");
  };

  // Helper chip adders
  const addChip = (
    field: "keywords" | "phrases" | "excluded" | "topics",
    val: string,
    clearInput: () => void
  ) => {
    const raw = val.split(",").map((s) => s.trim()).filter(Boolean);
    if (raw.length === 0) return;
    pushHistory();
    const current = config[field] || [];
    const next = Array.from(new Set([...current, ...raw])).slice(0, 12);
    setConfig({ ...config, [field]: next });
    clearInput();
  };

  const removeChip = (field: "keywords" | "phrases" | "excluded" | "topics", target: string) => {
    pushHistory();
    const current = config[field] || [];
    setConfig({ ...config, [field]: current.filter((x) => x !== target) });
  };

  const toggleSource = (sourceId: SourceId) => {
    pushHistory();
    const current = config.sources || [];
    const next = current.includes(sourceId)
      ? current.filter((s) => s !== sourceId)
      : [...current, sourceId];
    setConfig({ ...config, sources: next, feed_ids:(config.feed_ids||[]).filter(id=>!(feedQuery.data?.items||[]).some(f=>f.id===id&&!next.includes(f.family))) });
  };

  const toggleCategory = (category: IntentCategory) => {
    pushHistory();
    const current = config.categories || [];
    const next = current.includes(category)
      ? current.filter((c) => c !== category)
      : [...current, category];
    setConfig({ ...config, categories: next });
  };

  // AI Assistant Chat Submission
  const handleSendAssistant = async (textToSend?: string) => {
    const prompt = (textToSend || assistantInput).trim();
    if (!prompt || assistantLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${crypto.randomUUID()}`,
      role: "user",
      content: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setAssistantInput("");
    setAssistantLoading(true);

    try {
      const res=await mutation.mutateAsync({path:'/draft',body:{prompt,previous:config.keywords.length?config:null,icp_id:selectedIcpId||null}}) as DraftReply;
      if(res.schema_version!==1||!res.draft?.configuration?.keywords?.length||!res.draft.configuration.sources?.length)throw Error('No usable search setup was returned.');
      const setup=res.draft.configuration;
      setMessages(prev=>[...prev,{id:crypto.randomUUID(),role:'assistant',content:res.fallback_reason || 'Review the proposed setup before applying it.',timestamp:new Date().toLocaleTimeString(),proposedChanges:{objective:res.draft.strategy?.objective||prompt,name:res.draft.name,setup,base:JSON.stringify([config,objective,name,selectedIcpId]),keywordsToAdd:setup.keywords,sourcesToEnable:setup.sources,categories:setup.categories}}]);
    } catch(err){
      setAssistantInput(prompt);setErrorNotice(err instanceof Error?err.message:'Could not generate a setup. Retry or continue manually.');
    } finally {
      setAssistantLoading(false);
    }
  };

  // Apply AI Proposed Changes
  const handleApplyProposal = (msgId: string, changes: NonNullable<ChatMessage["proposedChanges"]>) => {
    if(!changes.setup || changes.base!==JSON.stringify([config,objective,name,selectedIcpId])){setErrorNotice('Your draft changed. Generate a new proposal before applying.');return;}
    pushHistory();setName(changes.name||name);setObjective(changes.objective||objective);setSelectedIcpId(changes.setup.icp_id||selectedIcpId);setConfig({...config,...changes.setup});
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, applied: true } : m))
    );
    toast.success("Applied AI recommendations to form.");
  };

  // Validation
  const validation = useMemo(() => {
    const hasName = Boolean(name.trim());
    const hasKeywords = (config.keywords || []).length > 0;
    const hasSources = (config.sources || []).length > 0;


    const issues: string[] = [];
    if (!hasKeywords) issues.push("Add at least one keyword");
    if (!hasSources) issues.push("Select at least one research source");
    if(config.semantic&&!config.offerings.trim())issues.push('Enter a relevant offering or select keyword matching.');
    for(const id of config.sources||[]){const source=access.data?.sources.find(s=>(s.id||'hacker_news')===id);if(!source||!['Available','Connected'].includes(source.state)){issues.push((source?.name||id)+': unavailable or not configured.');continue;}
      if(['atom','discourse','rss'].includes(id)&&!(feedQuery.data?.items||[]).some(f=>f.enabled&&f.family===id&&config.feed_ids?.includes(f.id)))issues.push('Choose an approved feed for '+source.name+'.');}
    const isValid=issues.length===0;

    return { isValid, issues, hasKeywords, hasSources, hasName };
  }, [name,config,access.data,feedQuery.data]);

  // Execute Discovery Run
  const handleRunDiscovery = async () => {
    if (!canWrite) {
      toast.error("You have read-only access to this workspace.");
      return;
    }
    if (!config.keywords || config.keywords.length === 0) {
      setErrorNotice("Please add at least one keyword in Section 2.");
      toast.error("Please add at least one keyword in Section 2.");
      const el = document.getElementById("section-keywords");
      if (typeof el?.scrollIntoView === "function") el.scrollIntoView({ behavior: "smooth" });
      return;
    }
    if (!config.sources || config.sources.length === 0) {
      setErrorNotice("Please select at least one research source in Section 3.");
      toast.error("Please select at least one research source in Section 3.");
      const el = document.getElementById("section-sources");
      if (typeof el?.scrollIntoView === "function") el.scrollIntoView({ behavior: "smooth" });
      return;
    }

    if(!validation.isValid){setErrorNotice(validation.issues.join(" "));return;}
    if(sending.current)return;
    const finalName = name.trim() || `Discovery: ${config.keywords.slice(0, 3).join(", ")}`;

    // Date range validation: Ensure YYYY-MM-DD format (no time strings)
    let fromDate = config.from_date || null;
    let toDate = config.to_date || null;
    if (fromDate && fromDate.includes("T")) {
      fromDate = fromDate.slice(0, 10);
    }
    if (toDate && toDate.includes("T")) {
      toDate = toDate.slice(0, 10);
    }
    if (fromDate && toDate && fromDate > toDate) {
      setErrorNotice("Start date cannot be after end date.");
      toast.error("Start date cannot be after end date.");
      return;
    }

    // Result limit validation: Enforce <= 20
    const clampedLimit = Math.min(20, Math.max(1, Number(config.result_limit) || 20));

    // Determine canonical search mode: 'ai' | 'advanced' | 'monitor' | 'rerun'
    const searchMode: "ai" | "advanced" = messages.length > 1 ? "ai" : "advanced";

    sending.current=true;setRunning(true);
    setErrorNotice(null);

    try {
      const configuration={...config,from_date:fromDate,to_date:toDate,result_limit:clampedLimit,icp_id:selectedIcpId||null};
      const check=await mutation.mutateAsync({path:'/discover/preflight',body:configuration}) as {executable:boolean;issue?:string};
      if(!check.executable)throw Error(check.issue||'Search setup could not be verified.');
      const payload=JSON.stringify([configuration,finalName,objective]);if(attempt.current?.payload!==payload)attempt.current={payload,id:crypto.randomUUID()};
      const res = (await mutation.mutateAsync({
        path: "/discover",body:{title:finalName,original_prompt:objective||finalName,configuration,request_id:attempt.current.id,
          search_mode: searchMode,
        },
      })) as IntentJob;

      toast.success("Discovery job started successfully.");
      const runId = res.discovery_id || res.id;
      router.push(`/intent-radar/discover/runs/${runId}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to execute discovery run.";
      setErrorNotice(msg);
      toast.error(msg);
      sending.current=false;setRunning(false);
    }
  };

  // Save Search Reusable
  const handleSaveSearch = async () => {
    const searchTitle = (saveSearchName || name).trim() || `Search: ${config.keywords.slice(0, 3).join(", ")}`;
    if (!config.keywords.length) {
      toast.error("Cannot save search without keywords.");
      return;
    }

    setSavingSearch(true);
    try {
      await mutation.mutateAsync({
        path: "/saved-searches",
        body: {
          name: searchTitle,
          description: objective || "",
          original_prompt: objective || searchTitle,
          configuration: {
            ...config,
            icp_id: selectedIcpId || null,
          },
        },
      });
      setSaveModalOpen(false);
      toast.success(`Saved search "${searchTitle}" saved to workspace.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save search.");
    } finally {
      setSavingSearch(false);
    }
  };

  const selectedIcpName = icps.find((i) => i.id === selectedIcpId)?.name;
  const availableSources=access.data?.sources||[];

  return (
    <div className="ir-page w-full min-w-0 space-y-6">
      {/* 1. Page Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              href="/intent-radar/discover"
              className="hover:text-foreground transition-colors inline-flex items-center gap-1"
            >
              <ArrowLeft size={13} />
              <span>Discover</span>
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">New Discovery</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Create Discovery
          </h1>
          <p className="text-xs text-muted-foreground">
            Configure keywords and research parameters, or collaborate with the Discovery Assistant.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {formHistory.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleUndo}
              className="gap-1.5 text-xs h-8 cursor-pointer"
            >
              <Undo2 size={13} />
              <span>Undo Changes</span>
            </Button>
          )}

        </div>
      </header>

      {/* Global Error Banner if any */}
      {errorNotice && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs text-destructive flex items-center justify-between gap-3"
        >
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="shrink-0" />
            <span>{errorNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorNotice(null)}
            className="text-destructive/80 hover:text-destructive cursor-pointer"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Mobile/Tablet Assistant Floating Trigger */}
      <div className="flex items-center justify-between rounded-xl border border-primary/30 bg-primary/5 p-3 text-xs">
        <div className="flex items-center gap-2 text-foreground font-medium">
          <Bot size={16} className="text-primary" />
          <span>Need help crafting your search?</span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMobileAssistantOpen(true)}
          className="h-7 text-xs gap-1.5 border-primary/40 text-primary hover:bg-primary/10"
        >
          <Sparkles size={12} />
          <span>Open AI Assistant</span>
        </Button>
      </div>

      {/* 2. Main Two-Column Layout */}
      <div className="mx-auto w-full min-w-0 max-w-5xl space-y-4">
        {/* LEFT COLUMN: Permanent AI Discovery Assistant */}
        <aside
          className={`rounded-2xl border border-border bg-card p-4 shadow-xs overflow-hidden ${
            mobileAssistantOpen ? "flex flex-col max-h-[70vh]" : "hidden"
          }`}
        >
          {/* Assistant Header */}
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 font-semibold text-foreground text-sm">
                <Sparkles size={15} className="text-primary" />
                <span>Discovery Assistant</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-tight">
                Describe what you want to find. I&apos;ll help configure your search.
              </p>
            </div>

            <div className="flex items-center gap-1">
              {mobileAssistantOpen && (
                <button
                  type="button"
                  onClick={() => setMobileAssistantOpen(false)}
                  className="rounded-lg p-1 text-muted-foreground hover:bg-muted cursor-pointer"
                  aria-label="Close assistant"
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </div>

          {/* Active Context Badges */}
          <div className="flex items-center gap-1.5 py-2 border-b border-border/60 text-[10px] text-muted-foreground overflow-x-auto">
            <span className="rounded-md border border-border bg-muted/30 px-1.5 py-0.5 font-medium text-foreground shrink-0">
              Discovery setup
            </span>
            <span className="rounded-md border border-border bg-muted/30 px-1.5 py-0.5 font-medium text-foreground shrink-0">
              ICP: {selectedIcpName || "All ICPs"}
            </span>
            {config.keywords.length > 0 && (
              <span className="rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 font-medium text-primary shrink-0">
                {config.keywords.length} keywords active
              </span>
            )}
          </div>

          {/* Scrollable Chat Area */}
          <div className="flex-1 overflow-y-auto py-3 space-y-3.5 pr-1 min-h-[220px]">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`space-y-2 text-xs ${
                  m.role === "user" ? "ml-auto max-w-[85%]" : "mr-auto max-w-full"
                }`}
              >
                <div
                  className={`rounded-xl p-3 leading-relaxed ${
                    m.role === "user"
                      ? "bg-slate-800 text-white font-medium dark:bg-slate-200 dark:text-slate-950"
                      : "border border-border/80 bg-muted/20 text-foreground"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                </div>

                {/* Structured Proposed Changes Diff Card */}
                {m.proposedChanges && (
                  <div className="rounded-xl border border-primary/30 bg-primary/5 p-3 space-y-2.5 text-xs text-foreground">
                    <div className="flex items-center justify-between border-b border-primary/20 pb-1.5">
                      <span className="font-semibold text-primary inline-flex items-center gap-1">
                        <Sparkles size={12} /> Proposed Search Criteria
                      </span>
                      <span className="rounded-full bg-primary/20 px-1.5 py-0.2 text-[10px] font-semibold text-primary">
                        {m.applied ? "Applied" : "Diff Preview"}
                      </span>
                    </div>

                    <div className="space-y-1 text-[11px] text-muted-foreground">
                      {m.proposedChanges.objective && (
                        <p>
                          <strong className="text-foreground">Objective:</strong>{" "}
                          {m.proposedChanges.objective.slice(0, 90)}...
                        </p>
                      )}
                      {m.proposedChanges.keywordsToAdd && m.proposedChanges.keywordsToAdd.length > 0 && (
                        <div>
                          <strong className="text-foreground">Keywords ({m.proposedChanges.keywordsToAdd.length}):</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {m.proposedChanges.keywordsToAdd.map((kw) => (
                              <span
                                key={kw}
                                className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary font-medium"
                              >
                                + {kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {m.proposedChanges.sourcesToEnable && m.proposedChanges.sourcesToEnable.length > 0 && (
                        <p>
                          <strong className="text-foreground">Sources:</strong>{" "}
                          {m.proposedChanges.sourcesToEnable.join(", ")}
                        </p>
                      )}
                      {m.proposedChanges.categories && m.proposedChanges.categories.length > 0 && (
                        <p>
                          <strong className="text-foreground">Categories:</strong>{" "}
                          {m.proposedChanges.categories.slice(0, 2).join(", ")}
                          {m.proposedChanges.categories.length > 2 ? ` +${m.proposedChanges.categories.length - 2}` : ""}
                        </p>
                      )}
                    </div>

                    {!m.applied ? (
                      <div className="flex items-center justify-end gap-2 pt-1 border-t border-primary/20">
                        <button
                          type="button"
                          onClick={() => {
                            setMessages((prev) => prev.filter((msg) => msg.id !== m.id));
                          }}
                          className="text-[11px] text-muted-foreground hover:text-foreground cursor-pointer px-2 py-1"
                        >
                          Discard
                        </button>
                        <Button
                          size="sm"
                          onClick={() => handleApplyProposal(m.id, m.proposedChanges!)}
                          className="h-7 text-xs px-2.5 font-medium gap-1"
                        >
                          <Check size={12} />
                          <span>Apply to Form</span>
                        </Button>
                      </div>
                    ) : (
                      <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1 pt-1">
                        <CheckCircle2 size={12} /> Criteria applied to form sections
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {assistantLoading && (
              <div className="flex items-center gap-2 rounded-xl border border-border/80 bg-muted/20 p-3 text-xs text-muted-foreground">
                <Loader2 size={13} className="animate-spin text-primary" />
                <span>Formulating search criteria &amp; keywords…</span>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Starter Pills */}
          <div className="pt-2 border-t border-border/70 space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
              Quick Starters
            </span>
            <div className="flex flex-wrap gap-1">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void handleSendAssistant(prompt)}
                  disabled={assistantLoading}
                  className="rounded-lg border border-border/80 bg-background px-2 py-1 text-[10px] text-muted-foreground hover:border-primary/50 hover:text-foreground hover:bg-muted/40 transition-colors cursor-pointer text-left whitespace-normal break-words max-w-full"
                  title={prompt}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void handleSendAssistant();
            }}
            className="pt-2.5 flex items-center gap-1.5"
          >
            <input
              type="text"
              value={assistantInput}
              onChange={(e) => setAssistantInput(e.target.value)}
              placeholder="e.g. Find teams looking for Postgres alternatives…"
              disabled={assistantLoading}
              className="flex-1 h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="submit"
              disabled={!assistantInput.trim() || assistantLoading}
              className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-40 transition-colors cursor-pointer shrink-0"
              aria-label="Send to assistant"
            >
              {assistantLoading ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
            </button>
          </form>
        </aside>

        {/* RIGHT COLUMN: Main Discovery Configuration (5 Logical Sections) */}
        <main className="space-y-6 min-w-0">
          {/* Section Navigation Tabs */}


          {/* SECTION 1: Discovery Objective */}
          <section
            id="section-objective"
            className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs scroll-mt-20"
          >
            <div className="border-b border-border/80 pb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                Section 1
              </span>
              <h2 className="text-base font-semibold text-foreground">Discovery Objective</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Define the high-level intent and business context for this discovery run.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="disc-name" className="text-xs font-semibold text-foreground flex items-center gap-1">
                  <span>Discovery Name</span>
                  <span className="text-destructive">*</span>
                </label>
                <input
                  id="disc-name"
                  type="text"
                  maxLength={120}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. CRM Alternatives & Dissatisfaction Discussions"
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="disc-icp" className="text-xs font-semibold text-foreground">
                  Target Ideal Customer Profile (ICP)
                </label>
                <select
                  id="disc-icp"
                  value={selectedIcpId}
                  onChange={(e) => setSelectedIcpId(e.target.value)}
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value="">All / Workspace Default</option>
                  {icps.map((icp, idx) => (
                    <option key={icp.id || icp.name || idx} value={icp.id || icp.name}>
                      {icp.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="disc-objective" className="text-xs font-semibold text-foreground">
                Research Objective &amp; Business Context
              </label>
              <textarea
                id="disc-objective"
                rows={3}
                maxLength={1000}
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="What specific buyer conversations, pain points, or buying signals should this discovery run target?"
                className="w-full rounded-lg border border-border bg-background p-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
              />
            </div>
          </section>

          {/* SECTION 2: Keywords & Search Criteria */}
          <section
            id="section-keywords"
            className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs scroll-mt-20"
          >
            <div className="border-b border-border/80 pb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                Section 2
              </span>
              <h2 className="text-base font-semibold text-foreground">Keywords &amp; Search Criteria</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Targeted terms, verbatim phrases, and noise exclusions used across all selected sources.
              </p>
            </div>

            {/* Primary Keywords */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label htmlFor="add-kw" className="text-xs font-semibold text-foreground flex items-center gap-1">
                  <span>Primary Keywords</span>
                  <span className="text-destructive">*</span>
                  <span className="text-muted-foreground font-normal text-[11px]">
                    ({config.keywords.length} active)
                  </span>
                </label>
                <span className="text-[11px] text-muted-foreground">Press Enter or comma to add</span>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-lg border border-border bg-background min-h-[42px]">
                {config.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="inline-flex items-center gap-1 rounded-md bg-primary/10 border border-primary/20 px-2 py-0.5 text-xs text-primary font-medium"
                  >
                    <span>{kw}</span>
                    <button
                      type="button"
                      onClick={() => removeChip("keywords", kw)}
                      className="hover:text-primary-foreground hover:bg-primary/30 rounded p-0.5 cursor-pointer"
                      aria-label={`Remove keyword ${kw}`}
                    >
                      <X size={11} />
                    </button>
                  </span>
                ))}
                <input
                  id="add-kw"
                  type="text"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === ",") {
                      e.preventDefault();
                      addChip("keywords", keywordInput, () => setKeywordInput(""));
                    }
                  }}
                  placeholder={config.keywords.length === 0 ? "Type keyword (e.g. CRM alternative) and press Enter" : "Add keyword…"}
                  className="flex-1 min-w-[160px] bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
                />
              </div>
            </div>

            {/* Exact Phrases & Exclusions in 2 Columns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              {/* Exact Phrases */}
              <div className="space-y-1.5">
                <label htmlFor="add-phrase" className="text-xs font-semibold text-foreground">
                  Exact Phrases (Verbatim)
                </label>
                <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-lg border border-border bg-background min-h-[38px]">
                  {config.phrases.map((phrase) => (
                    <span
                      key={phrase}
                      className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs text-foreground font-medium"
                    >
                      <span>&ldquo;{phrase}&rdquo;</span>
                      <button
                        type="button"
                        onClick={() => removeChip("phrases", phrase)}
                        className="hover:text-destructive rounded p-0.5 cursor-pointer"
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ))}
                  <input
                    id="add-phrase"
                    type="text"
                    value={phraseInput}
                    onChange={(e) => setPhraseInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        addChip("phrases", phraseInput, () => setPhraseInput(""));
                      }
                    }}
                    placeholder="Exact phrase…"
                    className="flex-1 min-w-[120px] bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
                  />
                </div>
              </div>

              {/* Exclusions */}
              <div className="space-y-1.5">
                <label htmlFor="add-exclusion" className="text-xs font-semibold text-foreground">
                  Negative Exclusions (Noise Filter)
                </label>
                <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-lg border border-border bg-background min-h-[38px]">
                  {config.excluded.map((ex) => (
                    <span
                      key={ex}
                      className="inline-flex items-center gap-1 rounded-md bg-destructive/10 border border-destructive/20 px-2 py-0.5 text-xs text-destructive font-medium"
                    >
                      <span>-{ex}</span>
                      <button
                        type="button"
                        onClick={() => removeChip("excluded", ex)}
                        className="hover:text-destructive rounded p-0.5 cursor-pointer"
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ))}
                  <input
                    id="add-exclusion"
                    type="text"
                    value={excludedInput}
                    onChange={(e) => setExcludedInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        addChip("excluded", excludedInput, () => setExcludedInput(""));
                      }
                    }}
                    placeholder="Exclude term (e.g. hiring, job, crack)…"
                    className="flex-1 min-w-[120px] bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
                  />
                </div>
              </div>
            </div>

            {/* 10 Intent Categories */}
            <div className="space-y-2 pt-2 border-t border-border/70">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">
                  Intent Categories ({config.categories.length ? `${config.categories.length} selected` : "All matched"})
                </span>
                <button
                  type="button"
                  onClick={() => {
                    pushHistory();
                    setConfig({
                      ...config,
                      categories:
                        config.categories.length === INTENT_CATEGORIES.length ? [] : [...INTENT_CATEGORIES],
                    });
                  }}
                  className="text-[11px] text-primary hover:underline font-medium cursor-pointer"
                >
                  {config.categories.length === INTENT_CATEGORIES.length ? "Deselect All" : "Select All"}
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {INTENT_CATEGORIES.map((cat) => {
                  const selected = config.categories.includes(cat);
                  return (
                    <label
                      key={cat}
                      className={`flex items-start gap-2 rounded-xl border p-2.5 cursor-pointer transition-colors text-xs select-none ${
                        selected
                          ? "border-primary/50 bg-primary/10 text-primary font-medium"
                          : "border-border bg-background text-muted-foreground hover:border-primary/30 hover:text-foreground"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleCategory(cat)}
                        className="mt-0.5 h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary"
                      />
                      <div className="space-y-0.5">
                        <span className="block font-medium text-foreground">{cat}</span>
                        <span className="block text-[10px] text-muted-foreground leading-tight">
                          {INTENT_CATEGORY_DESCRIPTIONS[cat] || "Relevant discussion category"}
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          </section>

          {/* SECTION 3: Research Sources */}
          <section
            id="section-sources"
            className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs scroll-mt-20"
          >
            <div className="border-b border-border/80 pb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                Section 3
              </span>
              <h2 className="text-base font-semibold text-foreground">Research Sources</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Select the platforms to scan for this discovery run. Configure specific subreddits, repos, or tags as needed.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {availableSources.map((source, idx) => {
                const sId = (source.id || "hacker_news") as SourceId;
                const isSelected = (config.sources || []).includes(sId);

                return (
                  <div
                    key={source.id || idx}
                    className={`rounded-xl border p-3.5 space-y-3 transition-colors ${
                      isSelected
                        ? "border-primary/60 bg-primary/5 shadow-xs"
                        : "border-border bg-background hover:border-border/80"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ProviderLogo provider={source.name} size={18} />
                        <span className="text-xs font-semibold text-foreground">{source.name}</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSource(sId)}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                        disabled={!isSelected&&!(["Available","Connected"].includes(source.state))}
                        aria-label={`Toggle ${source.name}`}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/60">
                      <span>{!['Available','Connected'].includes(source.state)?source.state:['atom','rss','discourse'].includes(sId)?(feedQuery.data?.items||[]).some(f=>f.enabled&&f.family===sId&&config.feed_ids?.includes(f.id))?'Feed selected':'Select approved feed':'Available'}</span>
                      {true && (
                        <button
                          type="button"
                          onClick={() => setConfiguringSource(sId)}
                          aria-label={`Configure ${source.name}`}
                          className="text-primary hover:underline font-medium inline-flex items-center gap-1 cursor-pointer"
                        >
                          <SlidersHorizontal size={11} />
                          <span>Configure</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* SECTION 4: Advanced Filters */}
          <details id="section-filters" className="rounded-lg border bg-card p-4 space-y-3"><summary className="cursor-pointer font-semibold">Advanced Filters</summary>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Date Range: Ensure YYYY-MM-DD date-only string */}
              <div className="space-y-1.5">
                <label htmlFor="filter-daterange" className="text-xs font-semibold text-foreground">
                  Time Horizon
                </label>
                <select
                  id="filter-daterange"
                  value={
                    !config.from_date
                      ? "any"
                      : config.from_date.slice(0, 10) === new Date(dateAnchor - 86400000).toISOString().slice(0, 10)
                      ? "24h"
                      : config.from_date.slice(0, 10) === new Date(dateAnchor - 7 * 86400000).toISOString().slice(0, 10)
                      ? "7d"
                      : config.from_date.slice(0, 10) === new Date(dateAnchor - 30 * 86400000).toISOString().slice(0, 10)
                      ? "30d"
                      : "custom"
                  }
                  onChange={(e) => {
                    const val = e.target.value;
                    pushHistory();
                    const formatDateOnly = (ms: number) => new Date(Date.now() - ms).toISOString().slice(0, 10);
                    if (val === "any") {
                      setConfig({ ...config, from_date: null });
                    } else if (val === "24h") {
                      setConfig({ ...config, from_date: formatDateOnly(86400000) });
                    } else if (val === "7d") {
                      setConfig({ ...config, from_date: formatDateOnly(7 * 86400000) });
                    } else if (val === "30d") {
                      setConfig({ ...config, from_date: formatDateOnly(30 * 86400000) });
                    }
                  }}
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value="any">Any time (historical &amp; recent)</option>
                  <option value="24h">Past 24 hours</option>
                  <option value="7d">Past 7 days</option>
                  <option value="30d">Past 30 days</option>
                </select>
              </div>

              {/* Result Limit: Enforce <= 20 */}
              <div className="space-y-1.5">
                <label htmlFor="filter-limit" className="text-xs font-semibold text-foreground">
                  Maximum Results per Run
                </label>
                <select
                  id="filter-limit"
                  value={Math.min(20, config.result_limit || 20)}
                  onChange={(e) => {
                    pushHistory();
                    setConfig({ ...config, result_limit: Math.min(20, Number(e.target.value)) });
                  }}
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value={5}>5 conversations (quick scan)</option>
                  <option value={10}>10 conversations</option>
                  <option value={15}>15 conversations</option>
                  <option value={20}>20 conversations (standard maximum)</option>
                </select>
              </div>
            </div>

            {/* Minimum Relevance Score Slider */}
            <div className="space-y-2 pt-2 border-t border-border/70">
              <div className="flex items-center justify-between text-xs">
                <label htmlFor="filter-relevance" className="font-semibold text-foreground">
                  Minimum Relevance Score Threshold
                </label>
                <span className="font-bold text-primary tabular-nums">
                  {config.min_relevance}%
                </span>
              </div>
              <input
                id="filter-relevance"
                type="range"
                min={0}
                max={100}
                step={5}
                value={config.min_relevance}
                onChange={(e) => {
                  setConfig({ ...config, min_relevance: Number(e.target.value) });
                }}
                className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>0% (Broadest match)</span>
                <span>50% (Recommended)</span>
                <span>80% (Strict high intent only)</span>
              </div>
            </div>

            {/* Semantic Search Toggle */}
            <div className="flex items-center justify-between rounded-xl border border-border bg-background p-3 pt-3">
              <div className="space-y-0.5">
                <span className="text-xs font-semibold text-foreground block">
                  Semantic Vector Matching
                </span>
                <span className="text-[11px] text-muted-foreground block">
                  Find semantically related discussions even if exact keyword terms are omitted.
                </span>
              </div>
              <input
                type="checkbox"
                checked={Boolean(config.semantic)}
                onChange={(e) => {
                  pushHistory();
                  setConfig({ ...config, semantic: e.target.checked });
                }}
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
              />
            </div>
            {config.semantic&&<div className="space-y-2"><label className="block text-sm">Relevant offerings<textarea maxLength={500} value={config.offerings} onChange={e=>setConfig({...config,offerings:e.target.value})} className="control block w-full"/></label>{!!offerings.data?.items.length&&<label className="block text-xs">Use a workspace offering<select className="control block max-w-full" value="" onChange={e=>{if(e.target.value){pushHistory();setConfig({...config,offerings:e.target.value})}}}><option value="">Choose an offering</option>{offerings.data.items.map(x=><option key={x}>{x}</option>)}</select></label>}</div>}
          </details>
          {/* SECTION 5: Review & Run */}
          <section
            id="section-review"
            className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs scroll-mt-20"
          >
            <div className="border-b border-border/80 pb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                Section 5
              </span>
              <h2 className="text-base font-semibold text-foreground">Review &amp; Run</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Pre-flight check of all parameters before launching discovery.
              </p>
            </div>

            {/* Parameters Review Summary */}
            <div className="rounded-xl border border-border bg-background p-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 border-b border-border/70 pb-3">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                    Discovery Name
                  </span>
                  <span className="font-semibold text-foreground truncate block">
                    {name || "Untitled Discovery"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                    Target ICP
                  </span>
                  <span className="font-medium text-foreground truncate block">
                    {selectedIcpName || "All ICPs"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                    Keywords
                  </span>
                  <span className="font-medium text-foreground block">
                    {config.keywords.length} keywords active
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                    Sources
                  </span>
                  <span className="font-medium text-foreground block">
                    {(config.sources || []).length} sources selected
                  </span>
                </div>
              </div>

              {/* Preflight Validation Alert */}
              <div
                className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-medium ${
                  validation.isValid
                    ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-800 dark:text-amber-200 border border-amber-500/30"
                }`}
              >
                {validation.isValid ? (
                  <>
                    <CheckCircle2 size={15} className="shrink-0" />
                    <span>Criteria entered. Workspace and source permissions will be checked before starting.</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={15} className="shrink-0" />
                    <span>Configuration incomplete: {validation.issues.join(", ")}.</span>
                  </>
                )}
              </div>

              {/* Quota usage notice */}
              <p className="text-[11px] text-muted-foreground">
                Consumes 1 run against your monthly workspace discovery quota. Results will be saved to your Discovery History.
              </p>
            </div>
          </section>

          {/* Contained Sticky Action Bar (Strictly inside <main>) */}
          <div className="mt-6 rounded-xl border border-border bg-card/95 backdrop-blur-xs p-3.5 shadow-lg flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  validation.isValid ? "bg-emerald-500" : "bg-amber-500"
                }`}
              />
              <span className="text-muted-foreground font-medium">
                {validation.isValid ? "Ready for preflight" : "Setup incomplete"} ·{" "}
                <strong className="text-foreground">{config.keywords.length} keywords</strong>,{" "}
                <strong className="text-foreground">{(config.sources || []).length} sources</strong>
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/intent-radar/discover"
                className="inline-flex h-8 items-center px-3 rounded-lg border border-border bg-background text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                Cancel
              </Link>

              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSaveSearchName(name || (config.keywords.length ? `Search: ${config.keywords[0]}` : "New Search"));
                  setSaveModalOpen(true);
                }}
                className="h-8 text-xs font-medium cursor-pointer"
                disabled={!config.keywords.length}
              >
                Save Search
              </Button>

              <Button
                size="sm"
                onClick={() => void handleRunDiscovery()}
                disabled={!canWrite || running}
                className="h-8 text-xs gap-1.5 font-semibold cursor-pointer"
              >
                {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                <span>{running ? "Starting Run…" : "Run Discovery"}</span>
              </Button>
            </div>
          </div>
        </main>
      </div>

      {/* Save Search Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <h3 className="text-sm font-semibold text-foreground">Save as Reusable Search</h3>
              <button
                type="button"
                onClick={() => setSaveModalOpen(false)}
                className="text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Save this configuration so any team member can re-run it with one click or convert it to a scheduled monitor.
            </p>

            <div className="space-y-1.5">
              <label htmlFor="save-search-name" className="text-xs font-semibold text-foreground">
                Search Name
              </label>
              <input
                id="save-search-name"
                type="text"
                value={saveSearchName}
                onChange={(e) => setSaveSearchName(e.target.value)}
                placeholder="e.g. CRM Alternatives Search"
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSaveModalOpen(false)}
                disabled={savingSearch}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => void handleSaveSearch()}
                disabled={!saveSearchName.trim() || savingSearch}
              >
                {savingSearch ? <Loader2 size={13} className="animate-spin" /> : "Save Search"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Per-Source Configuration Drawer */}
      <SourceConfigDrawer
        sourceId={configuringSource}
        value={config}
        onChange={setConfig}
        onClose={() => setConfiguringSource(null)}
      />
    </div>
  );
}
