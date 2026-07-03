# Contract — graded-decision flow (domain → API → frontend feedback)

> Read-only scan for the "professional-teacher-rework" roadmap. Key files: `backend/app/domain/evaluation.py`,
> `grading.py`, `postflop.py`, `providers/{heuristic,composite,base}.py`, `content/preflop/*.json`,
> `backend/app/api/v1/drill.py`, `frontend/src/components/{FeedbackPanel,RationaleTags,QuizPanel}.tsx`.

## Data-already-present (surface for (near-)free)

- **`EvaluationResult`** (`evaluation.py:48-61`) — every grader fully populates `per_action` (freq+EV each),
  `best_action`, `chosen_eval` (freq/EV of the action the user picked), `ev_loss_bb`, `correctness`
  (OPTIMAL/ACCEPTABLE/MISTAKE/BLUNDER), `rationale_tags: list[str]`, `explanation: str`, `provider`,
  `leak_category`, `coverage`, `is_mixed`. `solver_node_key` is a **dead field** (never assigned, Phase-3 reserved).
- **Already on the wire, nothing dropped:** `POST /drill/grade` returns `EvaluationResult` directly as the response
  model (`drill.py:213,217`; domain models reused as DTOs — `schemas/drill.py`). FE already renders `explanation` +
  `rationale_tags` (`FeedbackPanel.tsx:44-45` via `RationaleTags.tsx`, tag→phrase dict `:15-51`).
- **`chosen_eval` is delivered but NEVER rendered** in FeedbackPanel — free tier-2 material ("you played raise 12%,
  −1.4bb") sitting unused.
- **Postflop tags are 4-wide + rich:** `[node_tag, adv, cat, wetness]` e.g. `["cbet","hero","draw","wet"]` (6 sites in
  `postflop.py`). `RationaleTags.tsx:6-10` already self-documents that preflop tags are "thin by design."
- **12 genuinely authored exploit rationales** in `content/preflop/exploit.json` (real prose, not tautology, e.g.
  *"A station won't fold and rarely raises — isolate wider for value and cut bluffs."*). Read+appended to `explanation`
  ONLY for exploit spots by `heuristic.py::_enrich_exploit` (`:49-60`).
- **`leak_category`** (`domain/leaks.py:18-47`, namespaced 100-399, `TAXONOMY_VERSION=2`) = closest thing to a
  concept-id already in the system. `SRSItemRow` stores archetype identity = natural "this concept keeps coming up" key.

## Data-missing (real new work — the PRD's "surface for free" is over-optimistic)

- **Tautological baseline "why" is real + pervasive:** `grading.py:196` `"{hand} from {pos}: {top} is the play."`;
  `:219,:222-224` same shape. Postflop richer but still 100% f-string template (`postflop.py:292-301`) — **no
  mechanism-level reasoning** (no blockers / protection / range-freezing).
- **Every non-exploit content pack has ZERO authored rationale** — `rfi/vs_rfi/vs_3bet/vs_4bet/vs_limpers/blind_defense`
  have no `rationale` field (all 12 repo-wide live only in `exploit.json`). Baseline preflop = ~85% of reps, no prose.
- **Postflop graders never read `Entry.rationale`** — `grade_cbet/grade_vs_cbet/grade_vs_check_raise` take range
  strings, not `Entry`; no content-pack path into postflop explanations at all.
- **`explanation` is ONE flat string, not tiered** — verdict→reasoning→deep-dive needs a **new structured field**
  emitted by the grader, not fragile parsing of one prose slot.
- **`DrillAttempt` persists no rationale/tags/explanation** (`db/models.py:22-36`) — a "why did I miss this 3 days ago"
  deep-dive can only **re-derive from the archetype signature** (lossy by design — signature excludes hole cards/bet
  sizes; SRS review already reconstructs a NEW spot + re-grades live, `drill.py:91-170`).
- **`leak_category` too coarse to key a card 1:1** — e.g. `VS_RFI=112` covers call/3bet/fold together
  (`leaks.py:26-28`); the disambiguating signal lives in `rationale_tags`. No leak→card mapping exists anywhere.
- **QuizResult has no `rationale_tags`** (`schemas/drill.py:45-53`) — foundational-quiz feedback needs its own path.

## Integration points / blast radius

1. `drill.py:213-237 grade_drill` — builds `DrillAttempt` from `.correctness/.leak_category/.ev_loss_bb/.provider`;
   returns full result unchanged.
2. `services/review.py::record_attempt` — consumes only `correctness`+`leak_category` for SM-2. Untouched by rationale.
3. `services/stats.py` — aggregates `correctness/ev_loss_bb/leak_category/hand_class`; never touches rationale.
4. `providers/composite.py::_not_found` synthesizes `explanation="No content for this spot."` + empty tags — **tiered UI
   must handle the thin/empty case gracefully.**
5. `providers/heuristic.py::_enrich_exploit` is the ONLY post-construction mutator of tags/explanation — a new
   enrichment layer must not double-append.
6. `providers/base.py StrategyProvider` Protocol — **rationale is authored per-provider, NOT cross-cutting.** Enriching
   only HeuristicProvider/grading/postflop will NOT reach a future solver/hybrid unless a **shared post-processing
   wrapper** authors it. (Design the teaching enrichment as that shared seam — aligns with "seams not machinery.")
7. **Locked string-assert tests** — `test_grading.py:43,204,225-237` (`"over_fold"`/`"exploit"` in tags,
   `"station"` in explanation), `test_exploits.py:36-38` (every exploit Entry has `.rationale`). Reword deliberately.
8. `test_domain_purity.py` — new enrichment in `app.domain.*` must stay free of fastapi/sqlmodel imports; a DB-backed
   leak→card map belongs in `app/db`+`app/services`; card **content** = versioned JSON under `content/` (ContentPack pattern).

## Risks

- **`rationale_tags` is an untyped `list[str]` with positionally-meaningful but unenforced order** (postflop always
  `[node,adv,cat,wetness]`). Any reorder silently breaks future card logic that indexes it + no single tag-vocabulary source.
- **FE types hand-maintained + already drifted** — `types.ts:1-2` claims openapi-generated, but `schema.d.ts` doesn't
  exist; `EvaluationResult.solver_node_key` is missing from the FE interface. `verify.sh:36-38,72-73` only checks paths
  exist, not schema equality. **No CI gate.** Any new teaching field needs a manual, unenforced `types.ts` edit.
- **No persisted rationale → no true replay** of a past miss (see above).
- **Exploit-only rationale is narrow** (12 preflop entries) — treating "surface existing" as satisfying R1/R2 covers a
  small slice; the bulk is new authored content for baseline preflop + all postflop.
- **Solver won't inherit per-provider rationale** — Phase-3 provider needs its own path or the shared wrapper.
