# Tickets — Phase 2e-1: Facing a Flop Check-Raise

Spec: `docs/ai-dlc/specs/phase-2e-1-facing-check-raise.md`. 7 tickets — same shape as 2b (reuses the
equity-free heuristic family, texture classifier, composite provider, board UI). One-file-one-owner.
Build only after the gate is approved AND 2e-0 is done (T2 below has a hard cross-epic dependency on
2e-0's `_hand_category` fix). All refuter findings baked into the spec.

> **STATUS: ALL 7 TICKETS BUILT & VERIFIED (T1–T7).** 183 backend tests green (was 163 after 2e-0);
> `scripts/verify.sh` → `BACKEND VERIFY OK` (now with a `vs_check_raise` probe); frontend
> `vite build` + `tsc --noEmit` clean. T2's fold-baseline prior verified numerically (weak_made folds
> ~0.69 vs check-raise vs ~0.55 vs a plain c-bet). T5 corrected a bug in its own brief — a check-raise
> rebuild keys off `row.position` (hero = the opener/aggressor), not `row.facing` as the ticket first
> said. Live Playwright check pending (needs the user's dev servers up).

## DAG / waves
```
T1 ─┬─ T2 ─ T3 ─┐
    └─ T4 ───────┼─ T5 ─ T6 ─ T7
```
- W1: **T1** (contracts)
- W2: **T2** (grader, needs T1 + 2e-0 done), **T4** (builder, needs T1) — parallel
- W3: **T3** (provider, needs T2)
- W4: **T5** (drill, needs T3 + T4)
- W5: **T6** (frontend) → W6: **T7** (verify+docs)

---

### T1 — Contracts
`NodeContext.VS_CHECK_RAISE = "vs_check_raise"`; `LeakCategory.VS_CHECK_RAISE = 202`; bump
`TAXONOMY_VERSION`; `leak_category_for` gains a `VS_CHECK_RAISE` case. No `_postflop_signature`
shape change (2e-0's `faced_bet_bucket` fix already generalizes to "facing a raise").
- **Owns:** `domain/spot.py`, `domain/leaks.py`, `domain/grading.py` (leak case).
- **Done when:** new enum/leak values exist; `leak_category_for` routes `VS_CHECK_RAISE` correctly;
  no existing signature/leak test breaks.

### T2 — Check-raise grader
`domain/postflop.py`: `grade_vs_check_raise(spot, hero_range, villain_range, decision)` →
`EvaluationResult` over FOLD/CALL/RAISE. Reuses `range_advantage()` with `_villain_pos(spot)` as the
third argument (NOT hero's own position — refuter-caught naming risk) + 2e-0-fixed `_hand_category`
+ a new `_merits_vs_check_raise()` (higher fold baseline than `_merits_vs_cbet`, texture-conditioned
bluff plausibility per research §4.4/§10.3).
- **Owns:** `domain/postflop.py`, `tests/test_postflop.py`.
- **Depends:** T1, **and 2e-0 T2** (`_hand_category`'s top-pair→`weak_made` fix — this grader's
  fold-leaning design for top pair is wrong without it).
- **Done when:** anchors pass — strong (two-pair+/set/made straight/flush) → raise/call, never fold;
  air on high/dry → fold; combo draw on low-connected-wet → call (raise defensible); fold frequency
  for a fixed weak_made hand on a dry board is HIGHER than the analogous `grade_vs_cbet` spot (the
  check-raise-strength prior is doing real work); leak = 202.

### T3 — Provider routing
`PostflopHeuristicProvider.supports()` accepts `CBET`, `VS_CBET`, or `VS_CHECK_RAISE` (still gated to
`Street.FLOP`); `evaluate()/optimal()` dispatch adds `VS_CHECK_RAISE → grade_vs_check_raise`.
- **Owns:** `domain/providers/postflop.py`, `tests/test_provider.py`.
- **Depends:** T2.
- **Done when:** `vs_check_raise` spots grade via postflop; 2a/2b/2e-0 spots unaffected; non-flop →
  `NOT_FOUND`.

### T4 — Check-raise spot builder
`domain/scenarios.py::build_check_raise_spot(rng, pairing=None, eff_bb=100.0, raise_mult=None)` +
`sample_check_raise_spot()`. `raise_mult` defaults to `rng.choice([2.5, 3.0])`; **`CALL.min_bb =
raise_to - cbet`** (incremental delta — refuter-caught sizing bug, matches `VS_3BET`/`VS_4BET`
precedent, NOT `raise_to` itself); `pot_bb = flop_pot + cbet + raise_to`.
- **Owns:** `domain/scenarios.py`, `tests/test_scenarios.py`.
- **Depends:** T1.
- **Done when:** valid check-raise spot; hero = original aggressor; `CALL.min_bb` is the incremental
  delta (explicit assertion, not just "raise appears in history"); `pot_bb` includes both bets;
  cards disjoint; `raise_mult` param produces a distinguishably different `faced_bet_bucket`.

### T5 — Drill wiring
`api/v1/drill.py`: `/drill/next?mode=vs_check_raise` → `sample_check_raise_spot` (grid `{}`).
`_rebuild_postflop`/`_POSTFLOP_CTX` gain a `VS_CHECK_RAISE` branch for SRS review reconstruction.
- **Owns:** `api/v1/drill.py`, `tests/test_api.py`.
- **Depends:** T3, T4.
- **Done when:** `vs_check_raise` mode returns a valid spot that grades (leak 202) + persists; SRS
  review can reconstruct this archetype; 2a/2b/2e-0 + preflop + quizzes unaffected.

### T6 — Frontend
"Facing check-raise" drill mode entry; **`bettingLine()` street-scoped raise-verb fix** (refuter-caught:
the escalation counter currently spans the whole `action_history`, so a flop check-raise after a
preflop open would render as "3-bets" instead of "check-raises"/"raises to").
- **Owns:** `frontend/src/**`.
- **Depends:** T5.
- **Done when:** `vite build` + `tsc --noEmit` clean; live `vs_check_raise` spot shows "hero bets X,
  villain raises to Y" (correct verb, not an inherited preflop escalation count) + Fold/Call/Raise +
  grades.

### T7 — Verify + docs
`scripts/verify.sh` `vs_check_raise` probe; roadmap/README/ticket status.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap/ticket status.
- **Depends:** T1–T6.
- **Done when:** `verify.sh` green; live Playwright `vs_check_raise` check.

---

## Notes
- Riskiest: **T2** (the merit function must encode "check-raises are rarely bluffs at $1/$2" as a
  genuinely stronger prior than `grade_vs_cbet`'s fold baseline — the spec's Verify-by requires this
  be demonstrated numerically, not just asserted) and **T4** (the incremental-vs-total CALL sizing is
  exactly the kind of off-by-one-street bug the refuter caught once already; the done-condition
  explicitly asserts the delta, not just that a raise exists).
- 2e-0 must be DONE before T2 starts (hard cross-epic dependency) — T1 and T4 can start regardless.
