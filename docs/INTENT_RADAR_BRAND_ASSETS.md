# Intent Radar marketplace: assets and capability evidence

Research date: 2026-11-10. This document records the local marketplace implementation,
not production acceptance or third-party client connection certification.

## Locally bundled official artwork

| Asset | Official source | Rights basis and usage |
|---|---|---|
| `dashboard/public/integrations/hacker-news.svg` | [YC press page](https://www.ycombinator.com/press), official inline 48×48 Y artwork | Decoded from the official page's SVG data URI without changing the paths or colors. The simple Y-on-orange mark has a [PD-textlogo / threshold-of-originality record](https://commons.wikimedia.org/wiki/File:Y_Combinator_logo.svg). This is a copyright-status basis, **not an express YC trademark license**. YC retains trademark rights. Used only to identify the genuine HN public API source, never as PlaneByte branding or an endorsement. [HN FAQ](https://news.ycombinator.com/newsfaq.html) confirms YC owns HN. |
| `dashboard/public/integrations/vscode.png` | [Microsoft's official stable blue icon](https://code.visualstudio.com/assets/branding/code-stable.png) linked from [icon usage guidelines](https://code.visualstudio.com/brand) | Official guidelines permit the icon in documentation/tutorials about Visual Studio Code and as a link to its website. The marketplace icon links directly to `https://code.visualstudio.com`; the dialog provides descriptive setup documentation. Unaltered, proportional, no icon/name lock-up, no new background or color effects; the card reserves clear space. Visual Studio Code and its icon are trademarks of Microsoft Corporation. |

The [Microsoft vscode-icons repository LICENSE](https://github.com/microsoft/vscode-icons/blob/main/LICENSE)
is CC BY 4.0, but its UI glyph license was **not** assumed to license the separate
product logo. The downloaded product PNG uses the official brand-page permission
above. There is no unsupported claim that it is CC-licensed.

All images are served from fixed `/integrations/` paths through `ProviderLogo`.
No hotlinks, provider-string URL construction, remote SVG execution or client
credential generation is involved. SVG artwork has no scripts, external refs or
embedded HTML. Provider names without approved artwork use the existing Lucide
`Blocks` glyph with a neutral accessible label; it is not a reconstructed logo.

## Research and neutral fallback decisions

- **Google Sheets:** [Google trademark list](https://about.google/brand-resource-center/logos-list/)
  and [Google trademark guidelines](https://partnermarketinghub.withgoogle.com/brands/google/trademarks-and-terms/)
  reviewed. [Drive API branding permission](https://developers.google.com/workspace/drive/api/guides/branding)
  specifically concerns Drive and actual Drive actions/storage; it does not
  establish Sheets artwork permission for a planned Intent Radar export. Use a
  neutral glyph. Sheets trademark belongs to Google.
- **ChatGPT / OpenAI:** [official design guidelines](https://openai.com/brand/)
  reviewed. These grant limited guideline-compliant use directly related to OpenAI
  services, reserve review/revocation, and prohibit implied endorsement. A validated
  ChatGPT service integration is absent, so a neutral glyph is used rather than
  overstating a relationship. No OpenAI asset was downloaded.
- **Claude / Anthropic:** the candidate official `/brand` URL returned 404; no
  verifiable artwork license for this context was established. Neutral glyph.
- **Cursor:** [official brand resources](https://cursor.com/brand) provide assets
  for accurate representation, but no explicit license for this marketplace
  context was established. Neutral glyph rather than inferring rights from public
  download availability. [MCP docs](https://cursor.com/docs/context/mcp) support
  Streamable HTTP and Authorization header interpolation; client setup still
  needs an actual verification call.
- **HubSpot, Pipedrive, Slack, Zapier:** clearly Planned workflow candidates,
  rendered with neutral glyphs. No logo permission is asserted, no artwork was
  downloaded, and no connection or delivery capability is represented.

Brand names identify third-party products. Their owners retain trademark rights.
Future artwork additions need a source and a permission basis specific to the
actual usage, not merely a public image URL or a third-party icon library license.

## Implemented behavior and truthful status

- Five keyboard-accessible Radix category tabs, category search, responsive cards,
  meaningful details/setup dialogs, source loading/error/empty states, shared
  Developer access and Intent Radar workflow navigation.
- **Live Data Sources:** populated from `useRadarCapabilities()` rather than a
  fabricated provider list. `app/intent_radar/providers.py` currently catalogs only
  Hacker News, state `Available`. The official v0 API checks up to 20 recent Ask HN
  stories, with at most 22 requests per check. Matching is local. No historical
  full-text search, comment-tree ingestion, author profiles or target-page scans.
  `Available` is source adapter availability, not a connected customer account.
- **Shared MCP:** `app/developer/mcp_server.py` implements Streamable HTTP tools;
  `app/api/server.py` mounts the SDK app at `/api/v1`, yielding `/api/v1/mcp`.
  Shared `/api/organization/developer/status` provides `enabled`, `can_manage`
  and `mcp_available`. Its read uses the existing request service, a verified
  active workspace query key, an abort signal, no automatic retry, and runs only
  after workspace and Radar capabilities resolve. The UI reports shared gate
  state, never a verified client connection.
- **Visual Studio Code and Cursor:** manual setup review for the implemented MCP
  server, not connected-client badges or one-click installation. Official client
  docs are linked. No vendor-specific end-to-end acceptance is claimed.
- **ChatGPT and Claude:** Planned; compatible authentication and tool discovery
  are unverified. No invented OAuth endpoint, callback or Connect action.
- **Google Sheets, HubSpot, Pipedrive, Zapier, Slack:** Planned. Shared Sheets or
  webhook infrastructure does not prove an Intent Radar export/event contract.
- **Workspace notifications:** existing in-app Intent Radar alert records and
  read/unread workflow. No email/Slack delivery or scheduling guarantee is implied.

### MCP authorization and contracts

**AI Client → Authenticated MCP → Intent Radar → Authorized Signals**.

Verified implemented tool names:

1. `search_intent_signals`
2. `list_intent_monitors`
3. `get_intent_signal`
4. `list_intent_opportunities`

These read stored workspace-owned evidence. They do not start checks, send
messages, create contacts or write intent records. Tools are registered only when
the Radar stage is not Disabled; individual reads still check access.

`app/developer/keys.py` and `app/intent_radar/permissions.py` enforce developer/MCP
gates, `mcp:use` plus `intent:read`, credential hash verification, expiry/revocation,
active issuing-member membership, fixed workspace context, completed onboarding,
Lead Engine availability (the existing shared-key prerequisite), Intent Radar
product access and internal-preview workspace restrictions. Source identifiers
and data remain authorized server-side. The marketplace changes none of this.

Setup only links to `/settings/developer`, the actual owner/admin key-management
UI. That shared UI issues the one-time server-generated credential and supports
rotation/revocation. The marketplace neither requests nor renders keys. The backend
endpoint path is verified in code; the public deployed API origin, gateway
reachability and named client authentication must be administrator-confirmed.

## Handoff and verification

Owned files are only the new marketplace component, its stylesheet, logo helper,
local integration assets and this document. The shared-page owner must re-export
`IntegrationsPage` from `./integrations` in `workspace-pages.tsx`. The marketplace
uses the existing PageHeading props; adding its optional `badge` prop belongs to
the shared UI owner. No global tokens/layout changes or browser server are needed.

Run ESLint on `components/intent-radar/integrations.tsx` and
`components/intent-radar/provider-logo.tsx` from `dashboard/`. Full route/browser
acceptance remains a shared-page handoff task. Planned provider contracts,
customer authentication and named MCP client verification remain outstanding.
