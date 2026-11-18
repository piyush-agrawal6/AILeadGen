export interface HelpArticleLink {
  label: string;
  href: string;
}

export interface HelpArticle {
  id: string;
  category: string;
  title: string;
  summary: string;
  updatedAt: string;
  popular?: boolean;
  steps: { title: string; detail: string }[];
  troubleshooting: { symptom: string; resolution: string }[];
  settingsLinks: HelpArticleLink[];
  relatedIds: string[];
  aiPrompt: string;
}

export const HELP_CATEGORIES = [
  "Getting Started & Onboarding",
  "Discovering Conversations",
  "Intent Signals & Opportunities",
  "Monitoring & Alerts",
  "AI Assistant & Ideal Customers",
  "Research Sources & Integrations",
  "Developer API & MCP",
  "Billing, Trials & Subscriptions",
  "Team, Workspaces & Security",
  "Troubleshooting & Known Issues",
] as const;

export const HELP_ARTICLES: HelpArticle[] = [
  {
    id: "getting-started",
    category: "Getting Started & Onboarding",
    title: "Setting up your workspace & completing onboarding",
    summary:
      "Walk through the 5-step guided setup to configure your company profile, Ideal Customer Profiles, research preferences, and workspace plan.",
    updatedAt: "November 2026",
    popular: true,
    steps: [
      {
        title: "1. Enter your website or business summary",
        detail:
          "Start onboarding by providing your company website URL (or describing your business manually). PlaneByte extracts grounded public company details for your review without starting any automated scans.",
      },
      {
        title: "2. Confirm your Business Profile & offerings",
        detail:
          "Review your company description, positioning, target markets, and products/services. You can edit any field before saving.",
      },
      {
        title: "3. Define Ideal Customer Profiles (ICPs)",
        detail:
          "Approve or customize your ICP segments (industries, buyer roles, pain points, and buying signals). Your default ICP guides signal relevance scoring.",
      },
      {
        title: "4. Configure Research Setup & Plan Activation",
        detail:
          "Confirm your default research keywords and exclusions, then activate an eligible Starter Trial or monthly subscription for the workspace.",
      },
    ],
    troubleshooting: [
      {
        symptom: "My new workspace shows 'Activation required' or 'Setup required'",
        resolution:
          "Each workspace maintains separate billing, integrations, and onboarding progress. Creating a second workspace never inherits another workspace's paid plan or trial. Complete setup or activate a plan for that workspace.",
      },
      {
        symptom: "I skipped onboarding and want to resume later",
        resolution:
          "Click the compact Setup progress indicator near the bottom of the left sidebar (above Settings) to return directly to your saved step.",
      },
    ],
    settingsLinks: [
      { label: "Open Onboarding", href: "/onboarding" },
      { label: "Organization Profile", href: "/settings?category=company&tab=profile" },
      { label: "Manage Workspaces", href: "/settings/workspaces" },
    ],
    relatedIds: ["billing-subscriptions", "team-workspaces-security", "ai-assistant-icps"],
    aiPrompt: "Walk me through what remains to finish setting up my current workspace.",
  },
  {
    id: "discover-conversations",
    category: "Discovering Conversations",
    title: "Running discoveries, saved searches & Discovery History",
    summary:
      "Search permitted public conversations using AI-assisted prompts or Advanced Filters, save reusable queries, and review past runs.",
    updatedAt: "November 2026",
    popular: true,
    steps: [
      {
        title: "Choose AI Discovery or Advanced Filters",
        detail:
          "Describe what buyers are asking for in plain language, or open Advanced Filters to select specific sources, keywords, exclusions, date ranges, and minimum relevance.",
      },
      {
        title: "Select permitted public sources",
        detail:
          "Pick from enabled sources (Hacker News, Stack Exchange, GitHub, Bluesky, YouTube, Discourse, or Atom feeds). Source-specific filters appear in the configuration drawer.",
      },
      {
        title: "Save recurring searches & inspect history",
        detail:
          "Save high-performing queries to Saved Searches for one-click re-runs, and inspect past runs anytime in Discovery History without altering earlier snapshots.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Discovery returns a usage limit notice instead of results",
        resolution:
          "Check Settings → Billing & Usage to see whether your monthly search allowance or daily safety limit has been reached. Monthly limits reset at the start of the next billing period; daily safety limits reset at 00:00 UTC.",
      },
      {
        symptom: "AI analysis is unavailable during discovery",
        resolution:
          "Keyword-based discovery still runs even if AI operations are exhausted or disabled in Research Preferences → Discovery Defaults.",
      },
    ],
    settingsLinks: [
      { label: "Open Discover", href: "/intent-radar/discover" },
      { label: "Discovery Defaults", href: "/settings?category=preferences&tab=discovery" },
      { label: "Billing & Usage", href: "/settings?category=billing&tab=overview" },
    ],
    relatedIds: ["signals-opportunities", "sources-integrations", "monitors-alerts"],
    aiPrompt: "Why is my discovery search returning few results, and how can I improve my keywords?",
  },
  {
    id: "signals-opportunities",
    category: "Intent Signals & Opportunities",
    title: "Reviewing intent signals, evidence & qualifying opportunities",
    summary:
      "Evaluate collected public discussions, verify original source quotes, rate relevance, and promote qualified leads to Opportunities.",
    updatedAt: "November 2026",
    steps: [
      {
        title: "Inspect source evidence first",
        detail:
          "Click any signal to open its detail view, read the original excerpt, check the source link, and inspect why it matched your ICP. Relevance scores are analytical signals—always verify context before acting.",
      },
      {
        title: "Triage with statuses and feedback",
        detail:
          "Mark signals as Reviewed, Saved, Qualified, or Dismissed, and save important discussions into Research Library collections.",
      },
      {
        title: "Promote to an Opportunity",
        detail:
          "Convert qualified signals into Opportunities to assign priority (High/Medium/Low), record notes, and track next actions.",
      },
    ],
    troubleshooting: [
      {
        symptom: "An older signal now displays 'Source item unavailable'",
        resolution:
          "Public source excerpts automatically expire according to your Data Retention setting (or stricter publisher limits). Your workspace notes and opportunity records remain intact.",
      },
    ],
    settingsLinks: [
      { label: "Open Intent Signals", href: "/intent-radar/signals" },
      { label: "Open Opportunities", href: "/intent-radar/opportunities" },
      { label: "Data Retention", href: "/settings?category=preferences&tab=retention" },
    ],
    relatedIds: ["discover-conversations", "monitors-alerts"],
    aiPrompt: "Show my highest-intent signals from the last 7 days and recommend next steps.",
  },
  {
    id: "monitors-alerts",
    category: "Monitoring & Alerts",
    title: "Creating monitors, schedules & notification preferences",
    summary:
      "Automate recurring checks for high-value buying signals and customize in-app, email, quiet hours, and alert threshold settings.",
    updatedAt: "November 2026",
    popular: true,
    steps: [
      {
        title: "Create and activate a monitor",
        detail:
          "Navigate to Monitoring, define your keywords, sources, and ICP context, and set status to Active. Active monitors count toward your plan's active monitor limit.",
      },
      {
        title: "Configure a schedule",
        detail:
          "Choose a supported check cadence (minimum daily interval depending on plan) and display timezone. Pausing a monitor stops future checks while preserving collected evidence.",
      },
      {
        title: "Tune personal & workspace alerts",
        detail:
          "In Settings → Research Preferences → Notifications & Alerts, configure your personal in-app/email toggles, quiet hours, and workspace-wide high-relevance alert threshold.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Not receiving email alerts for new signals",
        resolution:
          "Verify Email notifications are enabled, cadence is set to Immediate, quiet hours are not active, and run 'Send Test Email' in Settings → Research Preferences → Notifications & Alerts.",
      },
    ],
    settingsLinks: [
      { label: "Open Monitoring", href: "/intent-radar/monitors" },
      { label: "Notifications & Alerts", href: "/settings?category=preferences&tab=notifications" },
    ],
    relatedIds: ["discover-conversations", "signals-opportunities"],
    aiPrompt: "How do I create an effective monitor for my current Ideal Customer Profile?",
  },
  {
    id: "ai-assistant-icps",
    category: "AI Assistant & Ideal Customers",
    title: "Using the AI Assistant & managing Ideal Customer Profiles",
    summary:
      "Leverage the workspace-aware PlaneByte AI Assistant for grounded analysis and maintain accurate Ideal Customer Profiles.",
    updatedAt: "November 2026",
    steps: [
      {
        title: "Maintain clear Ideal Customer Profiles",
        detail:
          "Open Intelligence → Ideal Customers to create, edit, or set your default ICP. Clear industries, buyer roles, pain points, and competitors improve both discovery and assistant answers.",
      },
      {
        title: "Ask grounded workspace questions",
        detail:
          "Open AI Assistant from the header sparkle icon (or Global Search → Ask AI). Factual workspace lookups use read tools with zero AI quota consumed.",
      },
      {
        title: "Review actions before execution",
        detail:
          "When the assistant proposes creating a monitor, ICP, or discovery, every write action requires your explicit approval before executing.",
      },
    ],
    troubleshooting: [
      {
        symptom: "AI Assistant switched to deterministic workspace data mode",
        resolution:
          "If your monthly AI operations or daily AI safety cap is reached, the assistant still answers factual questions directly from workspace data without consuming AI quota.",
      },
    ],
    settingsLinks: [
      { label: "Open AI Assistant", href: "/intelligence/assistant" },
      { label: "Open Ideal Customers", href: "/intent-radar/ideal-customers" },
      { label: "Capacity & Limits", href: "/settings?category=preferences&tab=limits" },
    ],
    relatedIds: ["getting-started", "billing-subscriptions"],
    aiPrompt: "Summarize my current Ideal Customer Profiles and highlight any gaps.",
  },
  {
    id: "sources-integrations",
    category: "Research Sources & Integrations",
    title: "Managing Research Sources, GitHub App & Custom Feeds",
    summary:
      "Connect GitHub repositories and webhooks, manage built-in public sources, understand AI processing policies, and configure Atom/Discourse feeds.",
    updatedAt: "November 2026",
    popular: true,
    steps: [
      {
        title: "Review Research Sources & AI Policies",
        detail:
          "Open Settings → Integrations & API → Research Sources. Click any source card to inspect connection health, rate limits, and whether AI processing is Authorized or Restricted.",
      },
      {
        title: "Connect GitHub for repository intelligence",
        detail:
          "Click the GitHub card to install the PlaneByte GitHub App, select permitted repositories, and verify webhook event health.",
      },
      {
        title: "Enable curated or custom feeds",
        detail:
          "Switch to the Custom Feeds tab to enable feeds from the Browse Feed Catalog or add an approved public Atom/Discourse feed URL.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Why is YouTube marked 'AI Restricted'?",
        resolution:
          "YouTube Data API v3 policy restricts sending YouTube metadata to generative AI models. PlaneByte enforces this strictly: YouTube results are display-only and excluded from AI prompts.",
      },
    ],
    settingsLinks: [
      { label: "Research Sources", href: "/settings?category=integrations&tab=sources" },
      { label: "Custom Feeds", href: "/settings?category=integrations&tab=feeds" },
      { label: "Sources Policy", href: "/sources-policy" },
    ],
    relatedIds: ["discover-conversations", "developer-api-mcp"],
    aiPrompt: "Which research sources are currently connected and AI-authorized in my workspace?",
  },
  {
    id: "developer-api-mcp",
    category: "Developer API & MCP",
    title: "Configuring Developer API keys & MCP server access",
    summary:
      "Issue scoped API keys for read-only REST endpoints and connect Claude, Cursor, or VS Code via the Model Context Protocol (MCP).",
    updatedAt: "November 2026",
    steps: [
      {
        title: "Issue a scoped API key",
        detail:
          "Owners and administrators can create keys in Settings → Integrations & API → MCP & Developer API. Copy the key immediately—it is displayed only once.",
      },
      {
        title: "Connect an MCP client",
        detail:
          "Use the MCP Setup tab to copy the ready-to-paste client configuration pointing to /api/v1/mcp with your Bearer token.",
      },
      {
        title: "Revoke or rotate anytime",
        detail:
          "Revoking a key takes effect immediately across both REST API and MCP requests. Every call verifies active workspace membership and plan API allowances.",
      },
    ],
    troubleshooting: [
      {
        symptom: "API or MCP requests return 403 or 429",
        resolution:
          "Confirm your plan includes Developer API requests in Settings → Billing & Usage, verify the key has not been revoked, and check that the workspace subscription is active.",
      },
    ],
    settingsLinks: [
      { label: "MCP & Developer API", href: "/settings?category=integrations&tab=developer" },
      { label: "Billing & Usage", href: "/settings?category=billing&tab=overview" },
    ],
    relatedIds: ["sources-integrations", "billing-subscriptions"],
    aiPrompt: "How do I configure the PlaneByte MCP server and check my Developer API allowance?",
  },
  {
    id: "billing-subscriptions",
    category: "Billing, Trials & Subscriptions",
    title: "Plans, Starter Trial, Creem billing & usage allowances",
    summary:
      "Understand monthly plan limits, Starter Trial rules, renewal cancellation, invoices, and how daily safety limits interact with monthly quotas.",
    updatedAt: "November 2026",
    popular: true,
    steps: [
      {
        title: "Review Current Plan & Usage",
        detail:
          "Open Settings → Billing & Usage to check your active plan, status, access period, next payment date, and four core monthly allowances (Searches, AI Operations, Active Monitors, Monthly Reports).",
      },
      {
        title: "Inspect Detailed Usage on demand",
        detail:
          "Expand Detailed Usage to inspect Reserved AI Tokens, Developer API Requests, Team Seats, Scheduled Checks, Provider-Reported AI Consumption, and Daily Safety Limits (UTC).",
      },
      {
        title: "Manage payment methods, switches, or cancellation",
        detail:
          "Use Manage Subscription to open the secure Creem billing portal for cards and invoices, or Change Plan to compare Starter ($59/mo), Growth ($149/mo), Scale ($379/mo), and Enterprise.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Why does a canceled trial still show active access?",
        resolution:
          "Canceling automatic renewal stops future charges while keeping your confirmed trial or billing period active until the Access Until date shown in Billing & Usage.",
      },
    ],
    settingsLinks: [
      { label: "Current Plan & Usage", href: "/settings?category=billing&tab=overview" },
      { label: "Compare Plans", href: "/settings?category=billing&tab=plans" },
      { label: "Cancellation Terms", href: "/cancellation" },
    ],
    relatedIds: ["getting-started", "team-workspaces-security"],
    aiPrompt: "What does my current plan include and how much monthly usage do I have remaining?",
  },
  {
    id: "team-workspaces-security",
    category: "Team, Workspaces & Security",
    title: "Managing team roles, invitations, domains & multi-workspace isolation",
    summary:
      "Invite teammates, manage Owner/Admin/Member/Viewer roles, verify company domains via DNS TXT, review audit logs, and switch between isolated workspaces.",
    updatedAt: "November 2026",
    steps: [
      {
        title: "Invite teammates & manage roles",
        detail:
          "Open Settings → Team & Access to invite teammates via company email, resend or revoke pending invites, change member roles (Owner only), or remove members while preserving last-owner protection.",
      },
      {
        title: "Verify business domains via DNS TXT",
        detail:
          "In Settings → Company & Targeting → Business Domains, add your domain, publish the generated _heysow-verify TXT record at your DNS provider, and click Verify.",
      },
      {
        title: "Review Audit Logs & switch workspaces safely",
        detail:
          "Owners and Admins can filter, inspect, and export workspace Audit Logs in Team & Access → Roles & Audit. Switching workspaces clears previous workspace caches so data never crosses tenants.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Domain verification fails right after adding the TXT record",
        resolution:
          "DNS propagation can take 5–30 minutes (occasionally longer depending on TTL). Confirm the record host is _heysow-verify.<yourdomain> and retry after the 30-second cooldown.",
      },
    ],
    settingsLinks: [
      { label: "Team & Access", href: "/settings?category=team&tab=members" },
      { label: "Roles & Audit Log", href: "/settings?category=team&tab=roles" },
      { label: "Business Domains", href: "/settings?category=company&tab=domains" },
      { label: "Manage Workspaces", href: "/settings/workspaces" },
    ],
    relatedIds: ["getting-started", "troubleshooting"],
    aiPrompt: "Explain workspace roles and what security controls are active in my workspace.",
  },
  {
    id: "troubleshooting",
    category: "Troubleshooting & Known Issues",
    title: "Resolving access restrictions, quota errors & sync issues",
    summary:
      "Quickly diagnose workspace access restrictions, monthly vs daily limits, email delivery checks, and workspace switching states.",
    updatedAt: "November 2026",
    steps: [
      {
        title: "Workspace access restricted or setup required",
        detail:
          "Confirm you have selected the intended workspace in the top header switcher. Newly created workspaces require completing onboarding and activating an independent plan before Intent Radar unlocks.",
      },
      {
        title: "Monthly allowance vs Daily safety limit",
        detail:
          "If a search or AI call is blocked, check both Settings → Billing & Usage (monthly plan limits) and Settings → Research Preferences → Capacity & Limits (daily UTC caps).",
      },
      {
        title: "Report an issue with safe diagnostics",
        detail:
          "Use the Contact Support button on this page to submit a bug report or billing question. Optional diagnostic metadata includes only app version, timestamp, and page path—never credentials or API keys.",
      },
    ],
    troubleshooting: [
      {
        symptom: "Subscription was paid in Creem but workspace still shows pending",
        resolution:
          "Open Settings → Billing & Usage and click Refresh Status to immediately synchronize confirmed provider state from Creem.",
      },
    ],
    settingsLinks: [
      { label: "Billing & Usage", href: "/settings?category=billing&tab=overview" },
      { label: "Manage Workspaces", href: "/settings/workspaces" },
      { label: "Capacity & Limits", href: "/settings?category=preferences&tab=limits" },
    ],
    relatedIds: ["getting-started", "billing-subscriptions", "sources-integrations"],
    aiPrompt: "Why might my workspace access or a search action be blocked right now?",
  },
];

export function searchHelpArticles(query: string): HelpArticle[] {
  const q = query.trim().toLowerCase();
  if (!q) return HELP_ARTICLES;
  const terms = q.split(/\s+/).filter(Boolean);
  return HELP_ARTICLES.map((article) => {
    const haystack = [
      article.title,
      article.category,
      article.summary,
      ...article.steps.map((s) => `${s.title} ${s.detail}`),
      ...article.troubleshooting.map((t) => `${t.symptom} ${t.resolution}`),
    ]
      .join(" ")
      .toLowerCase();
    let score = 0;
    if (article.title.toLowerCase().includes(q)) score += 60;
    if (article.category.toLowerCase().includes(q)) score += 30;
    for (const term of terms) {
      if (article.title.toLowerCase().includes(term)) score += 20;
      if (haystack.includes(term)) score += 10;
    }
    return { article, score };
  })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((entry) => entry.article);
}
