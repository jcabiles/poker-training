# Spec — P1: Persona correctness patch (fold-aces · open-limps · oversized 3bet · air-calls · overlap guard)

> Slice of `docs/ai-dlc/roadmap/persona-realism.md` (NOW slice P1). Reference/contract map:
> `docs/research/12-persona-engine-and-realism-fixes.md`. Inherits that roadmap's north-star,
> no-gos, and the initiative invariants (§6.3). One slice → one PR.

## Goal (one line)
Remove the loudest **off-archetype content bugs** + one **shared-table air-call** over-loosening, with a
new **overlap validator**, WITHOUT any engine-signature change — a pure correctness patch that precedes the
structural work (P2a/P2b/P3/P4).

## Files to touch (exact — one owner each)
| File | Fix(es) | Owner ticket |
|---|---|---|
| `content/personas/calling_station.json` | B1 | T1 |
| `content/personas/maniac.json` | M3 · N4/N5 · N3 | T2 |
| `content/personas/lag.json` | M3 | T3 |
| `backend/app/domain/personas_postflop.py` | A1 (`_CALL_BASE[AIR]`) | T4 |
| `backend/tests/test_content.py` | N2 validator (+ any residual-overlap fixes in packs) | T5 |
| `backend/tests/test_personas_postflop.py`, `test_coverage_baseline.py`, `test_personas.py`, `test_limper_coverage_belt.py`, `backend/tests/data/coverage_baseline.json` | re-anchor bands + re-record baselines + cumulative-delta report | T6 |

> **M1 (content half — maniac `aggression` 15.0→5.6) is DROPPED from P1** (refuter F1). Setting the lever to
> the cap breaks `test_aggression_cap_binds_maniac_only` (it asserts maniac `aggression > cap` *strictly* — the
> 15.0 exists to prove the cap clips maniac) while changing **zero** sampled behavior (the cap already clips
> 15.0→5.6). No behavioral value, guard cost → deferred to NEXT with the behavior-changing `tanh` code-half.

`backend/tests/data/coverage_baseline.persona-realism-start.json` — **immutable initiative snapshot already
committed in this branch's first commit; T6 reports cumulative delta vs it, never overwrites it.**

## The fixes (current → target)

### B1 — station never folds premiums first-to-act *(calling_station.json)*
Both `unopened` nodes (UTG-specific + `positions:null` default) carry
`{ "combos": "AA, KK, AKs", "weights": { "raise": 0.6, "fold": 0.4 } }`. A station folding 40% of its
premiums unopened is a hard bug. **Target:** replace the `fold` leg with `limp` (station is passive → limps
a lot, never folds a premium FTA): `{ "raise": 0.5, "limp": 0.5 }` (exact split at implementer discretion,
but **zero fold weight**). "call" is not a legal unopened action; use raise/limp only.

### M3 — no non-SB open-limps *(maniac.json + lag.json)*
Maniac & LAG are **raise-or-fold** archetypes; open-limping every seat is off-archetype (doc 12 §9 M3).
**Target:** delete the `limp` mix from **every `unopened` node EXCEPT `positions:["SB"]`** (SB completing the
small blind is a legitimate raise-or-limp spot — keep it). Deleted combos fall through first-match-wins to
fold (raise-or-fold). Do NOT re-home them into raise mixes — deletion is the fix.
- maniac: unopened UTG/UTG1/UTG2/LJ/HJ/CO/BTN/BB lose their limp mix; SB keeps it.
- lag: unopened UTG/UTG1/UTG2/LJ/HJ/CO/BTN/BB lose their `limp 0.7/fold 0.3` mix; SB keeps it.

### N4/N5 — maniac 3bet not absurd *(maniac.json)*
`sizing.threebet_mult: 5.5` → **3.3** (open 4.5bb → 3bet ~14.9bb, was 24.75bb). Keep maniac the largest sane
3bettor (LAG=3.5 mult on a 3.0 open = 10.5bb; maniac 14.9bb stays biggest). Target band 3.0–3.5.

### N3 — maniac re-jams LIGHTER than LAG *(maniac.json vs_3bet / vs_4bet)*
**Refuter F4 correction:** maniac's 5bet-shove combo *set* (`QQ+, AKs, AKo` + `A5s/A4s/KQs` half) is *already*
a superset of LAG's (`QQ+, AKs` + `A5s`), so a plain set-membership superset guard passes **trivially** without
any rebuild. The real bug is **behavioral**: maniac doesn't jam **lighter** (no distinctly-maniac light bluff
combos) and has **no trap flats** (AA/KK are inside `QQ+` at pure-shove 1.0). **Target shape** (exact combos at
implementer discretion, guarded by the BEHAVIORAL test below):
- **vs_4bet**: value shoves `QQ+, AKs, AKo`; **add light 5bet-shove bluffs LAG never shoves** (Ax-blocker
  suited + small pairs — e.g. `A3s, A2s, 55, 66` — at partial weight; LAG shoves none of these); **split AA/KK
  into a partial `call` (trap) leg** so they're no longer pure-shove; keep some `TT/JJ/AQs` calls.
