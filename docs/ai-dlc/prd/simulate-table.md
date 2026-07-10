# PRD — Simulate (persona table)

> Living hypothesis, not frozen contract. Gate decisions captured 2026-07-09/10 via interview
> (3 rounds + confirmed playback). Roadmap: `docs/ai-dlc/roadmap/simulate-table.md`.
> Research inputs: NLHE RNG best practices + persona/bot design (summarized in §8; agent
> reports 2026-07-09).

## 1. Context & problem

The app trains isolated spots ("Practice" = `drill` view): one decision, immediate feedback,
next random spot. What exists today:

- Grading: **all preflop families** (`content/preflop/*.json` — rfi, vs_rfi, vs_3bet, vs_4bet,
  vs_limpers, blind_defense) + **flop only** (c-bet, vs-c-bet, check-raise) behind the one async
  `StrategyProvider` (`backend/app/domain/providers/`). Turn/river and multiway grading do
  **not** exist — turn/river spots return `Coverage.NOT_FOUND` (street-gating landed in commit
  `53c865c`). ⚠️ `docs/ai-dlc/contracts/postflop-turn-river.md` is **partially stale** — it
  predates `53c865c`, which fixed its truncation/`faced_bet_bucket`/`_hand_category` hazards;
  still live: `range_advantage()`'s dead `node_context` param and `_rebuild_postflop()`'s
  silent random fallback (both assigned to roadmap slices S6/S7).
- Archetypes: `domain/archetypes.py` has 4 villain types (calling_station, nit, lag,
  passive_fish) used only as **hero-exploit drill adjustments** (`content/preflop/exploit.json`)
  — nothing *acts* as these players.
- Verdicts: `Correctness` enum (optimal / acceptable / mistake / blunder) + freq/EV results +
  tiered feedback composer — all reusable as-is.
- No game engine: no deck/dealing, no betting state machine, no pots/showdown, no chip state.

**Problem:** isolated reps don't test transfer. No continuity (stacks, position rotation), no
table dynamics (limpers, multiway, 3-bet wars), no multi-street consequences. The user wants
Practice-grade feedback *inside* a realistic full game.

**Why now:** the Professional Teacher Rework "Now" column is complete (N1–N9 all `[x]`); the
teaching layer exists to plug into. This initiative **supersedes** that roadmap's
"turn/river engine deferred" no-go — turn/river + multiway grading are pulled into scope
(gate decision, round 1 + 2).

## 2. Goal & non-goals

**Goal:** a "Simulate" tab where the user plays a persistent 9-max NLHE cash session against
8 persona bots calibrated to a live $2/$3 table, with every hero decision graded
Acceptable/Optimal/Blunder per street (preflop/flop/turn/river) against baseline strategy,
feeding the existing leak stats. Metric link (north-star: *winning $2/$3 player*): per-street
decision accuracy / EV-loss inside Simulate sessions; grading coverage of hero decisions
reaching ~complete once turn/river + multiway graders land.

**Non-goals / out of scope (v1):**
- 🚫 Exploit-/persona-aware grading (grade vs baseline only; exploit layer is a **Next**
  roadmap item — explicit gate decision).
- 🚫 SRS writes from Simulate (attempts recorded + tagged, but no review-queue items).
- 🚫 Hidden-persona mode / read-tagging UI (persona badges visible in v1).
- 🚫 Selectable table textures (live $2/$3 calibration only).
- 🚫 Depth-aware persona ranges beyond SPR commit/fold logic (charts authored at 100BB).
- 🚫 Solver strategies, real-money anything, multiplayer, hand-history imports (global no-gos).
- 🚫 Tournament/SNG formats, straddles, antes, rake modeling.

## 3. Affected files / interfaces (patterns to mirror)

| Area | Files | Pattern to mirror |
|---|---|---|
| Game engine (new) | `backend/app/domain/table/` (deck, hand state machine, pots, showdown) | pure-domain like `domain/postflop.py`; purity test-enforced |
| Persona content (new) | `content/personas/*.json` + `content/schema/` | versioned packs like `content/preflop/*.json`; strategy in data, not code |
| Persona engine (new) | `backend/app/domain/personas.py` (or `table/bots.py`) | consumes content packs like `domain/content/` loaders |
| Turn/river graders | `backend/app/domain/postflop.py`, `providers/postflop.py`, `providers/composite.py`, `domain/srs.py` | hazards mapped in `contracts/postflop-turn-river.md` — street-aware dispatch, `faced_bet_bucket`, signature append-rules |
| Persistence (new tables) | `backend/app/models/`, `backend/alembic/versions/` | additive migrations; owner_id sentinel pattern from migration 0006 |
| API (new router) | `backend/app/api/v1/simulate.py`, `schemas/` | mirror `api/v1/drill.py` |
| Grading reuse | `backend/app/services/review.py` (`record_attempt`), `api/v1/drill.py` (grading orchestration), `domain/evaluation.py` — there is **no** `services/grading.py` | one async `StrategyProvider`; results freq+EV never boolean |
| FE tab | `frontend/src/App.tsx` (VIEWS + hash route), new `components/simulate/`, `api/types.ts` (hand-maintained), `styles/tokens.css` (values), `app.css` | hash routing from N6; tokens-only CSS; AA contrast both themes |

