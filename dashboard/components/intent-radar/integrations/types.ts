import type { SourcePolicySummary } from "@/lib/intent-radar";

export type FeedFamily = "rss" | "discourse" | "atom";

export type FeedPolicyRecord = {
  ai_processing_authorized: boolean;
  ai_status: string;
  classification_mode: string;
  policy_locked: boolean;
  reason: string | null;
  retention_max_days: number;
};

export type FeedConfig = {
  id?: string;
  name: string;
  family: FeedFamily;
  endpoint: string;
  policy_reference: string;
  attribution: string;
  retention_days: number;
  polling_minutes: number;
  enabled: boolean;
  ai_processing_authorized?: boolean;
  content_kind?: string | null;
  policy?: FeedPolicyRecord;
};

export type FeedPreset = {
  preset_id: string;
  name: string;
  family: "discourse" | "atom";
  endpoint: string;
  policy_reference: string;
  attribution: string;
  content_kind?: string | null;
  ai_processing_authorized: boolean;
  host_approved: boolean;
  configured: boolean;
  enabled: boolean;
  policy?: FeedPolicyRecord;
};

export type ProviderTestResult = {
  ok: boolean;
  provider: string;
  http_status: number | null;
  latency_ms: number | null;
  checked_at: string;
  summary: string;
  quota_remaining?: number | null;
  policy?: SourcePolicySummary;
  error: string | null;
};

export type FeedTestResult = {
  ok: boolean;
  endpoint: string;
  http_status: number | null;
  latency_ms: number | null;
  checked_at: string;
  feed_format: string | null;
  entry_count: number;
  latest_entry_at: string | null;
  sample_titles: string[];
  etag: string | null;
  last_modified: string | null;
  policy?: FeedPolicyRecord;
  error: string | null;
};

export type GitHubStatus = {
  app_configured: boolean;
  oauth_configured: boolean;
  webhooks_configured: boolean;
  public_search_available: boolean;
  app_slug: string;
  status: string;
  installation_id: string | null;
  account_login: string | null;
  account_type: string | null;
  repositories: { id: number; full_name: string; private: boolean; selected: boolean }[];
  last_verified_at: string | null;
  last_error_code: string | null;
};

export type SourceHealthItem = {
  provider: string;
  name?: string;
  availability?: string;
  state: string;
  last_success: string | null;
  last_error?: { code: string; message?: string } | null;
  daily_requests_reserved?: number;
  daily_reservation_limit?: number;
  consecutive_failures?: number;
  stream_health?: {
    state: string;
    sequence: number;
    enabled: boolean;
    updated_at: string | null;
  };
};

export type FeedCategoryKey =
  | "community"
  | "releases"
  | "research"
  | "other";

export const FEED_CATEGORIES: { key: FeedCategoryKey; label: string; description: string }[] = [
  {
    key: "community",
    label: "Community Discussions",
    description: "Permitted public Discourse communities for product questions and workflows.",
  },
  {
    key: "releases",
    label: "Software Releases",
    description: "Official release Atom feeds classified as Market / Technology Intelligence.",
  },
  {
    key: "research",
    label: "Research & Publications",
    description: "Academic & technical Atom publications classified as Market / Technology Intelligence.",
  },
  {
    key: "other",
    label: "Developer Updates",
    description: "Additional permitted publication or developer channel Atom/RSS feeds.",
  },
];

export function categorizeFeed(feed: {
  family: string;
  name?: string;
  endpoint?: string;
  preset_id?: string;
  content_kind?: string | null;
}): FeedCategoryKey {
  if (feed.family === "discourse") return "community";
  const lower = `${feed.preset_id || ""} ${feed.name || ""} ${feed.endpoint || ""}`.toLowerCase();
  if (lower.includes("arxiv") || lower.includes("research")) return "research";
  if (
    lower.includes("release") ||
    lower.includes("github.com") ||
    feed.content_kind === "release_announcement"
  ) {
    return "releases";
  }
  return "other";
}

export function categorizePreset(preset: FeedPreset): FeedCategoryKey {
  return categorizeFeed(preset);
}

export function extractHostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export type SourceAvailabilityStatus =
  | "Connected"
  | "Available"
  | "No custom feeds"
  | "Setup required"
  | "Permission required"
  | "Disabled";

export type SourceOperationalHealth =
  | "Healthy"
  | "Degraded"
  | "Failed"
  | "Checking"
  | "Not yet checked";

export function deriveSourceAvailability(
  catalogState: string | undefined,
  ghStatus?: GitHubStatus | null,
  sourceId?: string,
  availabilityLabel?: string
): SourceAvailabilityStatus {
  if (sourceId === "github" && ghStatus?.status === "CONNECTED") return "Connected";
  if (availabilityLabel === "No custom feeds") return "No custom feeds";
  const s = (catalogState || "").toLowerCase();
  if (s === "connected") return "Connected";
  if (s === "available") return "Available";
  if (s.includes("not configured")) {
    return sourceId === "rss" ? "No custom feeds" : "Setup required";
  }
  if (s.includes("approval") || s.includes("permission")) return "Permission required";
  return "Disabled";
}

export function deriveOperationalHealth(item?: SourceHealthItem | null): SourceOperationalHealth {
  if (!item) return "Not yet checked";
  const fails = item.consecutive_failures ?? 0;
  const st = (item.state || "").toUpperCase();
  if (st === "RUNNING" || st === "CHECKING") return "Checking";
  if (st === "FAILED" || fails >= 3) return "Failed";
  if (fails > 0 || item.last_error?.code) return "Degraded";
  if ((st === "COMPLETE" || st === "NO_RESULTS" || st === "HEALTHY") && item.last_success) {
    return "Healthy";
  }
  return "Not yet checked";
}