- **vs_3bet**: keep/modestly widen the 4bet value+bluff split; do not narrow it.
- **Guard (behavioral, not set-membership):** (a) maniac vs_4bet has **≥3 combos at nonzero `5bet_shove` weight
  that have zero shove weight in LAG's vs_4bet** (the light-jam inversion); (b) maniac vs_4bet has **nonzero
  `call` weight on `AA` and/or `KK`** (trap flats — impossible today); (c) no cross-mix combo overlaps in any
  node (T5 validator).

### A1 (shared table) — air stops calling without a draw *(personas_postflop.py)*
`_CALL_BASE[StrengthBucket.AIR]: 0.25` → **0.08** (line ~251). **Street-neutral base drop only.** No-draw air
call merit falls to `0.08 × stickiness`; drawing air is untouched because `_DRAW_CALL_BONUS`
(WEAK 0.20 / STRONG 0.55) already adds on top — so the "gate air-continue behind a real draw" is achieved by
the *ratio* shifting, no new branch. **Ownership boundary (Codex-Sol F4): P1 MUST NOT add river-specific
logic** — the river "air-call ≈0" gate belongs to P2a (street-aware). This is a shared table used by every
persona AND the population harness AND `range_estimate` replay → it deliberately changes sampled decisions →
`test_personas_postflop.py` fixtures + population bands re-anchor in **T6** (not silently).

### N2 — overlap validator *(test_content.py)*
Add a test asserting **no combo appears in more than one mix within a single preflop node** across all six
packs (first-match-wins silently shadows later overlaps — doc 12 N2). Include a **synthetic overlapping pack
that the validator rejects** (positive + negative case). **Run/author AFTER T2's maniac rebuild** so it
self-checks the new mixes; fix any residual real overlaps it surfaces (T5 owns the packs at that point).

## Out of scope (P1)
- No `street` kwarg / river polarization (P2a). No scare-card/bluff-decay memory (P2b). No stickiness split
  (P3). No preflop position/size kwargs (P4). No `range_estimate.py` change (P1 doesn't diverge the live
  policy from the streetless one — A1 shifts the shared table identically for live + estimator).
- No grader touch: `grade_map*.py`, `postflop.py` graders, `spot_signature()`, `TAXONOMY_VERSION` frozen.
- No solver ranges. No new engine randomness (action draw stays the first `rng.choices`).

## Constraints (inherited invariants — doc 12 §6.3 / profile)
- Domain purity: `personas_postflop.py` stays web/DB-import-free.
- Results are frequency + EV, never boolean; EVs labeled *approximate*.
- Strategy lives in `content/` data — content fixes are JSON edits, not code branches.
- Anti-sizing-tell (`test_sizing_spread_no_deterministic_strength_to_size`) and bluff-ordering
  (`test_bluff_ordering_across_personas_at_fixed_size` — `station < nit < fish < tag < lag < maniac`) pins
  must stay green (A1 touches CALL merit, not the bluff path — should not move bluff ordering; verify).
- `_AGGRESSION_CAP` guard untouched — P1 does NOT change any `aggression` lever (M1 deferred), so
  `test_aggression_cap_binds_maniac_only` (maniac lever `> cap`, all others `<= cap`) stays green unmodified.
- Re-anchor bands **levers-first, with in-file justification**; re-record `coverage_baseline.json`
  deliberately; **report cumulative graded-coverage delta vs the immutable snapshot** and adjudicate any loss.

## Verify-by (end-to-end)
1. `./scripts/verify.sh` → `BACKEND VERIFY OK` (all backend tests + boot probe).
2. `cd backend && ruff check .` clean.
3. Slice pass/fail (roadmap P1):
   - station never folds `AA/KK/AKs` unopened (test).
   - no persona has a non-SB `unopened` limp mix (validator/test).
   - maniac `threebet_mult ≤ 3.5`; maniac vs_4bet has ≥3 `5bet_shove` combos LAG never shoves **and** nonzero
     AA/KK `call` trap weight (behavioral inversion test — not a trivial set-superset check).
   - **(refuter F3 — reachable relative criterion, NOT an absolute 0.9)** on a no-pair-no-draw board, air's
     no-draw CALL frequency facing a medium bet **drops materially vs the pre-A1 baseline** (regenerate the
     §4 dist; assert the air call-freq **at least halves** and that **fold now exceeds call** for air). The
     literal "air-fold ≈0.9 / ≈0 on the river" gate needs `_FOLD_BASE`/street logic → **P2a**, out of P1.
     Draw-air (WEAK/STRONG) call-freq stays materially higher than no-draw air (the draw gate holds).
   - overlap validator rejects a synthetic overlapping-combo pack (test).
   - population bands re-anchored with in-file justification; `coverage_baseline.json` re-recorded; cumulative
     delta vs immutable snapshot reported.
