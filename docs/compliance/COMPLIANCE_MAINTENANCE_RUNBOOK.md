# PlaneByte Compliance Maintenance Runbook

**Policy Version:** `planebyte-compliance-2026-11-18-v4`  
**Registry File:** `docs/compliance/COMPLIANCE_REGISTRY.json`  
**Automated Check:** `scripts/verify_compliance_invariants.py` and `tests/unit/test_compliance_invariants.py`

## 1. Mandatory Pre-Launch Review Triggers

Before merging or enabling ANY of the following changes in production, complete the review checklist below:

1. **New third-party research source or connector** (e.g., Reddit, X, LinkedIn, new RSS/Discourse domain, or new GitHub/YouTube scope).
2. **New AI provider, model, or AI analytics flag** (especially enabling `INTENT_RADAR_YOUTUBE_AI_ANALYTICS_ENABLED` or `INTENT_RADAR_YOUTUBE_CROSS_SOURCE_ANALYTICS_ENABLED`).
3. **New infrastructure subprocessor, analytics tool, cookie, or third-party embed**.
4. **Pricing, trial duration, refund window, or payment provider changes**.
5. **Expansion into new regulated jurisdictions or launch of outreach/email-sending modules (e.g., Lead Engine)**.

## 2. Review Checklist

- [ ] **Data Collected**: Document exact fields, personal data categories, and whether data is customer-supplied or publicly sourced.
- [ ] **Lawful Purpose & Basis**: Map purpose and applicable legal basis (contract, consent, legitimate interests, legal obligation).
- [ ] **Platform Permissions & Terms**: Confirm official API access, rate limits, attribution/license rules (e.g., CC BY-SA, YouTube API Services Policies), and commercial AI processing rights. Never assume public visibility grants unrestricted AI rights.
- [ ] **Retention & Deletion**: Configure server-side retention TTLs, deletion propagation (e.g., Jetstream deletes, 30-day YouTube sweep), and user revocation/disconnect paths.
- [ ] **Security & Isolation**: Verify workspace scoping, server-side secret storage (GCP Secret Manager), encryption in transit/at rest, and privacy-safe logging.
- [ ] **Consent & Cookie Impact**: If any browser cookie or third-party script is added, update `/cookies` and wire real consent gating before deployment.
- [ ] **Policy & Registry Updates**: Update `docs/compliance/COMPLIANCE_REGISTRY.json`, `dashboard/lib/legal-policies.json`, and `planebyte-website-new/src/markup/*` together so both domains remain 100% consistent.
- [ ] **Automated Gate**: Run `python scripts/verify_compliance_invariants.py` and `pytest tests/unit/test_compliance_invariants.py` and `cd planebyte-website-new && npm test`.
- [ ] **Owner / Counsel Sign-Off**: Material legal-policy changes or new billing terms require explicit owner approval (and qualified legal counsel review where applicable) before production release.

## 3. Version History

| Version | Date | Summary |
|---|---|---|
| `planebyte-creem-global-2026-11-17-v3` | 2026-11-17 | Creem Merchant of Record alignment and Odisha individual operator disclosure on `app.planebyte.com`. |
| `planebyte-compliance-2026-11-18-v4` | 2026-11-18 | Full 11-document legal & compliance package synchronized across `planebyte.com` and `app.planebyte.com`, YouTube API Services mandatory disclosures, GitHub/Bluesky/Stack Exchange/HN/Discourse/RSS disclosures, real Cal.com cookie consent gating, privacy request history UI, compliance registry, and automated drift checks. |
