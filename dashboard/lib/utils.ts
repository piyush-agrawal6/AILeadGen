import { clsx,type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num);
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return dateStr;
  }
}

export function formatDuration(seconds?: number | null): string {
  if (seconds === undefined || seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

export function getTierBadgeClass(tier: string): string {
  switch (tier) {
    case "A+":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    case "A":
      return "bg-sky-500/10 text-sky-400 border-sky-500/30";
    case "B":
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    case "C":
      return "bg-orange-500/10 text-orange-400 border-orange-500/30";
    default:
      return "bg-slate-500/10 text-slate-400 border-slate-500/30";
  }
}

export function getStatusBadgeClass(status: string): string {
  switch (status.toUpperCase()) {
    case "COMPLETED":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    case "RUNNING":
      return "bg-sky-500/10 text-sky-400 border-sky-500/30 animate-pulse";
    case "QUEUED":
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    case "FAILED":
      return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    case "CANCELLED":
      return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    default:
      return "bg-slate-500/10 text-slate-400 border-slate-500/30";
  }
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-sky-400";
  if (score >= 40) return "text-amber-400";
  return "text-slate-400";
}