## 4. Requirements (atomic, testable)

**R1 — Deal & RNG.** As a player I get realistically random hands.
*AC:* per-hand `random.Random` seeded from `secrets.randbits(256)`; seed persisted on the hand
record; same seed ⇒ byte-identical deal (unit test); `shuffle()` used (no hand-rolled
Fisher-Yates, no sort-by-random); statistical suite (≥200k seeded deals) passes chi-square on
card-position uniformity and matches pocket-pair 5.88% / suited 23.53% within tolerance;
hole cards + full board dealt at hand creation, revealed street-by-street; no card repeats.

**R2 — Hand engine.** As a player I experience complete, correct NLHE hands.
*AC:* 9-max betting state machine with blinds, rotating button, limps/raises/3-bet/4-bet/
all-in; multiway side pots settle correctly (scripted scenario tests); showdown uses the hand
evaluator; **chip conservation** property test over randomized playouts (total chips constant);
hero's legal actions exposed as the same predetermined-sizing `LegalAction`/`Decision` shape
Practice uses (fold/check/call/bet/raise as legal — no free-form sizing).

**R3 — Personas.** As a player I face 8 distinct-feeling, realistic opponents.
*AC:* 6 persona packs (passive fish, calling station, nit, TAG, LAG, maniac) as versioned
JSON validating against a new schema; seats filled by doubling passive fish + TAG; preflop =
per-position weighted ranges (action = categorical sample); postflop = strength-bucket + draw
category → frequency vector shaped by persona levers (aggression, stickiness, bluff_freq,
sizing distributions, SPR commit threshold, multiway bluff dampener); **closed-loop stat
test:** ≥10k simulated hands per persona yields VPIP/PFR/3-bet/AF/WTSD inside the §8 bands;
actions are frequency-mixed (no deterministic strength→action or strength→size mapping).

**R4 — Table texture.** As a player the table plays like live $2/$3.
*AC:* full-table simulation (≥10k hands) shows avg players-to-flop ≈ 3–4, majority of hands
with ≥1 limper, 3-bet pots low single-digit % and premium-weighted; iso-raise sizing ≈
4BB + 1BB/limper; stakes expressed in BB.

**R5 — Session & chips.** As a player my table persists like a real online session.
*AC:* stacks carry over across hands within a session; bust ⇒ auto-rebuy to 100BB next hand
(hero and bots); ledger shows per-player net BB (buy-ins vs current stack); session persists
in SQLite (Alembic migration, additive, owner_id-sentinel pattern) and survives app reload;
"Leave table" ends the session; new session reseats/reshuffles personas.

**R6 — Grading & tracking.** As a learner every decision is judged and tracked per street.
*AC:* each hero decision maps to a `Spot` and grades through the existing `StrategyProvider`
stack (baseline ranges — never persona-aware in v1); verdicts use the existing `Correctness`
enum; decisions that map to no supported grader node are stored and shown "no baseline yet"
(never guessed); attempts recorded in the existing attempt table **tagged `source=simulate`**
so leak stats include them — `drill_attempt` has no `source` column today, so an **additive
Alembic migration adds it (default `'practice'`)**; **no SRS item writes**; at ship,
turn/river + multiway graders cover those streets (roadmap slices S5–S8).

**R7 — Feedback UX.** As a learner I get feedback without losing immersion.
*AC:* during the hand each hero decision shows only a small color badge (verdict tier), no
text, no pause; at hand end a recap panel lists per-street decisions with verdict, freq/EV
(labeled *approximate*), and tiered "why" (existing composer) expanded for mistakes/blunders;
recap dismissible to deal next hand.

**R8 — Pacing.** As a player the action is followable but never tedious.
*AC:* bot actions play with short randomized delays (~0.5–1.5s); speed setting
(normal/fast/instant); after hero folds, the hand resolves instantly and the result lands in
the ledger; next hand deals without manual confirmation (configurable).

