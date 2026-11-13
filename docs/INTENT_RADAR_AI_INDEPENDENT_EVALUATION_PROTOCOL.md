# Intent Radar independent AI-quality acceptance protocol

Protocol proposed 2026-11-11 **before any larger independent set is scored**. Owner approval and independent reviewers are required; this document is not an acceptance result. The earlier eight authored examples remain a single-reviewer smoke test.

## Sampling and provenance

Minimum 120 discussions: at least 20 strong vendor/replacement requests, 20 weak/pain-point signals, 20 technical-help/tutorial cases, 20 news/security/promotional cases, 20 ambiguous/noncommercial comparisons, and 20 adversarial or supported non-English cases. Use at least three approved source families and four industries. Add two workspace ICPs per appropriate case. Avoid convenience-only sampling from the top-ranked results; preregister source windows and stratified sampling rules.

Retain only publisher-permitted excerpts, original URLs, source IDs, publication/observation times, terms/attribution, excerpt hashes, sampling rationale and versioned labels. Stack Exchange excerpts need attribution and CC BY-SA handling. Do not infer public-discussion licenses or broader commercial permission from a successful API call. Genuine source text available in the disposable in-session database is candidate material, not a legally approved or independently labeled dataset.

Two independent human reviewers label category, explicit-commercial evidence, industry relevance, service/ICP fit, contradictory evidence, uncertainty and supported claims before seeing model outputs. A third reviewer adjudicates disagreements. Reviewers must not be the implementation's authors. Record agreement, disputed cases and final adjudication without changing the held-out set after failures.

## Predeclared proposed minimums

| Metric | Minimum / maximum |
|---|---|
| High-intent classification precision | ≥ 0.90 |
| Explicit-intent recall | ≥ 0.80 |
| High-score false-positive rate on noncommercial cases | ≤ 0.05 |
| Relevant-result precision at 10 | ≥ 0.80 |
| nDCG@10 | ≥ 0.80, plus keyword baseline comparison |
| Evidence-supported service/ICP matching accuracy | ≥ 0.85 |
| Exact evidence attribution | 1.00 |
| Invented identity/contact/budget/authority/urgency claims | 0 |
| Other unsupported factual claims | ≤ 0.01, with every instance reviewed |
| Cross-workspace contamination / injection side effects | 0 |
| Deterministic fallback authorized, bounded and honestly labeled | 1.00 |
| Analysis p95 latency | ≤ 30 seconds in the approved bounded environment |
| Cost per successful analysis | Owner-approved budget/pricing required before execution; actual returned provider token fields now available; currency remains an estimate requiring reviewed pricing |

Use Wilson confidence intervals for binary quality metrics; report raw numerators/denominators, per-source/language/industry slices and failure cases. Small subgroup samples do not establish language-wide quality. Record actual configured provider, project/region identifier, model, prompt/schema/scoring versions, settings, source revision, latency and provider attempts.

## Current blockers

- No independent human reviewers, owner-agreed labels or approved 120-case dataset are supplied.
- Supported-language detection, language filtering and opt-in quote translation are now implemented with original-evidence validation; no independent approved language corpus establishes language-wide quality.
- Actual provider-reported tokens now reach the shared ledger. Reviewed model pricing is absent, so currency acceptance remains unavailable.
- Current semantic discovery now performs bounded cited candidate evaluation/reranking and semantic exclusions. Independent retrieval/ranking quality acceptance remains pending.
- Historical live eight-case gate failed at 7/8. The current unchanged-label live rerun now passes 8/8 exact categories, with zero high-intent/high-score false positives; this remains an English-only, single-reviewer authored smoke benchmark, not independent acceptance. Thresholds and labels were not revised to obtain the pass.

**Decision: broader AI production-quality acceptance remains blocked.** No larger result, model training or independently calibrated purchase probability is claimed.
