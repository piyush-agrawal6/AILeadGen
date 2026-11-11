# Intent Radar Phase 3 implementation and AI verification

## Independent product audit follow-up — 2026-11-11

The prior bounded implementation/evaluation evidence below is preserved, not a
complete Phase 3 customer acceptance claim. See the detailed 510-criterion audit
and final readiness report. General semantic retrieval/reranking/exclusions,
dedicated full grounded summaries, primary list feedback-ranking, full workspace
ICP factors and multilingual processing remain incomplete. Quote/summary claims
are real AI interpretation, but do not satisfy the entire required summary
workflow. Feedback changes analysis/drafts, not the primary list ordering.

New safeguards fence draft cache persistence after membership/ICP changes and
analysis after monitor edits; cache identity includes Vertex project/location and
prompt; client feedback scoring refreshes. Current genuine Vertex eight-case
smoke run **FAILED exact-category acceptance, 7/8**, despite zero high-intent
false positives. Historical 8/8 is not silently reused or substituted. Independent
larger quality/cost/language acceptance remains open. **Production NO-GO.**

### Preserved prior report

Verified locally on 2026-11-11. **Local implementation passes the bounded acceptance
checks; broader adjudicated AI quality and release activation remain pending.**

| Completed feature | Actual implementation/evidence |
|---|---|
| Existing Vertex integration | `app/intent_radar/ai.py` and `intelligence.py` reuse the shared acquisition gateway/router. Live evaluation and browser draft/analysis returned `VERTEX_AI`, configured `gemini-3.6-flash`, HTTP 200. No new provider or credentials. |
| Editable query generation/refinement | Structured inert drafts include available source capabilities, approved feed IDs, existing ICP and customer-reviewed company context. Previous editable criteria survive fallback. Review does not save, discover, schedule or send. Unit and live browser checks pass. |
| Semantic relevance | Explicit semantic candidate opt-in can retain non-keyword requests; this is candidate collection, not verified matching. Structured claims require an exact permitted target and exact source quote. Curated paraphrase/service-alignment evaluation passes; unavailable/malformed output is rejected. |
| Intent classification | Structured versioned taxonomy distinguishes service/recommendation/comparison/alternative requests, pain, research/help, general discussion and insufficient evidence. Budget/time claims require explicit wording. Unsupported citations cannot return or persist. |
| Selected existing ICP | Ownership and revision rechecked, exclusions honored, problem/service alignment separated from unknown company/role/market attributes. Inferred fit receives reduced weight and mandatory review. Selected/foreign/revised ICP and exclusion checks pass. |
| Scoring | `INTENT_SCORE_V2` dimensions are explained heuristic rankings, never buying probabilities. General/insufficient output cannot inherit a keyword intent bonus. Feedback is bounded; inferred ICP fit is explicitly uncertain. |
| Summaries | Structured `summary` claims must quote original title/excerpt. Genuine HN analysis produced a quoted summary of a macOS security-feature concern, classified General discussion, expressed need 0 and final score 40 (including +5 feedback). |
| Cache, budgets and availability | Workspace/input/model/ICP-sensitive validated caches, committed call/token reservations, shared usage ledger, timeouts and deterministic/manual fallback. PostgreSQL cache/budget checks pass. Actual provider token billing is not exposed by the gateway. |
| Customer controls and feedback | Owned preferences/default ICP, AI assistance opt-out, call/token ceilings, reversible active feedback and review notes. Real browser feedback and synthetic/real database authorization checks pass. Feedback adjusts ranking; it does not train a model. |

## Documented quality evaluation

Commands:

```sh
.venv/bin/python scripts/evaluate_intent_radar_ai.py --live
.venv/bin/python scripts/evaluate_intent_radar_ai.py --replay data/artifacts/verification/intent-radar23-ai-quality-initial.json
```

The first command made **one successful Vertex request**. EVAL_V3 replays those
unchanged live labels through the current evidence validator and production scorer,
avoiding an unnecessary second paid inference. It also rejects incomplete intent
citations and makes exact category correctness part of the gate.

- Eight authored English examples; one engineering reviewer; no independent adjudication.
- Category accuracy, exact evidence attribution, explicit-intent precision/recall
  and problem/service alignment accuracy: **8/8, 100%** where applicable.
- **Zero false-positive high-intent classifications. Zero negative examples ≥75.**
- Scores: recommendation 80; service request 80; unrelated product comparison 45;
  relevant alternative 90; explicitly non-buying pain 35; tutorial 15; geography
  discussion 15; prompt injection 15.
- Deterministic baseline explicit recall: 75%; exact target-string alignment: 75%.

The score replay constructs validated interpretations from the live evaluation's
labels/alignment judgments; it is not eight independent full production analysis
requests. The genuine browser analysis is separate evidence. This sample does not
establish calibrated buyer-intent scores, production accuracy, multilingual quality
or verified buyer identity. See [pending gates](INTENT_RADAR_PHASE_2_3_PENDING.md).
