export type FeedFamily = "rss" | "discourse" | "atom";

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
    label: "Research & Technology",
    description: "Academic & technical Atom publications classified as Market / Technology Intelligence.",
  },
  {
    key: "other",
    label: "Other Verified Feeds",
    description: "Additional permitted publication or developer channel Atom/RSS feeds.",
  },
];

export function categorizePreset(preset: FeedPreset): FeedCategoryKey {
  if (preset.family === "discourse") return "community";
  const lower = `${preset.preset_id} ${preset.name} ${preset.endpoint}`.toLowerCase();
  if (lower.includes("arxiv") || lower.includes("research")) return "research";
  if (
    lower.includes("release") ||
    lower.includes("github.com") ||
    preset.content_kind === "release_announcement"
  ) {
    return "releases";
  }
  return "other";
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
  sourceId?: string
): SourceAvailabilityStatus {
  if (sourceId === "github" && ghStatus?.status === "CONNECTED") return "Connected";
  const s = (catalogState || "").toLowerCase();
  if (s === "connected") return "Connected";
  if (s === "available") return "Available";
  if (s.includes("not configured")) return "Setup required";
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
