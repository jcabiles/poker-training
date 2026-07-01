# Delta spec — Challenge mode (preflop RFI, difficulty-biased sampling)

> Not on the postflop roadmap — a learning-quality feature. Built via the AI-DLC loop
> (scout → spec → refuter → tickets → build → verify). Contract scan folded in below.
> User decisions: **blended difficulty** (objective boundary + personal mistakes), delivered as an
> **opt-in "Challenge" mode**, **RFI-only** first slice, with a **DB migration** so the personal
> signal is truly per-hand.

## Goal (one line)
Add an opt-in `challenge` preflop drill mode that biases the DEALT hand toward high-difficulty RFI
spots — where fold-vs-raise is genuinely contestable (position-flippy, near the range edge) and,
increasingly, toward the specific hands this user misplays.

## Contract scan (verified by scout — key facts)
- **Sampling is uniform-random today.** `build_spot` deals `rng.sample(_DECK, 2)`
  (`scenarios.py:106-107`); which hand you see is decoupled from the chart. Challenge mode changes
  ONLY how the hand (and RFI seat) is chosen — everything downstream (grading, feedback) is reused.
- **`range_grid(entry)`** (`grading.py:241-257`) is pure-domain, no equity/IO, returns
  `{hand_class: "raise"|"fold"|"call"|"mixed"}` for one Entry. Cheap to call for all 6 RFI seats →
  exact cross-position flip signal.
- **Near-edge proxy** exists: `grade()` scores by `hand_rank` distance to the range floor
  (`_range_floor`, `grading.py:127-135`). Authored *mixed frequencies* do NOT exist in RFI content
  (`is_mixed` is structurally always false for RFI) — so difficulty uses **flip + edge-distance**,
  not authored mixes.
- **No per-hand history today.** `DrillAttempt` (`models.py:22-33`) stores `chosen_action` +
  `spot_signature` but NO hand class; the signature deliberately excludes hole cards
  (`srs.py:5-7`). Hence the migration (below).
- **Purity boundary** (`tests/test_domain_purity.py`): `app.domain.scenarios`/`grading` must not
  import DB/web. Precedent for DB-informed sampling: `_next_leak_focus` (`drill.py:171-177`) — the
  API layer fetches DB stats and passes plain data into a pure domain sampler.

## Difficulty model (the crux — define precisely, refuter to stress this)
For a candidate `(position P ∈ RFI seats, hand class H)`:

