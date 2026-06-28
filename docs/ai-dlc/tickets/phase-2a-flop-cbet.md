# Tickets — Phase 2a: Flop C-Bet + Foundational Postflop Drills

Spec: `docs/ai-dlc/specs/phase-2a-flop-cbet.md`. 9 tickets (biggest slice yet — postflop introduces an equity engine + a new grader). Small, one-file-one-owner. Build only after the gate is approved.

> **STATUS: ALL 9 TICKETS BUILT & VERIFIED (T1–T9).** 128 backend tests green; `scripts/verify.sh` → `BACKEND VERIFY OK`; frontend `vite build` + `tsc --noEmit` clean. Live Playwright check pending (needs the user's dev servers up).

## DAG / waves
```
T1 ─┐
T2 ─┼─ T4 ─ T5 ─┐
T3 ─┘           ├─ T7 ─ T8 ─ T9
        T6 ─────┘
```
- W1: **T1, T2, T3** (parallel — disjoint)
- W2: **T4** (needs T2+T3), **T6** (needs T3)
- W3: **T5** (needs T4)
- W4: **T7** (needs T5+T6+T1+T2)
- W5: **T8** → W6: **T9**

---

### T1 — Equity engine (pure Python)
`domain/equity.py`: 7-card best-5 evaluator + `equity_vs_range(hero, board, villain_combos, iters, rng)` with dead-card filtering (filter villain combos vs `hero|board` before the loop; runout from `deck − dead − combo`), own seeded RNG, iter cap.
- **Owns:** `domain/equity.py`, `tests/test_equity.py`.
- **Done when:** AA vs KK preflop ≈ 0.82, nut = 1.0, crushed ≈ 0; deterministic with a seed; blocked combos excluded; equity-estimation-sized call < ~150ms.

### T2 — Board-texture classifier
`domain/texture.py`: flop → `{wetness, pairing, suitedness, connectedness, high_card}` + `texture_class` label.
- **Owns:** `domain/texture.py`, `tests/test_texture.py`.
- **Done when:** anchors pass (A♠K♦2♣ dry/rainbow/unpaired; 9♥8♥7♥ wet/monotone/connected).

### T3 — Postflop contracts
`Spot.hero_range`/`villain_range`; `NodeContext.CBET`; `spot_signature` postflop branch (texture+SPR buckets, preflop path unchanged); `LeakCategory` 200/210/211; `leak_category_for` CBET case.
- **Owns:** `domain/spot.py`, `domain/srs.py`, `domain/leaks.py`, `domain/grading.py` (CBET leak case), `tests/test_signature.py`.
- **Done when:** postflop signature stable across same-texture/different-board; preflop signatures byte-identical to before.

### T4 — Postflop grader
`domain/postflop.py`: `range_advantage()` (positional+texture heuristic, no equity) + `grade_cbet()` producing `EvaluationResult` (CHECK/BET freq+EV, FLOP_CBET leak, rationale).
- **Owns:** `domain/postflop.py`, `tests/test_postflop.py`.
- **Depends:** T2, T3.
- **Done when:** dry+range-adv → small bet OPTIMAL; big bet OOP with air on wet board → worse; leak = FLOP_CBET.

### T5 — Provider routing
`PostflopHeuristicProvider` + `CompositeProvider` (route by street; supports-chain; not-found fallback); `get_provider()` returns composite.
- **Owns:** `domain/providers/{postflop.py,composite.py,factory.py,__init__.py}`, `tests/test_provider.py`.
- **Depends:** T4.
- **Done when:** preflop spots still grade via HeuristicProvider; flop spots via postflop; unknown → not_found.

### T6 — Flop spot builder
`scenarios.build_cbet_spot()` — HU SRP flop from a preflop pairing, sets hole cards + flop + hero_range/villain_range + legal (check/bet33/bet75); a `sample_cbet_spot()`.
- **Owns:** `domain/scenarios.py`, `tests/test_scenarios.py`.
- **Depends:** T3.
- **Done when:** valid flop spot with ranges set + disjoint cards; signature stable.

### T7 — Drill + quiz wiring
`/drill/next?mode=postflop` (flop c-bet, grid `{}`); `/drill/quiz/next` + `/drill/quiz/grade` (`QuizItem`/`QuizResult`, texture + equity, tolerance bands) persisting `DrillAttempt` (provider `"quiz"`); `_next_review` postflop fallback.
- **Owns:** `api/v1/drill.py`, `app/schemas/drill.py`, `tests/test_api.py`.
- **Depends:** T5, T6, T1, T2.
- **Done when:** postflop mode grades + persists; both quizzes round-trip + grade; preflop modes + grid unaffected.

### T8 — Frontend (board + c-bet + quizzes)
Board render (3 cards) on the table; Check/Bet decision bar; Postflop mode; texture-classification quiz screen; equity-estimation input screen; mode entries.
- **Owns:** `frontend/src/**`.
- **Depends:** T7.
- **Done when:** `vite build` + typecheck clean; flop c-bet + both quizzes work live.

### T9 — Verify + docs
`scripts/verify.sh` postflop + quiz checks; README/roadmap/ticket status.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap/ticket status.
- **Depends:** T1–T8.
- **Done when:** full verify-by green via one command; live Playwright postflop check.

---

## Notes
- Riskiest: **T1** (equity correctness/perf — dead-card filtering is the classic bug) and **T4** (the new grader's heuristics must read as sane poker). Both get focused tests.
- Range-vs-range equity (equity-backed range advantage) is intentionally deferred to 2b — 2a's range advantage is a positional+texture rule.