**R9 — Tab & design.** As a user Simulate is a first-class view.
*AC:* "Simulate" in `VIEWS` with hash route `#/simulate`; reload restores the live session
view; persona badge on each seat; all CSS via design tokens; AA contrast + visible focus both
themes; `design-reviewer` pass on the table UI.

## 5. Constraints (3-tier)

✅ **Always:** domain purity (`app/domain/` no web/DB imports); results freq+EV never boolean;
grading behind the one async `StrategyProvider`; strategy + personas in versioned `content/`;
EVs labeled approximate; tokens-only CSS + AA contrast; every schema change ships an additive
Alembic migration; per-hand isolated RNG instance, seed persisted; frequency-mixed bot
decisions; manual `types.ts` maintenance for API changes.

⚠️ **Ask-first:** any `StrategyProvider` interface change; any change to `spot_signature()`
inputs or any new signature bucket dimension (append conditionally for turn/river only — see
contract map); any migration rewriting existing rows; new top-level dependency (incl. any FE
animation lib); grading multiway/off-depth spots with heads-up/100BB logic under a caveat
label.

🚫 **Never:** silently grade an unmapped spot; deterministic persona strength→action or
strength→size mapping (documented sizing-tell pitfall); global/shared RNG state across hands;
break the preflop signature branch (byte-locked); SRS writes from Simulate in v1; push to
`main` / force-push / merge without confirmation.

## 6. Milestones

Map 1:1 to roadmap slices S1–S11 (`docs/ai-dlc/roadmap/simulate-table.md`) — objective,
output, done-check live there. Parallel-track plan (disjoint file ownership for parallel
agents) also lives there.

## 7. Verification (end-to-end)

`./scripts/verify.sh` → `BACKEND VERIFY OK` (includes new engine/persona/grader/stat tests) ·
`cd backend && ruff check .` · `cd frontend && npm run typecheck && npm run build` · manual
probe: `./scripts/serve.sh start`, open `#/simulate`, play a hand through showdown, fold a
hand, reload mid-session (state restored), leave table. "Done" = all R1–R9 acceptance
criteria pass, commands exit clean, nothing outside the named areas changed.

## 8. Research grounding (2026-07-09 agent reports)

**RNG (decided):** Fisher-Yates via Python's `random.Random.shuffle` (correct, unbiased
`_randbelow` rejection sampling); seed minted per hand from `secrets.randbits(256)` (≥226 bits
so all 52! decks reachable — the Planet Poker/ASF failure was a 32-bit clock seed); CSPRNG-only
dealing rejected (kills replay, no adversary locally); burn cards computationally irrelevant;
board predetermined at deal = statistically identical to street-by-street. Validation: card ×
position chi-square + known hand-frequency anchors.

**Persona stat bands (validation targets, 9-max live low stakes):**

| Persona | VPIP | PFR | 3-bet % | AF | Fold-to-cbet | WTSD |
|---|---|---|---|---|---|---|
| Passive fish | 28–45 | 3–9 | 0–2 | <1.5 | <45 | 30–35 |
| Calling station | 40–60 | <8 | ~0–1 | <1 | <35 | 35–45 |
| Nit | 7–14 | 2–9 | 1–2 | 1–2 | 55–70 | 20–24 |
| TAG | 15–20 | 12–17 | 6–7 | ~3 | 45–55 | 25–27 |
| LAG | 24–36 | 18–24 | 8–12 | 3–4.5 | 35–45 | 27–30 |
| Maniac | 45–60+ | 30–40 | 12–20 | 5+ | <35 | 28–35 |

(Station/maniac AF/WTSD bands extrapolated from source thresholds; treat as targets, tune in
the closed-loop test.)

**Design references:** GTO Wizard AI profiles — persona = *global* per-action incentive
biases, applied everywhere in the tree ("you exploit players, not one decision point");
Loki/Poki — EHS = HS + (1−HS)·PPOT with probabilistic bet/semi-bluff triggers (the postflop
bot template); APT — the cautionary tale (sizing tells, degenerate ranges).

**Live-texture anchors:** ~92% multiway after a limp (PokerNews $1/$2 analysis); population
3-bet ≈ 1–3%, premium-weighted (Ed Miller); realistic lineup ≈ 1 nit, 1–2 TAGs, 3–4
loose-passives, 1 station, 0–1 LAG/maniac; iso-sizing 4BB + 1BB/limper.

**Pitfalls to test against:** sizing tells (decouple size from strength); never-bluffing bots
(even stations keep nonzero bluff freq); archetype drift (closed-loop stat verification);
deterministic play → memorizable lines (mix + small per-session frequency noise, ±10–15%
relative); stack-depth blowups (SPR-gated commit logic).