- **Flip score F(P,H) ∈ [0,1]** — fraction of the *other* 5 RFI seats whose `range_grid` action for
  H differs from H's action at P. Raise-everywhere (AA) → 0; raise-some/fold-some (A9o, KTo, 66,
  low SC) → high. This is the primary signal (matches the user's CO-vs-LJ example).
- **Edge score E(P,H) ∈ [0,1]** — locality to a raise/fold TRANSITION in P's own chart.
  **(refuter HIGH-1)** Do NOT derive this from `_range_floor` (a single min-rank scalar): the RFI
  raise/fold split is non-monotonic in the `hand_rank` proxy (suited-connector playability isn't
  modeled by `_strength()`), so trash like 74o/82o that ranks near a loose seat's floor would score
  spuriously high. Instead: order all 169 classes by `hand_rank`; E(P,H) = closeness (in rank-ORDER
  steps, kernel-decayed) to the nearest hand whose `range_grid` action at P DIFFERS from H's. A hand
  adjacent to a raise→fold transition scores ~1; a hand deep inside a homogeneous raise (AA) or fold
  (72o) block scores ~0. Robust because it reads actual chart membership, not a scalar threshold.
  Depends on a STABLE rank order — see the hand_rank prereq below.
- **Objective difficulty** `D_obj(P,H) = wF·F + wE·E` (start `wF=0.6, wE=0.4`; F emphasized per the
  user's ask). Tunable constants, commented.
- **Personal multiplier M(H) ∈ [Mmin, Mmax]** (e.g. 0.5–2.0, default **1.0**) — **(refuter MED)**
  from the user's **mean EV-loss** on hand class H in RFI attempts (one pinned metric — continuous,
  already stored per attempt; not binary correctness). **Min-sample guard: if H has < 5 RFI
  attempts, M(H)=1.0** (neutral) regardless of observed rate. Injected as plain data; empty history
  ⇒ all-neutral ⇒ pure objective difficulty (cold start fully useful).
- **Sampling weight** `W(P,H) = (ε + D_obj(P,H)) · M(H)`, small floor `ε` (e.g. 0.02) so every
  legal hand keeps a nonzero chance (calibration + coverage). Sample `(P,H)` jointly ∝ W over the
  6×169 grid, then deal a random specific combo of H (reuse existing combo expansion), then
  `build_spot`.

## Files / interfaces to touch
- **PREREQ — deterministic hand_rank (refuter HIGH-2):** `backend/app/domain/hand_rank.py` — the
  rank table is built from a `set` (`all_hands()`), so the 24 `_strength()` ties resolve by
  `PYTHONHASHSEED` and swap between runs. Fix the ordering to a stable tie-break (e.g.
  `sorted(all_hands(), key=lambda h: (_strength(h), h))`). Pre-existing bug; the edge score's
  rank-ORDER definition depends on it. Land first. Add a test asserting a tied pair (e.g. KQo/88)
  gets stable ranks across `PYTHONHASHSEED` values.
- **DB + migration:** `backend/app/db/models.py` — add `hand_class: str | None` (nullable) to
  `DrillAttempt`. New Alembic migration (confirmed head 0004 → **0005**) adding the column. Populate
  it **unconditionally on every grade** (all modes — cheap, always derivable) at the persist path
  (~`drill.py:214-223`) via `hole_cards_to_class` (`app/domain/content/notation.py:91-99`) on the
  graded spot's hole cards. RFI-only scoping happens later in the query, not here. **(refuter LOW)**
- **Domain (pure):** new `backend/app/domain/challenge.py` (or a scoped section of `scenarios.py`) —
  `sample_challenge_spot(rng, personal_weights: dict[str, float] | None = None, eff_bb=...)` +
  the pure `F/E/D_obj/W` scorers. Imports only `app.domain.*` (uses `range_grid`, `hand_rank`,
  RFI entries via the index). NO DB/web import.
- **Service:** `backend/app/services/stats.py` — `hand_error_weights(session) -> dict[str, float]`:
  aggregate `DrillAttempt` by `hand_class`, **filtered to RFI via `leak_category IN {RFI_EP=100,
  RFI_MP=101, RFI_CO=102, RFI_BTN=103, RFI_SB=104}`** (there is NO `node_context` column — this set
  is the only correct RFI filter; source `app/domain/leaks.py`). Per hand class with **≥5** attempts,
  compute mean `ev_loss_bb` → map to a multiplier in `[Mmin,Mmax]`, normalized so the mean
  multiplier ≈ 1.0; classes with <5 attempts are omitted (caller defaults them to 1.0). **Guard the
  degenerate cases** (zero rows → `{}`; all-equal / near-zero mean → return neutral 1.0s, no
  divide-by-zero). **(refuter MED)**
- **API:** `backend/app/api/v1/drill.py` — `_next_challenge(session)` (fetch weights → call the
  pure sampler), `elif mode == "challenge"` branch in `next_drill` (~181-198), and the module
  docstring mode list (drill.py:5-7).
- **Frontend:** `frontend/src/api/types.ts:87-94` `Mode` union += `"challenge"`;
  `frontend/src/App.tsx:28-36` `MODES` += `{ id: "challenge", label: "Challenge" }`. `client.ts` is
  generic over `Mode` — no change.

## Out of scope
- Postflop challenge (flop/turn/river) — RFI preflop only.
- Non-RFI preflop nodes (vs-3bet, vs-4bet, blind defense, squeeze, vs-limpers) — a follow-up slice.
- Authoring mixed-frequency RFI content (difficulty uses flip + edge-distance, not authored mixes).
- Changing any existing mode's sampling (`random`/`leak_focus`/etc. stay uniform).
- Backfilling `hand_class` for historical `DrillAttempt` rows (new column is nullable; personal
  signal simply grows as new attempts land).
- Per-(position×hand) personal granularity — personal weight is per hand class across RFI (denser,
  avoids sparsity); position bias comes from the objective F/E terms.

## Constraints (house rules + discovered)
- **Domain purity:** the difficulty scorer/sampler imports no DB/web; personal weights arrive as an
  injected `dict[str,float]`. **`tests/test_domain_purity.py`'s hardcoded module list must gain
  `app.domain.challenge`** — an explicit build step, not just prose, or the guard silently passes
  even if the new module imports sqlalchemy/fastapi. **(refuter LOW)**
- **Cold start:** empty `personal_weights` ⇒ `M(H)=1.0` everywhere ⇒ pure objective difficulty. The
  mode must be fully useful with zero history.
- **Determinism/testability:** sampling takes an injected `rng` (seedable) so distribution tests are
  deterministic. Difficulty constants (`wF,wE,ε,Mmin,Mmax`) are named module constants, commented.
- **Frequency+EV preserved:** grading/feedback path is untouched — challenge only changes selection.
- **Migration safety:** additive nullable column; no data rewrite; `alembic upgrade head` clean;
  downgrade drops the column.

## Verify-by (end-to-end)
1. `./scripts/verify.sh` → `BACKEND VERIFY OK`; `alembic upgrade head` applies 0005 cleanly; domain
   purity test green.
2. **Distribution test (objective, cold start):** sample N (e.g. 3000) challenge spots with a seeded
   rng and no history → boundary hands (A9o, KTo, 66, 54s, KTo/QJo-class offsuit broadways) appear
   markedly more than premiums (AA/AK) and trash (72o); assert weight ordering, not exact counts.
2b. **Position-flip is exercised:** the sampled set includes the same hand at seats where it's a
   raise AND seats where it's a fold (e.g. A9o at BTN vs LJ).
2c. **Edge score is not fooled by trash-near-floor (refuter HIGH-1):** assert E(BTN, ·) is LOW for
   74o/82o/93o (unambiguous folds that rank near BTN's loose floor) and HIGH for hands adjacent to a
   raise/fold transition.
2d. **Determinism (refuter HIGH-2):** hand_rank of a tied pair (KQo/88) is identical across
   `PYTHONHASHSEED=1` and `=42`; a seeded challenge run reproduces the same hand sequence.
3. **Personal blend:** seed `DrillAttempt` rows with repeated errors on one hand class (e.g. KJo) in
   RFI → `hand_error_weights` raises KJo's weight → KJo's sampled share rises vs the cold-start run.
4. **API:** `GET /api/v1/drill/next?mode=challenge` returns a preflop RFI spot with a `grid`; grading
   the returned spot still works and now persists `hand_class`.
5. **Frontend:** `npm run typecheck && npm run build` clean; "Challenge" selectable in the mode list
   and drives `?mode=challenge`.
6. **No regression:** existing modes unchanged; `mode=random` still uniform.

## Pre-build note
Build on a fresh branch off the now-current `main` (user pulled). This is independent of
`feat/collapsible-range-grid`. New migration = 0005 (0004 is the latest head).
