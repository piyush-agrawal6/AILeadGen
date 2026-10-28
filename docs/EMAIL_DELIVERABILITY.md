# PlaneByte domain email verification

DNS is never changed automatically by LeadEngine. In Hostinger's verified mailbox/domain panel, inspect the actual sending-domain authentication instructions for planebyte.com and compare them with authoritative DNS.

Read-only verification during Phase 4 on 27 October 2026 found SPF `v=spf1 include:_spf.mail.hostinger.com ~all` and DMARC `v=DMARC1; p=none`. DKIM remains unknown pending the actual selector from the provider panel; no selector or key was guessed. No DNS changes were made.

- SPF: verify the existing TXT policy includes the authorized sending service. Keep one SPF policy; review the provider's current exact instructions before editing an existing policy.
- DKIM: obtain the real selector and public key from the mailbox provider. Query that selector under `_domainkey.planebyte.com` and compare it exactly. No selector or key is guessed by the application.
- DMARC: query `_dmarc.planebyte.com` and review the existing policy and reporting destinations with the domain owner. Do not silently create or tighten a policy.

Use provider diagnostics and inspect the authentication headers of a controlled test reply. Report authentication configuration as configured, missing or unknown. SMTP authentication and SPF/DKIM/DMARC configuration do not establish delivery to an inbox or perfect deliverability.

The app does not use tracking pixels, rewrite links through trackers, guess recipient addresses or send bulk campaigns. A suppression record persists at canonical prospect level. Email source, public source URL and discovery/country data remain in the existing intelligence/contacts records. Confirm the appropriateness of each real outreach message manually.

Automatic reply promotion requires known RFC Message-ID references, the expected peer address, the configured recipient mailbox, a plausible message time and aligned DKIM/DMARC success reported by a trusted receiving-provider Authentication-Results header. A structurally matched but unverified message can be retained for manual review but cannot automatically change sales status or increment verified-reply counts. No claim of independent cryptographic message verification is made.
