# Tickets — Phase 2b: Facing a Flop C-Bet (Defense)

Spec: `docs/ai-dlc/specs/phase-2b-vs-cbet.md`. 7 tickets — smaller than 2a (reuses the equity engine, texture classifier, composite provider, board UI). One-file-one-owner. Build only after the gate is approved. All 5 refuter fixes are baked into the spec.

> **STATUS: ALL 7 TICKETS BUILT & VERIFIED (T1–T7).** 141 backend tests green; `scripts/verify.sh` → `BACKEND VERIFY OK`; frontend `vite build` + `tsc --noEmit` clean. Live Playwright check pending (needs the user's dev servers up).

## DAG / waves
```
T1 ─┬─ T2 ─ T3 ─┐
    └─ T4 ───────┼─ T5 ─ T6 ─ T7
```
- W1: **T1** (contracts)
- W2: **T2** (grader, needs T1), **T4** (builder, needs T1) — parallel
- W3: **T3** (provider, needs T2)
- W4: **T5** (drill, needs T3 + T4)
- W5: **T6** (frontend) → W6: **T7** (verify+docs)

---

### T1 — Contracts + signature
`NodeContext.VS_CBET="vs_cbet"`; `LeakCategory.VS_CBET=201`; `leak_category_for` VS_CBET case; `_postflop_signature` gains `faced_bet_bucket` (`none`/`small`/`big` from the largest opponent `bet` in `action_history` vs pot).
- **Owns:** `domain/spot.py`, `domain/leaks.py`, `domain/grading.py` (leak case), `domain/srs.py`, `tests/test_signature.py`.
- **Done when:** same texture + different faced-bet size → different postflop signature; same size → same; **preflop signatures byte-identical** (existing guard test still green).

### T2 — Defender grader
`domain/postflop.py`: `range_advantage_defender(aggressor_pos, defender_pos, texture)` (no aggressor baseline; edge on low/connected/wet; OOP penalty on defender) + `grade_vs_cbet(spot, hero_range, villain_range, decision)` → `EvaluationResult` over FOLD/CALL/RAISE (freq + proxy EV incl. pot-odds + bet-size term; leak VS_CBET; rationale).
- **Owns:** `domain/postflop.py`, `tests/test_postflop.py`.
- **Depends:** T1.
- **Done when:** anchors pass — strong→raise/call never fold; air on high/dry vs big bet→fold; draw on wet defender-favored→call (raise defensible); **bet-size monotonicity** (small faced bet → higher call / lower fold than big); high&wet board reachable as `"defender"`; leak=201.

### T3 — Provider routing
`PostflopHeuristicProvider.supports()` accepts CBET **or** VS_CBET; `evaluate()/optimal()` dispatch CBET→`grade_cbet`, VS_CBET→`grade_vs_cbet`. Composite unchanged.
- **Owns:** `domain/providers/postflop.py`, `tests/test_provider.py`.
- **Depends:** T2.
- **Done when:** vs_cbet spots grade via postflop; 2a c-bet spots still grade; non-postflop/unknown → NOT_FOUND; preflop unaffected.

### T4 — vs-c-bet spot builder
`domain/scenarios.py`: `build_vs_cbet_spot()` (hero=BB OOP, villain=opener IP who has c-bet; `players=[BB(hero),opener]`; hero hand from BB call range; flop; villain `bet` appended; `pot_bb=flop_pot+cbet`; legal fold/call(=faced)/raise(≈3× w/ min_bb); `facing`=opener; ranges set) + `sample_vs_cbet_spot()`.
- **Owns:** `domain/scenarios.py`, `tests/test_scenarios.py`.
- **Depends:** T1.
- **Done when:** valid flop defense spot; hero OOP; pot includes c-bet; raise LegalAction has concrete min_bb; cards disjoint; signature distinguishes faced-bet size.

### T5 — Drill wiring
`api/v1/drill.py`: `/drill/next?mode=vs_cbet` → `sample_vs_cbet_spot` (grid `{}`). Grade route unchanged (composite handles it).
- **Owns:** `app/api/v1/drill.py`, `tests/test_api.py`.
- **Depends:** T3, T4.
- **Done when:** vs_cbet mode returns a flop defense spot that grades (leak 201) + persists; 2a postflop + preflop + quizzes unaffected.

### T6 — Frontend
"Facing c-bet" drill mode; `bettingLine()` renders the `bet` action ("CO bets X"). Board + fold/call/raise bar already exist.
- **Owns:** `frontend/src/**`.
- **Depends:** T5.
- **Done when:** `vite build` + `tsc --noEmit` clean; live vs_cbet spot shows board + c-bet line + Fold/Call/Raise + grades.

### T7 — Verify + docs
`scripts/verify.sh` vs_cbet probe; roadmap/README/ticket status.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap/ticket status.
- **Depends:** T1–T6.
- **Done when:** `verify.sh` green; live Playwright vs_cbet check.

---

## Notes
- Riskiest: **T2** (the defender grader's heuristics must read as sane poker AND satisfy bet-size monotonicity) and **T1's signature change** (must not perturb preflop hashes). Both get focused tests.
- Equity-backed range advantage stays deferred (still a positional+texture+pot-odds rule). The equity engine remains quiz-only.
