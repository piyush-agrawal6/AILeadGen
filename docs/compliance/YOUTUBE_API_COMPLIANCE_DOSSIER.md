# YouTube API Services Compliance Verification Dossier

**Product:** PlaneByte — Intent Radar (`https://app.planebyte.com`, `https://planebyte.com`)  
**Operator:** Planebyte, an individually operated business owned by Piyush Agrawal (`contact@planebyte.com`)  
**Date:** 2026-11-18  
**Policy Reference:** [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies)

## 1. Actual Implementation Scope (Verified from `app/intent_radar/youtube_source.py`)

- **Access Method:** Server-side **YouTube Data API v3 API key** stored in Google Cloud Secret Manager (`leadengine-youtube-api-key`).
- **OAuth Status:** PlaneByte does **NOT** request YouTube user OAuth scopes and does **NOT** access private YouTube accounts, private playlists, subscriptions, or watch history. (Google Sign-In, when used for PlaneByte login, requests identity claims only and is completely separate from YouTube API Services.)
- **Public Data Accessed:**
  - Public video search results (`/youtube/v3/search` with `safeSearch=strict`, `type=video` or `channel`).
  - Public video metadata & public statistics (`/youtube/v3/videos`, `part=snippet,contentDetails,statistics`).
  - Public comment threads (`/youtube/v3/commentThreads`, when enabled and public comments are allowed on the video).
- **Quotas & Rate Controls:** Bounded project daily limits and per-workspace fair-usage limits (`youtube_daily_search_limit`, `youtube_workspace_daily_search_limit`, `youtube_daily_unit_limit`) enforced server-side via `app/intent_radar/source_runtime.py`.
- **Caching & 30-Day Retention:** Short-lived API response cache (`intent_provider_cache`, TTL 600–900 seconds). Persisted YouTube signals carry a strict **30-day maximum retention** enforced by the worker retention sweep (`retention_days = 30`).
- **AI Analytics & Cross-Source Gate (HARD-GATED OFF):**
  - `INTENT_RADAR_YOUTUBE_AI_ANALYTICS_ENABLED=false` (default in `app/config/settings.py`)
  - `INTENT_RADAR_YOUTUBE_CROSS_SOURCE_ANALYTICS_ENABLED=false` (default in `app/config/settings.py`)
  - Neither derived AI sentiment/intent scoring nor cross-platform AI analytics run on YouTube API Data unless separate written/recorded YouTube API policy approval is obtained.

## 2. Published Mandatory Disclosures (Both `planebyte.com` & `app.planebyte.com`)

| Requirement | Where Published | Verified Links |
|---|---|---|
| Statement that app uses YouTube API Services | Privacy Policy, Terms of Service, Third-Party Sources Policy | `/privacy`, `/terms`, `/sources-policy` |
| Binding link to YouTube Terms of Service | Terms of Service, Privacy Policy, Third-Party Sources Policy | `https://www.youtube.com/t/terms` |
| Link to Google Privacy Policy | Privacy Policy, Third-Party Sources Policy | `https://policies.google.com/privacy` |
| Link to Google Security Settings | Privacy Policy, Data Deletion Policy, Third-Party Sources Policy | `https://security.google.com/settings/security/permissions` |
| Public API key vs non-OAuth clarification | Privacy Policy, Third-Party Sources Policy | Clarifies no private YouTube account access |
| 30-day refresh/deletion & user deletion workflow | Privacy Policy, Data Deletion Policy, Third-Party Sources Policy | `Settings -> Account -> Sign-in & Security` & `contact@planebyte.com` |
| Source attribution & original YouTube links | In-app signal cards & Third-Party Sources Policy | Direct `https://www.youtube.com/watch?v=...` attribution |

## 3. Owner Checklist Before Submitting Google API Compliance Form

- [ ] Capture live signed-in screenshots of YouTube discovery results in `https://app.planebyte.com` showing YouTube attribution and original `youtube.com/watch?v=...` links (never fabricate screenshots).
- [ ] Capture screenshots of `https://planebyte.com/privacy`, `https://planebyte.com/terms`, and `https://planebyte.com/sources-policy` displaying the YouTube Terms of Service and Google Privacy Policy links.
- [ ] Confirm `INTENT_RADAR_YOUTUBE_AI_ANALYTICS_ENABLED` remains `false` in Cloud Run production env vars until Google approves any derived analytics use case.
- [ ] If YouTube user OAuth is ever planned in a future release, perform a dedicated Google OAuth Verification & CASA/security review before enabling.
