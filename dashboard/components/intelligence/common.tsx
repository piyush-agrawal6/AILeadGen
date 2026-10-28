import Link from "next/link";
import { scoreTone, STATUS_STYLES } from "@/lib/lead-display";
import { label, type LeadStatus } from "@/lib/intelligence";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">{eyebrow || "PlaneByte / Intelligence"}</p><h1 className="text-2xl font-semibold tracking-tight">{title}</h1><p className="mt-2 text-sm text-muted-foreground">{description}</p></div>{action}</div>;
}
export function Loading({ rows = 5 }: { rows?: number }) { return <div aria-label="Loading workspace" className="space-y-3 animate-pulse">{Array.from({ length: rows }, (_, i) => <div key={i} className="h-12 rounded bg-muted/60" />)}</div>; }
export function ErrorState({ error, retry }: { error: unknown; retry: () => void }) { return <div role="alert" className="rounded-md border border-destructive/30 p-5"><p className="font-medium">We couldn’t load this workspace.</p><p className="my-2 text-sm text-muted-foreground">{error instanceof Error ? error.message : "Please try again."}</p><Button variant="outline" onClick={retry}><RefreshCw className="mr-2 h-3 w-3"/>Try again</Button></div>; }
export function Empty({ title, detail, href, action }: { title: string; detail: string; href?: string; action?: string }) { return <div className="grid min-h-48 place-content-center border-y py-12 text-center"><p className="font-medium">{title}</p><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{detail}</p>{href && <Link className="mt-5 text-sm font-medium text-primary" href={href}>{action || "Start a scan"} <ArrowUpRight className="inline h-3 w-3"/></Link>}</div>; }
export function Score({ value, compact = false }: { value?: number | null; compact?: boolean }) { return <span title={value == null ? "Not assessed with available evidence" : "Higher means stronger sales opportunity, not better website quality"} className={`${compact ? "score-chip" : "score-value"} ${scoreTone(value)}`}>{value ?? "—"}{!compact && value != null && <span className="ml-1 text-xs font-normal opacity-60">/100</span>}</span>; }
export function State({ value }: { value: string }) { const style=STATUS_STYLES[value as LeadStatus];return <span className={"status-pill "+(style||(["RUNNING","COMPLETED"].includes(value)?"status-shortlisted":value==="FAILED"?"status-danger":"status-muted"))}><span className="status-dot"/>{label(value)}</span>; }
