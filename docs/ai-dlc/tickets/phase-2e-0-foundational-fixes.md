# Tickets — Phase 2e-0: Foundational Fixes (pre-turn/river)

Spec: `docs/ai-dlc/specs/phase-2e-0-foundational-fixes.md`. 5 tickets — pure bug-fix, no new feature.
One-file-one-owner. Build only after the gate is approved. All refuter findings baked into the spec.

> **STATUS: ALL 5 TICKETS BUILT & VERIFIED (T1–T5).** 163 backend tests green (was 148 pre-2e-0);
> `scripts/verify.sh` → `BACKEND VERIFY OK`; zero new ruff findings (20 pre-existing, unchanged).
> T2 confirmed the top-pair→`weak_made` demotion changed no existing fixture's expected output
> (top-pair spots still resolved to the same best action). T5 fixed the 5th `classify()` site in
> `srs.py::_postflop_signature` (byte-identical for 3-card boards — no signature-hash change).

## DAG / waves
```
T1 ─┐
T2 ─┼─ T5
T3 ─┤
T4 ─┘
```
- W1: **T1, T2, T3, T4** (parallel — disjoint files, no cross-dependencies)
- W2: **T5** (needs T1–T4)

---

### T1 — `faced_bet_bucket` raise-aware rewrite
`domain/srs.py::faced_bet_bucket()`: read `CALL.min_bb` from `spot.legal_actions` (not
`action_history` scanning); subtract `hero_prior_this_street` (hero's own `BET`/`RAISE` amounts on
`spot.street`) from `pot_bb - faced` to get the correct pre-bet pot. Update
`tests/test_signature.py::_vs_cbet_spot()` to set `legal_actions=[LegalAction(action=CALL,
min_bb=cbet)]` (currently unset — the rewrite would otherwise break
`test_faced_bet_size_changes_signature`).
- **Owns:** `domain/srs.py`, `tests/test_signature.py`.
- **Done when:** byte-identical output for `hero_prior_this_street == 0` (all existing vs_cbet
  cases); a hand-computed check-raise fixture (hero has prior street investment) buckets correctly;
  differentiates a small vs. big check-raise across ≥2 different `cbet` baselines;
  `test_faced_bet_size_changes_signature` still passes.

### T2 — `_hand_category` made-hand fix
`domain/postflop.py::_hand_category()`: demote plain top pair (`made == 2`) to `"weak_made"`;
`"strong"` now requires `made >= 3` (two-pair/set) OR a made straight/flush (new checks, evaluated
before the pair-based tiers). `flush_draw`/`oesd` only fire when no made straight/flush exists.
- **Owns:** `domain/postflop.py`, `tests/test_postflop.py`.
- **Done when:** monotone-flop made flush → `"strong"`; made straight → `"strong"`; plain top pair →
  `"weak_made"` (regression anchor for the live 2b bug the refuter traced); unmade flush-draw/OESD →
  still `"draw"`; two-pair/set → still `"strong"`; existing `grade_cbet`/`grade_vs_cbet` fixtures that
  use top-pair or made-flush/straight hands have their expected output updated (documented as
  intentional) and the full suite stays green.

### T3 — Provider street guard
`domain/providers/postflop.py::PostflopHeuristicProvider.supports()`: gate to `spot.street ==
Street.FLOP` (was `len(board) >= 3`, silently accepting turn/river).
- **Owns:** `domain/providers/postflop.py`, `tests/test_provider.py`.
- **Done when:** a `Street.TURN`/`Street.RIVER` spot with `CBET`/`VS_CBET` context returns
  `Coverage.NOT_FOUND` via `CompositeProvider`; flop spots unaffected.

### T4 — `classify()` call-site cleanup
Make the remaining 3 `classify(spot.board)` call sites (of 5 total identified — 2 already slice
correctly) pass `spot.board[:3]` explicitly: `services/review.py::_postflop_archetype()` and
`api/v1/drill.py::_rebuild_postflop`'s `_key` closure. Document `classify()`'s contract as
"classifies exactly the first 3 cards given" (no behavior change to `classify()` itself — this
ticket is about honest call sites, not the function).
- **Owns:** `services/review.py`, `api/v1/drill.py`, `domain/texture.py` (docstring only).
- **Done when:** all 5 identified call sites are consistent; no behavior change for flop spots
  (still classifies the same 3 cards); grep confirms no remaining un-sliced `classify(spot.board)`
  call outside a street-gated context.

### T5 — Verify + docs
`scripts/verify.sh` — no new probe needed (this ticket changes no wire contract), but re-confirm the
full suite green after T1–T4's fixture updates. Update `docs/ai-dlc/roadmap.md`/ticket status to
DONE.
- **Owns:** `scripts/verify.sh` (if any regression probe needed), `docs/ai-dlc/roadmap.md`, this
  ticket file's status line.
- **Depends:** T1–T4.
- **Done when:** `scripts/verify.sh` → `BACKEND VERIFY OK`; roadmap reflects 2e-0 DONE.

---

## Notes
- Riskiest: **T2** (`_hand_category`'s top-pair demotion is a deliberate behavior change to shipped
  2a/2b output — every existing fixture touching a top-pair or made-flush/straight hand needs its
  expected value re-derived, not just re-run) and **T1** (the raise-aware pot formula has no existing
  precedent in this codebase to copy verbatim — verified by hand-derivation in the spec, needs its
  own focused test with ≥2 baselines per the refuter's finding).
- T1–T4 are fully parallel (disjoint files) — safe to build with 2-3 concurrent sub-agents at once.
