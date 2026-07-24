# W3-b/c/d — position / street / texture mechanics

**Slice of:** `docs/ai-dlc/roadmap/persona-realism.md` → W3 (context). Second PR of the
two-PR W3 packaging (W3-a plumbing landed in PR #96). Built serial — all three slices
rewrite the one `personas_postflop.py` merit-assembly hotspot, so no concurrency.

## Goals (fixes F1 / F4 / F19 / F8 / F3 / F20)
- **W3-b (B1, F1) — position.** An IP/OOP multiplier on the whole aggressor-side BET
  candidate (bluff + value + semi-bluff), scaled by a new per-persona
  `position_sensitivity` lever. Disciplined types (tag/nit=1.0, lag=0.6) c-bet more IP;
  station/fish/maniac stay position-blind (`None`→0.0 — an intended leak). Aggressor-side
  c-bet/barrel frequency ONLY; the matched-with-option check-raise and the OOP
  continue/defense damp are out of scope (Later).
- **W3-c (B6/B7, F4/F19/F8) — street schedule.** A `street_agg_mult` decays the
  bluff/semi-bluff merit ONLY (value never scaled): flop ×1.0 (byte-identical invariant)
  → turn ×0.6 → river ×0.33. WEAK semi-bluffs decay steeper (turn ×0.4 → river ×0.0,
  F19). Busted draws that BET the previous street get extra river bluff mass (B7, via the
  W3-a `bet_prev_street` + `busted_draw`; STRAIGHT > FLUSH). Applies to all personas.
- **W3-d (B2/B3, F3/F20) — texture brakes.** A vulnerable one-pair BET merit is damped by
  overcard count (0→×1.00, 1→×0.75, 2+→×0.50) and board wetness (dry ×1.00 → high-two-tone
  ×0.85 → connected ×0.70 → monotone ×0.55). MIDDLE_PAIR / TOP_PAIR ONLY — OVERPAIR_TPTK
  (bundles overpairs) and sets/monsters keep betting. Composes multiplicatively with B1 +
  multiway. Reuses the ONE `texture.classify`.

## Files
- `app/domain/content/models.py` — new optional `position_sensitivity` lever (None→0.0).
- `app/domain/personas_postflop.py` — the three mechanics + helpers; runtime import of
  `PostflopContext`/`BustedDraw` (cycle broken by making `postflop_context`'s personas
  import lazy).
- `content/personas/{tag,nit,lag}.json` — `position_sensitivity` opt-in.
- `tests/test_personas_postflop.py` — W3-b/c/d exact-weight unit tests; updated street pins.
- Seeded fixtures re-recorded (below).

## Out of scope
No matched-with-option position effect · no OOP defense/realization damp · no
`street_polarization`/`position` lever beyond `position_sensitivity` · no equity solve
(heuristic only) · no barrel-more-on-scare-cards range side (villain-range pilot, Later).

## Invariants honored
Domain purity · grading via the sampler unchanged · `spot_signature()` frozen · FE types
untouched (`position_sensitivity` is content-only, no API shape change) · flop stays
byte-identical for the STREET schedule (mult 1.0); W3-b (opted personas) and W3-d
deliberately move flop one-pair betting.

## Fixtures re-recorded (slice-authorized; bands frozen to W4-b)
- `_GOLDEN_STATS_N200`, `coverage_baseline.json`, limper `_PRE_M3_FIRES` — shared-rng
  stream displaced by the behavior change; every `_WANT_*` coverage shape still fires.
- **Coverage ratio dipped 29.6% → 27.5%** (graded 363→345 of 1255). This is MAPPER
  coverage (orthogonal): more-realistic villains visit a different mix of hero spots and
  the unchanged mapper grades that mix slightly less. Flagged for the mapper track, NOT a
  persona-realism regression.

## WTSD test stabilization (flakiness fix — owner-approved "more hands")
W3-b narrowed the station-vs-tag WTSD gap to ~0.044 (still station > tag, robust at
n≥2000). The population WTSD assertions (bands + ordering) measured at the
throughput-derived n≈200–400 (3σ≈0.10) then flaked. Fix: **all WTSD assertions now
measure at a fixed `_WTSD_ORDER_N = 2500`** (machine-independent; `_persona_stats`
memoizes per (persona, n), so bands + ordering share the sims — paid once). AF/FtC stay
on the cheaper throughput-n. Band VALUES untouched (frozen). maniac WTSD stays deferred
(it sits exactly on its 0.50 ceiling — unfixable by sample size).

## Verify-by
`./scripts/verify.sh` green (931 passed, 1 skipped — maniac WTSD defer), boot OK; `ruff
check .` clean. Both WTSD tests stable across repeated runs.

## Review dispositions
_(folded from the refuter + Codex Sol fan-in — see the PR.)_
