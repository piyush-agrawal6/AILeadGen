# Independent review package and owner arrangements

The owner approved the existing 120-case protocol on November 13, 2026. Its
sampling requirements and quality thresholds are unchanged. No independent human
evaluation has passed. The implementation's authors cannot supply human labels.

Arrange **two independent reviewers and one distinct adjudicator**, all independent
of the implementation authors. Reviewers need experience interpreting B2B public
discussions, explicit commercial evidence, non-buying technical questions, and
customer-profile fit. Supported non-English cases require reviewers competent in
their original language; do not treat machine translation as independent evidence.
The adjudicator needs authority to resolve conflicting labels and inspect claim,
privacy, contamination and injection failures. The owner verifies reviewer identity
and provenance. No account credentials are needed by the offline workflow.

Each reviewer independently labels all 120 cases before seeing model predictions
or the other person's labels. Budget reviewer time after inspecting a pilot; no
unmeasured completion-time promise is made. The adjudicator reviews agreements
as well as disagreements and supplies a reason for each disputed resolution.

## Preparing the corpus

Use `scripts/prepare_intent_review.py prepare` with a candidate JSON (`cases` array),
preregistered configuration JSON, and a new restricted output directory. It performs
seeded sampling of up to 20 permitted cases in each of the protocol's six strata,
checks source windows, excludes repeated source text, strips model output, and
hashes the frozen package. It never fetches sources, calls AI or invents cases.

Configuration fields: `sampling_seed`, `source_windows` (approved family to UTC
`from`/exclusive `to`), `protocol_approved_at`, `implementation_authors`,
`reviewer_ids` (empty until two real people are assigned), `adjudicator_id`,
`reviewed_pricing_reference`, and `approved_cost_per_analysis`. Sources require
documented permissions and attribution. Supply existing actual approved ICPs with
each applicable case. Insufficient source, industry or stratum coverage is reported
as NOT_READY, never filled with fictional examples. Currently only Hacker News is
approved in production; full three-family sampling remains outstanding.

Give reviewers **only** `blind-cases.json` or CSV, `review-template.json`, and these
instructions. Keep the private manifest, sample strata, model results, and the other
reviewer's submission hidden. Files are created exclusively with restricted file
permissions; an existing frozen package or submission is never overwritten.

## Label definitions

- `category`: evidence-supported category from the current scoring taxonomy.
- `explicit_commercial`: a genuine explicit provider, replacement, comparison or
  purchasing request; technical curiosity or a pain point alone is insufficient.
- `relevance`: 0 irrelevant, 1 weak/contextual, 2 relevant, 3 strongly relevant.
- `industry` and `industry_relevant`: explicit evidence and fit, without guessing.
- `icp_fit`: each supplied profile ID mapped to SUPPORTED, UNSUPPORTED or UNCERTAIN.
- `commercial_evidence`, `contradictory_evidence`, `supported_claims`: exact original
  quotations, never paraphrases or facts inferred about the author.
- `uncertainty`: Low, Moderate or High; this is not a purchase probability.
- `rationale`: a specific explanation, including missing/contradictory context.

Use `validate-review` to check a submission. Each case must appear exactly once;
unknown/duplicate IDs, unassigned reviewers, unsupported quote text and missing ICPs
are rejected. Reviewers attest independence and blindness. This offline tool does
not authenticate those attestations; the owner must verify provenance.

Use `adjudication-queue` with the two locked submissions. It reports raw agreement
and disputed fields. Use `finalize` with the actual third reviewer ID, package hash,
`all_cases_reviewed: true`, owner-verified `provenance_verified: true`, and a
`resolutions` array containing every disputed ID, final `label` and specific `reason`.
Finalizing labels does **not** mark quality accepted.

## Scoring and error review

Only after labels are locked, run saved inference against the unchanged set. Record
real model/project/region and prompt/schema/scoring versions, attempt counts,
latencies and provider tokens. Do not run 120 paid calls without the existing quota
and cost authorization. Do not alter the held-out sample after observing failures.

The adjudicator supplies a separate post-inference assessment referencing the exact
prediction hash, with one record per case: unsupported/total reviewed claims,
invented sensitive claims, cross-workspace contamination, injection side effects,
and fallback authorization/bounds/honesty where used. Count all actual failures.
`score` combines this with saved predictions and finalized labels. It reports
precision/recall, confidence intervals, confusion, nDCG and keyword baseline,
precision@10, ICP accuracy, attribution, source/language/industry slices, human safety
counts, p95 latency, reviewed cost estimates and per-case error analysis. Missing
metrics fail closed. A score pass is separate from deployed end-to-end acceptance.
