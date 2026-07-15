# Simulate (persona table) — Roadmap (created 2026-07-10)

> Living, pass/fail, resumable. A fresh context should read this and know exactly what's left.
> PRD: `docs/ai-dlc/prd/simulate-table.md` (incl. research grounding + persona stat bands).
> Contract map for the grader work: `docs/ai-dlc/contracts/postflop-turn-river.md`.
>
> **Supersedes one no-go** in `roadmap/professional-teacher-rework.md`: the turn/river engine
> (and multiway grading) are **pulled into scope** here — gate decision 2026-07-09. That
> roadmap's Later bets 2f–2j are realized as slices S5–S8 below.
>
> **Gate decisions (2026-07-09/10):** turn/river graders before ship · carry-over stacks,
> persistent session, auto-rebuy · badge + end-of-hand recap · baseline grading (exploit layer
> = Next) · 6 personas, fish+TAG doubled · unmapped spots shown "no baseline yet" until S8 ·
> attempts tagged `source=simulate`, no SRS v1 · live $2/$3 texture · short delays +
> skip-on-fold · visible persona badges · parallel tracks, grading wires in as it lands.
>
> **Resume rule:** work waves in order; within a wave, slices run in PARALLEL (disjoint file
> ownership — see track plan); verify a slice's pass/fail actually passes before `[x]`
> (agents falsely mark work done). Hand ONE slice at a time to `/ai-dlc`.
>
> **Staleness warning (refuter, 2026-07-10):** `contracts/postflop-turn-river.md` predates
> commit `53c865c` (Phase 2e-0/2e-1), which already fixed hazards 1-of-3 it lists:
> `supports()` now street-gates to FLOP (turn/river ⇒ `Coverage.NOT_FOUND`),
> `faced_bet_bucket()` reads the current decision point, `_hand_category()` orders made
> hands before draw flags. Still LIVE from that map: `range_advantage()`'s dead
> `node_context` param (→ S6) and `_rebuild_postflop()`'s silent random fallback for unknown
> node contexts (→ S6/S7). Re-verify against HEAD before speccing any C-track slice.

---

## North-star outcome — the WHY

- **Primary (unchanged):** *become a winning $2/$3 player.* Simulate adds the **transfer
  layer**: decisions graded under real-game conditions (continuity, multiway dynamics,
  multi-street consequences).
  Metric: **per-street decision accuracy / EV-loss under game conditions** (leak stats
  already aggregate attempts; `source=simulate` tag isolates them).
  Baseline: **0% of decisions are graded under game conditions** (no full-game surface;
  turn/river decisions ungradeable anywhere) → Target: **≥90% of hero decisions in a
  Simulate session graded** (coverage — the rest honestly "no baseline yet") **and a
  measurable per-street accuracy trend across sessions**, with turn/river accuracy visible
  for the first time. The playable persistent table is the *output* that makes this
  measurable, not the outcome itself.

## Parallel-track plan (how agents fan out)

| Track | Slices | Owns (no other track touches) |
|---|---|---|
| A — Game engine | S1 (domain half), S2 | `backend/app/domain/table/` (new) |
| B — Personas | S3, S4 | `content/personas/`, `content/schema/persona*`, `backend/app/domain/personas.py` (new) |
| C — Turn/river graders | S5, S6, S7 | `domain/postflop.py`, `domain/providers/*`, `domain/srs.py` (postflop branch), `api/v1/drill.py` (`_rebuild_postflop`), grader tests |
| D — Multiway grading | S8 | same files as C ⇒ **runs after C, never alongside** |
| E — Session/UI/grading-wire | S1 (tab+API half), S9, S10, S11 | `api/v1/simulate.py`, models+migrations, `frontend/src/*`, `services/` |

Waves: **W1** S1‖S3‖S5 → **W2** S2‖S6 → **W3** S4‖S7 → **W4** S9‖S8 → **W5** S10 → **W6** S11.
(S4 must FOLLOW S2, not run beside it — its closed-loop tests need the finished hand engine.
S9 must follow S4 for the same reason. S8 shares C-track files, so it runs only after S7.)
Maker ≠ checker: every slice gets a `refuter` pass; UI slices also get `design-reviewer`.
`App.tsx`, `types.ts`, `app.css` are single-owner-per-wave: S1 in W1, then E-track slices —
never two slices touching them in the same wave. Attempt recording lives in
`services/review.py` (`record_attempt`) + `api/v1/drill.py` (grading orchestration) — there
is **no** `services/grading.py`. `backend/tests/test_domain_purity.py` has a hardcoded module
allowlist: S1/S2 add `app.domain.table.*` and S3 adds `app.domain.personas` to it, else the
purity invariant silently skips the new code.

### Agent fan-out plan (approved 2026-07-10; concurrency cap 15, never binding)

Rhythm per wave: lead commits shared contracts FIRST (API shapes, JSON schemas, module
interfaces) → makers fan out in parallel (disjoint files) → fan-in barrier: `verify.sh` + FE
build + one fresh `refuter` per slice (+ `design-reviewer` on UI slices) → merge → next wave.
Lead does all merging/synthesis; sub-agents never spawn sub-agents. Workers stay in the main
tree (gitignored `.venv`/`node_modules` rule out worktrees) ⇒ one-file-one-owner is hard law.
Lead specs the NEXT wave's slices via `/ai-dlc` while the current wave's makers run.

| Wave | Makers (agent → owns) |
|---|---|
| W1 | S1: impl → `domain/table/deck.py`+tests+purity entry · impl → `api/v1/simulate.py`+schemas · ux-ui → `App.tsx`/`hashRoute`/`components/simulate/`/`types.ts` ▪ S3: heavy → persona schema+`domain/personas.py`+stat test · impl → packs fish/station/nit · impl → packs TAG/LAG/maniac ▪ S5: heavy → golden tests+routing seams |
| W2 | S2: heavy → `domain/table/engine.py` (state machine+side pots, one owner — interlocked) · impl → test battery (chip-conservation, side-pot scenarios, 200k-deal RNG suite) ▪ S6: heavy → turn graders+`range_advantage` rewrite+content · impl → `_rebuild_postflop` branches+SRS tests · impl → leak buckets+feedback wiring |
| W3 | S4: heavy → postflop persona engine · impl → pack postflop params · impl → calibration suite (stat bands+table texture) ▪ S7: heavy → river graders+content · impl → drill.py river branches+tests |
| W4 | S9: impl → models+migration+session service (sole Alembic owner) · impl → session/play endpoints · ux-ui → playable table UI ▪ S8: heavy → multiway adjustments (sole C-track-file owner) · impl → direction-assertion tests |
| W5 | S10: impl → grading wire+`source` migration+tagged `record_attempt` · ux-ui → badge+recap panel · impl → no-SRS/tag-visibility tests |
| W6 | S11: impl → pacing+speed setting · impl → tokens/polish pass |

Peak ≈ 7 makers (W1). Spare headroom goes to CHECKERS, not makers: refuter/design-reviewer
panels (2–3 lenses per slice) run concurrently at each fan-in. Ceilings are file ownership +
the serial spine S2→S4→S9→S10, not the agent budget.

## NOW — spec-ready vertical slices (ICE = Impact·Confidence·Ease, 1–10)

- [x] **S1 — Table walking skeleton: deal a real hand on a Simulate tab.** *(done 2026-07-10, PR #27: domain/table deck + rotation, /simulate endpoints w/ hero-only wire + 404 precedent, Simulate tab via synthetic-Spot adapter over PokerTable; 277 tests + verify.sh green; refuter pass; design-review pass after 2 fixes. Carry-forward notes: StrictMode dev double-session (benign), leak test is key-name-based; "you are to act" now conditional on legal_actions + deal bar moved under the felt (a2ab3c9, post-review UX pass); "Pot 0bb" w/o posted blinds → resolves in S2)* ICE 8·9·7. *(Track A+E seed, W1)*
      **Problem:** no game surface exists at all. **Outcome-link:** transfer layer exists end-to-end.
      **Solution:** pure-domain `Deck` (`random.Random.shuffle`, per-hand seed from
      `secrets.randbits(256)`, hole cards + full board dealt upfront); minimal
      `POST /simulate/session` + `POST .../hand`; "Simulate" in `VIEWS` at `#/simulate`
      rendering 9 seats, hero cards, button rotating hand-to-hand. No betting yet.
      **Pass/fail:** fixed seed ⇒ byte-identical deal (test); 52 unique cards, no repeats;
      `app.domain.table` added to the purity-test allowlist and green; `#/simulate` deals +
      shows a hand, next-hand rotates button; `verify.sh` + FE build green.
      **Appetite:** ~1 small epic. **No-gos:** no betting/chips/personas; no persistence beyond
      in-memory session + logged seed; no hand-rolled shuffle; heavy RNG statistical suite is
      S2's, not here (keep the skeleton thin).

- [x] **S2 — Hand engine: betting, side pots, showdown, chip conservation.** *(done 2026-07-10, wave 2: `domain/table/engine.py` — 4 legal-action shapes incl. BB-option + no-reopen, incomplete-raise increment rule, side pots w/ dead money, best7 showdown, deltas sum exactly 0.0 by construction; 407-line scripted+property battery; RNG suite 200k shuffles χ² GOF < 1057 @ 2.1s unmarked; refuter-probed live for BB option/reopen/layering)* ICE 9·7·4. *(Track A, W2)*
      **Problem:** no betting state machine; full hands can't play out.
      **Outcome-link:** correct game = precondition for every graded decision.
      **Solution:** 9-max state machine in `domain/table/` — blinds, limps, raise/3-bet/4-bet,
      all-ins, multiway side pots, showdown via existing evaluator; legal actions surfaced in
      Practice's predetermined-sizing `LegalAction`/`Decision` shape; RNG statistical
      validation suite (deferred from S1).
      **Pass/fail:** scripted side-pot scenarios settle exactly; chip-conservation property
      test over randomized playouts; illegal actions rejected; RNG suite green (≥200k seeded
      deals: card×position chi-square, pocket-pair 5.88% / suited 23.53% ±tolerance);
      domain-purity test still green; `verify.sh` OK.
      **Appetite:** ~1 epic. **No-gos:** no straddles/antes/rake; no UI here;
      no persona logic (random-policy playouts suffice for tests).

- [x] **S3 — Persona packs + preflop bot play.** *(done 2026-07-10, wave-1b: PersonaPack models + pure-domain sampling engine; 6 band-tuned packs; VillainType += tag/maniac w/ EXPLOIT_ARCHETYPES decoupling + leak cats 304/305; closed-loop proxy-band test 19/19, 0.4s unmarked; refuter pass)* ICE 9·7·5. *(Track B, W1)*
      **Problem:** archetypes are hero-exploit hints, not acting opponents; TAG + maniac
      don't exist. **Outcome-link:** the "special sauce" — seats that play like people.
      **Solution:** persona JSON schema + 6 packs (fish, station, nit, TAG, LAG, maniac) with
      per-position weighted preflop ranges (RFI/limp/call/3-bet/4-bet/fold); sampling engine
      in `domain/personas.py` (categorical draw per combo — mixed, never deterministic);
      `VillainType` gains TAG + maniac.
      **Pass/fail:** packs validate against schema; closed-loop test — ≥10k simulated preflop
      hands per persona lands VPIP/PFR/3-bet inside the PRD §8 bands; same seed ⇒ same
      actions; `verify.sh` OK. **Appetite:** ~1 epic. **No-gos:** postflop behavior (S4);
      no depth-aware charts (100BB authoring); no persona-aware *grading* anywhere.

- [x] **S4 — Persona postflop engine + live-texture calibration.** *(done 2026-07-10, wave 3: `personas_postflop.py` — 7-rung analytic ladder + lever-block engine (levers in packs, mechanics in code); closed-loop full-hand suite N≈600/persona at 11.6s; honest PRD±3σ bands — AF + fold-to-cbet all pass after a refuter-driven merit rebalance + exact current_bet_to raise formula. **Two documented deviations:** table-texture players-to-flop floor 3.0→2.4 (VPIP-sum bound — a maniac-bearing lineup structurally kills passive limped multiway pots) and WTSD for 5/6 personas uses ENGINE-ANCHORED regression bands + cross-persona ordering invariants, not PRD tracker anchors (per-seat levers provably can't steer this population statistic — lever sweeps moved it <0.05 while breaking AF; PRD-fidelity revisit = Later item alongside engine perf: apply() is 91% pydantic deep-copy, ~430 hands/s ceiling))* ICE 9·6·3. *(Track B, W3)*
      **Problem:** bots must act on flop/turn/river or no hand reaches showdown.
      **Outcome-link:** realistic multi-street trees (the raise/3-bet/barrel situations asked for).
      **Solution:** strength-bucket (7-rung ladder + draw category, Loki-style EHS) →
      frequency vector shaped by persona levers (aggression, stickiness, bluff_freq, sizing
      distributions, SPR commit threshold, multiway bluff dampener) from the packs; small
      per-session frequency noise (±10–15% relative).
      **Pass/fail:** closed-loop full-hand sim per persona hits AF/fold-to-cbet/WTSD bands;
      **table-texture test** — 9-max lineup over ≥10k hands: avg players-to-flop ≈ 3–4,
      majority of hands ≥1 limper, 3-bet pots low single-digit %; no deterministic
      strength→size mapping (test samples sizes across strength); `verify.sh` OK.
      **Appetite:** ~1 large epic. **No-gos:** no solver lookups; no persona learning/tilt;
      tuning stays in content data, not code constants.

- [x] **S5 — Turn/river routing seams + residual hazard closure.** *(done 2026-07-10, wave-1b: pinned-hash tripwires + turn/river signature fixtures; flop-only grader guards; street-keyed dispatch map; append-rule docstring; zero behavior change — provider tests byte-identical; LIVE record_attempt truncation gap documented → S6; refuter pass)* ICE 6·8·7. *(Track C, W1)*
      **Problem:** the worst hazards (silent flop-truncation of turn/river spots) were already
      fixed in commit `53c865c` — `supports()` street-gates to FLOP, `faced_bet_bucket()`
      reads the current decision point (see staleness warning above). What REMAINS: no
      dispatch seam exists for TURN/RIVER providers; residual `board[:3]` truncation sites
      outside the provider path need an audit against HEAD; signature append-rules for new
      turn/river bucket dims are unwritten; no golden test pins today's turn/river ⇒
      `NOT_FOUND` behavior against regression.
      **Outcome-link:** prerequisite for honest per-street grading (S6/S7 plug into these seams).
      **Solution:** golden tests locking (a) flop signatures byte-stable and (b) turn/river
      spots ⇒ `Coverage.NOT_FOUND` until real graders land; provider dispatch seam for
      street-specific providers in `CompositeProvider`; audit + fix any remaining `board[:3]`
      truncation call sites (`srs.py`, `services/review.py`, `api/v1/drill.py` `_key`
      closure) at HEAD; document the conditional-append rule for new signature dims
      (turn/river only — preflop branch byte-locked).
      **Pass/fail:** golden tests exist and pass; a TURN spot routed today returns
      `NOT_FOUND` (never a flop-graded verdict); truncation audit findings fixed or
      explicitly cleared in the slice notes; full pytest + `verify.sh` green.
      **Appetite:** ~1 small epic (shrunk — much already landed in `53c865c`).
      **No-gos:** no new grading logic here; no `spot_signature()` preflop changes;
      `range_advantage`/`_rebuild_postflop` rework belongs to S6, not here.

- [x] **S6 — Turn graders: barrel + facing turn bets.** *(done 2026-07-10, wave 2: TURN_BARREL/VS_TURN_BET graders + TurnHeuristicProvider in `_by_street[TURN]`; `range_advantage` consumes node_context (flop path verbatim, byte-identical); NOT_FOUND coverage gate closes the live persist gap; SRS turn_class CONDITIONALLY appended (refuter caught constant-append breaking the pin — element omitted for flop) + nullable column + migration 0007; rebuild matches 4-tuple incl. turn_class; leaks 203/204, TAXONOMY_VERSION 4; pins 6832…/0cdf… unchanged as literals; combined refuter caught + fixed a PYTHONHASHSEED flake via sorted combo iteration)* ICE 8·6·4. *(Track C, W2 — after S5)*
      **Problem:** no turn grading (old 2f/2g). **Outcome-link:** per-street tracking, street 3.
      **Solution:** heads-up turn aggressor (2nd-barrel: scare-card / picked-up-equity /
      capped-range per research §5.1–5.2) + facing-turn-bet graders behind `StrategyProvider`;
      **rewrite `range_advantage()` to actually consume its `node_context` param** (dead
      today — contract-map hazard 4, still live at HEAD; barrel logic needs it); strategy
      thresholds in `content/postflop/` packs; tiered feedback inherited via the composer;
      new leak buckets; **explicit `_rebuild_postflop` branches for the new turn node
      contexts** (else Practice SRS review silently degrades to random — hazard 6);
      **coverage-gate `record_attempt`/`spot_signature` in `grade_drill`** (S5 audit found a
      LIVE gap: a client-supplied turn/river spot persists a truncated-texture SRS row today
      despite NOT_FOUND — see `contracts/simulate-s5.md` item 4).
      **Pass/fail:** turn spots return freq+EV verdicts (never boolean) with non-tautological
      reasoning; `range_advantage` behavior differs by node context (test); SRS review of a
      due turn spot rebuilds that spot, not a random one (test); signature golden tests prove
      flop signatures untouched; `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** multiway (S8); river (S7); no Practice drill
      mode here (Next); EVs labeled approximate.

- [x] **S7 — River graders: value/bluff + facing river bets.** *(done 2026-07-10, wave 3: RIVER_BARREL/VS_RIVER_BET graders + RiverHeuristicProvider (4th `_by_street` slot); busted-draw demotion (draw→air on river — refuter-confirmed `_hand_category` overvalued busted draws at the 1.2 tier); river_card_class + second conditional SRS append + `river_class` column (migration 0008) + separate `_RIVER_CTX` rebuild branch matching all 5 archetype fields; feedback names BOTH turn and river cards (6-wide tags); leaks 205/206, TAXONOMY_VERSION 5; pins unchanged + new turn-hash pin independently re-derived; 4-flush/4-straight 5-card regression fixtures. **Per-street grading now covers all 4 streets.**)* ICE 8·6·4. *(Track C, W3 — after S6)*
      **Problem:** no river grading (old 2h/2i). (Note: the made-hand-vs-draw conflation the
      contract map flagged was already fixed in `53c865c` — made straights/flushes now
      categorize before draw flags; do NOT re-diagnose it.)
      **Outcome-link:** per-street tracking, street 4.
      **Solution:** river value-bet/bluff + bluff-catch graders (pot-odds vs bluff-frequency
      heuristics) behind `StrategyProvider`; content-pack thresholds; leak buckets;
      `_rebuild_postflop` branches for the new river node contexts (same SRS-degradation
      hazard as S6).
      **Pass/fail:** river spots return freq+EV verdicts with authored reasoning; SRS review
      of a due river spot rebuilds that spot, not a random one (test); river categorization
      spot-checked on 4-flush/4-straight boards (regression guard, not a fix); `verify.sh`
      green.
      **Appetite:** ~1 large epic. **No-gos:** multiway (S8); no solver EVs; approximate labels.

- [x] **S8 — Multiway grading extension.** *(done 2026-07-11, wave 4: binary HU/multiway via `players_in_pot()`/`is_multiway()` derived from PlayerState liveness — NO `Spot` field. `_apply_multiway` merit scaling (`_MW_BLUFF_DAMPEN=0.6`/`_MW_VALUE_LEAN=1.15`/`_MW_CATCH_TIGHTEN=1.3`) inside all 7 graders behind the `is_multiway` gate — aggressor dampens bluff-candidate merit, facing tightens **weak_made** bluff-catch (NOT air — air folds anyway; maker overrode the brief's `cat=="air"` per the spec's "marginal catchers"; combined-refuter verified ~1700 weak_made samples 100% tighter MW, 0% looser). Third conditional `"mw"` signature append after river_class (flop 9/10, turn 10/11, river 11/12); pins 6832…/0cdf…/9c1a… byte-identical (recomputed); scales only positive merits; graders read no persona data. **Scope property:** MW spots never persist in v1 (Practice HU-only + no Simulate SRS) ⇒ NO migration/model/rebuild/leak change, `TAXONOMY_VERSION` stays 5. Direction tests non-tautological (fail under no-op dampen). Combined-refuter PASS.)* ICE 7·5·3. *(Track D, W4)*
      **Problem:** live-texture tables are multiway-heavy; HU graders would mis-teach
      (bluff frequencies collapse multiway). **Outcome-link:** grading coverage where the sim
      actually lives. **Solution:** multiway adjustments (player-count-aware c-bet/barrel/
      bluff-catch thresholds — value-lean, bluff-dampened) across flop/turn/river graders;
      spots carry player count; signature dim appended conditionally (never mutates existing
      HU signatures).
      **Pass/fail:** a 3-way c-bet spot grades differently from HU (tests assert direction:
      fewer acceptable bluffs); HU golden signatures unchanged; `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** no exotic nodes (squeeze-pot postflop trees
      beyond player count); if a spot still doesn't map, it stays "no baseline yet" — never
      silently HU-graded.

- [x] **S9 — Hero plays: session persistence, stacks, ledger.** *(done 2026-07-11, wave 4: playable/persistent Simulate — `domain/table/play.py` (bot-driving loop mirroring the S4 `test_personas_postflop` harness PER-DECISION, stops at `hero_seat`; purity-allowlisted) + `sim_session`/`sim_seat`/`sim_hand` tables (migration 0009; rng_seed str, state_json text, SimSeat composite PK, owner_id '' sentinel) + `services/sim_session.py`. **FULL mid-hand restore** (persist live HandState JSON at every hero-boundary/hand-over — bots resolve atomically per request ⇒ no mid-bot checkpoints; rehydrate → exact decision point). Carry-over stacks + auto-rebuy (stack<1.0→100, `buyins+=100−stack`, 2dp) + net-BB ledger. Bot-action RNG = fresh `secrets.randbits(256)` per `advance_to_hero` (deal reproducible from rng_seed; full-hand bot replay = Later item). Hero-only wire privacy structural (SeatView + showdown-only reveals — refuter: 5 hands, zero leak). FE "Midnight Club rail sheet" table (SimTable/ActionBar/Ledger/EventLog/Showdown) + localStorage restore + 404 recovery. **sim_decision DEFERRED to S10** (interview). Fixes folded: SimTable wire-status case (lowercase enum), 404 seam (`SessionNotFound`), carry-over test assertion, badge/leave/puck polish. Design-review: desktop+tablet premium/ship (AA both themes, focus, privacy verified); **mobile 375px deferred → NEXT** (felt collapse + pre-existing shared-masthead scroll). 427 backend tests + verify.sh + FE typecheck/build green.)* ICE 9·7·4. *(Track E, W4)*
      **Problem:** engine + bots exist but the user can't sit down; nothing survives reload.
      **Outcome-link:** the actual product surface.
      **Solution:** hero seat + action buttons (Practice's decision component pattern);
      carry-over stacks, auto-rebuy to 100BB on bust (hero + bots), per-player net-BB ledger;
      new tables (`sim_session`, `sim_hand` w/ rng_seed, `sim_decision`) via additive Alembic
      migration (owner_id-sentinel pattern from 0006); reload restores the live session;
      "Leave table" closes it; persona badges on seats.
      **Pass/fail:** play a hand to showdown in the browser; fold mid-hand; reload mid-session
      restores state; bust triggers rebuy + ledger reflects buy-ins; migration up/down clean;
      `verify.sh` + typecheck/build green. **Appetite:** ~1 large epic.
      **No-gos:** no grading yet (S10); no pacing polish (S11); no multi-session tables list.

- [x] **S9b — Table size + crowding fix.** *(done 2026-07-12, wave 4.5 — user-reported: felt starved at ~640px on 1440px screens, board cards overlapped HJ/CO pods. Simulate route alone widens to `--content-width-wide` 1360px via `.app:has(.simulate)`; sim ring caps 5×card-h with a 4× re-cap inside the existing `@media (max-height:920px)` density gate (refuter caught the specificity beating the gate); SimTable slotStyle top-half y-radius 38→41 (bottom stays 38 — hero pod otherwise clipped `.stage overflow:hidden`); sim-layout single-column gate raised 900→1100px so ≤1100px drops the rail sheet below the felt instead of starving the ring. Playwright bounding-box sweep: zero overlaps + zero stage-clipping at 1440×900/1280×800/1024×768; Practice/Quiz shells verified untouched at 1080px. Spec/contracts/tickets: `simulate-table-size.md`.)* *(Track E, W4.5 — between S9 and S10)*

- [x] **S10 — Grading wired in: live badge + end-of-hand recap + tagged attempts.** *(done 2026-07-12, wave 5: `grade_map.map_decision_point` — preflop RFI/vs-RFI/blind-defense via the SAME `scenarios.build_spot` Practice uses + HU flop c-bet mirroring `build_cbet_spot`; open-size band [2.0..canonical] per W1-refuter adjudication (bots min-raise — strict gate made facing-a-raise ungradeable); None ⇒ honest "no baseline yet", NO drill_attempt. Async `apply_hero_action` grades the pre-`apply()` state via the drill provider singleton, writes ride the single commit (illegal action ⇒ zero rows). `sim_decision` (migration 0010) + `DrillAttempt.source='simulate'` (marker sig `sim:ctx:pos`, never `spot_signature()`); stats.py NULL-tolerant source filter on all 5 Practice reads. FE: hero-pod side-flag badge (clip-rescued per final design review), SimRecap w/ live-tier accumulation (reload degrades to numbers-only — 0011 tracked in NEXT), SimStreetReport all-time panel + fold-path refetch fix (final-gate refuter high-1). 10 `--sim-tier-*` tokens. 472 backend tests; refuter PASS-w-issues all folded; design-review ship-with-nits, nit fixed + re-verified.)* ICE 10·7·4. *(Track E, W5)*
      **Problem:** the key value — Practice-grade verdicts inside the game — isn't wired.
      **Outcome-link:** primary metric becomes measurable in-sim.
      **Solution:** map each hero decision to a `Spot`, grade via the existing provider stack
      (baseline only), store verdicts on `sim_decision`; unmapped spots stored + shown
      "no baseline yet"; during hand: color badge per decision (verdict tier, no pause); hand
      end: per-street recap with freq/EV (≈ labels) + tiered "why" expanded for
      mistakes/blunders; attempts recorded tagged `source=simulate` — **`drill_attempt` has
      no `source` column today (verified), so this slice ships an additive Alembic migration
      adding it (default `'practice'`)** and threads it through `record_attempt` in
      `services/review.py` + stats reads; **no SRS writes**; PLUS *(scope add 2026-07-12,
      user vision)* a **minimal per-street report**: one aggregate endpoint over
      `sim_decision` (all-time, grouped by street: graded count, verdict-tier mix, EV-loss
      sum, no-baseline count) + a compact read-only panel in the Simulate view — numbers
      only, no charts.
      **Pass/fail:** a deliberately-bad preflop play shows a red badge + blunder recap with
      reasoning; unmapped spot renders "no baseline yet"; migration applies up/down clean and
      existing attempt rows read back unchanged; attempt rows carry the simulate tag and
      appear in stats; zero SRS rows created (test); per-street report shows the played
      decisions bucketed by street with rates that EXCLUDE no-baseline rows (shown as
      coverage count instead); `verify.sh` + build green.
      **Appetite:** ~1 epic (+ the small report stretch). **No-gos:** no exploit-aware
      verdicts; no SRS; no charts/winrate graphs/positional breakdowns (NEXT: session
      analytics).

- [x] **S11 — Pacing + table feel polish.** *(done 2026-07-12, wave 6: one `stagedIndex` drives log narration AND felt seat reveals (revealAt map — felt never leads the log, design-review frame-verified); SimSpeedPicker normal 0.5-1.5s random / fast ×0.4 / instant, localStorage, radio-group a11y; hero-fold skips playback → next hand; prefers-reduced-motion ⇒ instant. T5 polish: Night folded persona/stack 3.82→4.73:1 AA (sim-scoped rule, shared base untouched), fmtBb kills float smears at all bb sites, caption voice unified. Final design review: ship-with-nits — badge clip fixed (side-flag), mobile + nav-desync pre-existing/tracked.)* ICE 6·8·6. *(Track E, W6)*
      **Problem:** instant 8-bot action is unreadable; folded hands waste time.
      **Outcome-link:** "feels like a real game" — the premise.
      **Solution:** randomized bot delays (~0.5–1.5s) with normal/fast/instant setting;
      hero-fold ⇒ instant resolution into the ledger + auto-deal next; tokens-only styling
      pass; `design-reviewer` run on the table across themes/breakpoints.
      **Pass/fail:** speed setting observably changes pacing; fold skips ahead; design-review
      verdict acceptable (AA contrast + focus both themes); build green.
      **Appetite:** ~1 small epic. **No-gos:** no sound; no avatars/art beyond badges; no
      animation library without ask-first.

---

## NOW — Epic 2: Realism, Range Coverage & Coaching Depth (added 2026-07-14)

> Second epic on the shipped Simulate table. Same north-star (become a winning $2/$3
> player — deepen the *transfer layer*). Six user asks (2026-07-14 interview) →
> research-backed slices. **Interview decisions (locked):** bet sizes are **live $2/$3
> stakes-calibrated, persona-flavored, fixed** · Reveal = **two buttons** (last-in villains /
> all incl. folded) · hero sizing = **context-specific option pairs per node** (not one global
> rule) · postflop "ranges" = an **openable call/fold/raise chart for the current spot**
> (postflop analog of the preflop chart #36) · **three separate `/research` passes** (ranges,
> bet sizes, postflop ranges) · coaching gap = **spot-specificity + why-it's-wrong depth**
> (trend view stays lower priority).
>
> **Sequencing (user-approved):** R1 → R2 → R3 → R4 → R5 → R6, with the three research spikes
> (RES-A/B/C) front-loaded and running in parallel since each seeds a later slice. Research
> spikes are `/research` + `/deep-research` tasks whose OUTPUT is content-pack data + a
> decision doc — no app code. Each build slice consumes its spike's findings.
>
> **Cross-cutting hazards to inject into every Epic-2 slice brief:**
> - **Hero-only wire privacy (S9 invariant):** the client never has villain hole cards
>   pre-showdown. R1's Reveal needs a *server* endpoint returning the finished hand's cards.
> - **Hero-fold playout path** (PR #38 `domain/table/play.py` + FE staging): fold-path FE state
>   bugs recurred **three times** in waves 3-6 — always test the hero-fold branch first.
> - **Predetermined-sizing shape:** hero + bots use a fixed `LegalAction`/`Decision` sizing
>   today. R2/R3 change what those sizes ARE and add a hero *choice*; keep the frequency-
>   sampled anti-sizing-tell no-go (strength→size must stay non-deterministic for bots).
> - **`spot_signature()` preflop byte-lock:** R4 adds positions — new RFI rows must not mutate
>   existing signatures (append/extend content, don't renumber the preflop signature dims).
> - **Heuristic-only no-go:** all range/sizing/coaching content stays heuristic + research-
>   grounded (no solver tables); EVs stay labeled *approximate*.

### Research spikes (front-loaded, parallel — output = data + decision doc, no app code)

- [ ] **RES-A — Preflop range research: RFI-by-position + all node contexts, live $2/$3.**
      **Problem:** `content/preflop/rfi.json` (+ vs_rfi/vs_3bet/vs_4bet/blind_defense) covers
      UTG, LJ, HJ, CO, BTN, SB — the early seats between UTG and LJ (commonly **UTG+1/UTG+2**)
      have no ranges, and coverage of every node context for those seats is absent.
      **Outcome-link:** hero can't be graded / can't range-guess in spots the content doesn't
      cover. **Solution:** `/deep-research` live $2/$3 (≈100BB) opening + response ranges by
      seat; if literature is sparse, land the **CO→UTG monotonic-tightening heuristic** the
      user named, documented and defensible. Deliver a positions×node-context coverage matrix +
      proposed range strings. **Pass/fail:** a decision doc under `docs/ai-dlc/research/`
      lists, for each missing seat × node context, either a sourced range or an explicit
      heuristic-derived range with rationale; no app code touched. **Appetite:** ~1 research
      spike. **No-gos:** no content-file edits here (that's R4); no solver ranges.

- [ ] **RES-B — Bet-sizing research: realistic fixed $2/$3 sizes, persona-flavored.**
      **Problem:** bot/hero bet sizes are unrealistic (user-reported). **Outcome-link:** every
      graded decision happens at a realistic price. **Solution:** `/deep-research` live $2/$3
      standard sizings per node (open, 3-bet, 4-bet, c-bet, turn/river barrel, check-raise,
      facing-bet raises) AND how they skew by player type (maniac overbet, nit small/standard,
      TAG textbook). Confirm/refute the user's "sizes differ by level" intuition — resolved as
      **stakes-calibrated** ($2/$3), persona-flavored. Deliver a size table keyed by
      node × persona. **Pass/fail:** decision doc gives a defensible fixed size for every
      node × persona with sources or explicit heuristic; flags any node where hero should get
      TWO options (feeds R3). **Appetite:** ~1 research spike. **No-gos:** no code; sizes stay
      FIXED (no bet-size sliders); no per-hand randomization beyond the existing sampling.

- [ ] **RES-C — Postflop range research: call/fold/raise ranges by street & spot.**
      **Problem:** postflop has heuristic graders (S6/S7) but no openable *range* view — hero
      can't see "what should call/fold/raise here." **Outcome-link:** point-of-need postflop
      strategy = the deepest transfer gap. **Solution:** `/deep-research` postflop
      continuation/response ranges for the common Simulate node families (c-bet/vs-c-bet,
      turn barrel/vs, river value-bluff/vs) at live $2/$3, HU and multiway-aware; where solver
      literature is thin, a documented merit-bucket → action-frequency heuristic. Deliver a
      spot → {call/fold/raise range or category-frequency} spec. **Pass/fail:** decision doc
      covers each shipped postflop grader's node family with a range/frequency spec + honest
      "approximate" labeling and a stated representation (combo strings vs category weights);
      no app code. **Appetite:** ~1 large research spike. **No-gos:** no solver tables; no code;
      approximate labels mandatory.

### Build slices

- [x] **R1 — Reveal Hands: face-down playout + two reveal buttons.** *(done 2026-07-15,
      feat/reveal-hands-r1: face-down gate in `_view()` gated strictly on hero
      `PlayerStatus.FOLDED` at hand_over — a villain-only showdown after a hero fold no
      longer auto-reveals; `settle()` untouched so a genuine hero-in showdown is byte-stable.
      New `GET /simulate/{id}/reveal/{scope}` (scope last-in|all) sourced from
      `SimHand.state_json` — NO migration; last-in = non-hero IN/ALLIN seats, all = every
      non-hero dealt seat, hero always excluded. Capability seam = module constant
      `REVEAL_ENABLED` (global; a future hidden-persona mode flips it off). Watch-ON only (the
      face-down watch-and-guess loop only exists there). FE: two ghost buttons in SimShowdown
      beside "Deal next hand" (heroFolded-gated), reveal FLIPS THE FELT via SimTable
      `revealedBySeat`, state reset on the same hand-transition boundary as the range panel.
      8 new backend tests built from a crafted terminal HandState (bots use non-seeded RNG →
      can't reproduce hero-fold-then-villain-showdown by play); privacy sweep asserts zero
      non-hero cards on the wire for a hero-folded hand. refuter PASS (test-determinism +
      "mirror" wording + felt-flip decision folded in); design-review ship-with-nits — all 3
      folded: reveal-all felt collision fixed by matching cards to the 0.45 face-down
      footprint, Night ghost-border lifted to --muted for WCAG 1.4.11 3:1, empty-showdown copy
      softened when heroFolded. 532 backend tests + verify.sh + FE typecheck/build green.)*
      ICE 8·9·8.
      **Problem:** after hero folds (PR #38) the still-live villains play out **face-up**,
      destroying the range-guessing exercise the user learns from. **Outcome-link:** hero
      practices reading ranges as streets unfold — the core learning loop.
      **Solution:** villain hands stay **face-down** through any no-showdown resolution (fold
      wins included); the played-out action still advances so hero can watch and guess.
      Add **two buttons** beside "Deal Next Hand": **"Reveal Last-In"** (villains still live
      when the hand ended) and **"Reveal All"** (every villain dealt in, incl. early folders).
      Reveal fetches cards from a **new server endpoint** for the just-completed hand (client
      has no hole cards pre-reveal — S9 privacy invariant); showdown still auto-reveals as
      today. **Pass/fail:** fold as UTG → villains play out face-down; "Reveal Last-In" shows
      only end-of-hand live villains; "Reveal All" shows every dealt villain; a genuine
      showdown still auto-reveals; no villain hole card reaches the client until a reveal/
      showdown (privacy test — mirror S9's zero-leak sweep); hero-fold FE staging still lockstep
      (test that path first); `verify.sh` + typecheck/build green; design-review both themes.
      **Appetite:** ~1 small epic. **No-gos:** no auto-reveal on fold; no persona/read tagging
      (that's the NEXT hidden-persona bet); no change to showdown behavior. **Reveal must route
      through a server-side capability seam** (endpoint + a togglable flag), NOT an always-on
      client toggle — so the NEXT hidden-persona mode can withhold it later without a rewrite.

- [ ] **R2 — Realistic persona-flavored fixed bet sizes** *(consumes RES-B)*. ICE 8·7·5.
      **Problem:** unrealistic sizings make every price wrong. **Outcome-link:** decisions
      graded at real prices. **Solution:** replace predetermined bot/hero sizings with the
      RES-B size table — fixed, keyed by node, flavored per persona (levers in the persona
      packs, mechanics in code, per the S4 lever/code split). **Pass/fail:** bot open/3-bet/
      c-bet/barrel sizes match the researched table per persona (test asserts persona A sizes ≠
      persona B where research says so); sizes stay frequency-sampled where multiple are
      authored (no deterministic strength→size tell); chip-conservation + engine tests still
      green; `verify.sh` green. **Appetite:** ~1 epic. **No-gos:** no sliders; no rake/ante;
      hero *choice* is R3, not here — R2 keeps hero on a single predetermined size.

- [ ] **R3 — Hero bet-sizing feature: two context-specific options** *(consumes RES-B, after R2)*.
      ICE 8·7·5.
      **Problem:** hero can't choose a size — a real skill the trainer omits. **Outcome-link:**
      sizing decisions become gradeable. **Solution:** when hero bets/raises, surface **two
      size options chosen per node** (RES-B flags which two — e.g. vs a 3-bet: standard re-raise
      OR shove; c-bet: 1/3 OR 2/3), not one global rule. Grade the size choice against the
      node's baseline (extends S10 grade_map / grade coverage). **Pass/fail:** hero facing each
      supported node sees the two researched options; choosing gets a freq+EV verdict (approx);
      an unmapped node falls back to the single predetermined size + "no baseline yet"; illegal
      sizes rejected; `verify.sh` + build green; design-review the new action UI both themes.
      **Appetite:** ~1 epic. **No-gos:** no free-form slider; no more than two options; no
      solver EVs.

- [ ] **R4 — Preflop coverage: fill UTG+1/UTG+2 + all node contexts** *(consumes RES-A)*.
      ICE 8·8·6.
      **Problem:** early seats between UTG and LJ have no ranges → hero un-gradeable / no chart
      there. **Outcome-link:** ≥90% preflop-decision coverage (the north-star coverage metric).
      **Solution:** add the missing seats to `content/preflop/*.json` (rfi/vs_rfi/vs_3bet/
      vs_4bet/blind_defense) from RES-A; extend persona per-position ranges, the S10 grade_map,
      and the preflop chart (#36) to render them. Confirm the table engine's seat model exposes
      those positions (open question for /ai-dlc). **Pass/fail:** a hand where hero is UTG+1/
      UTG+2 gets a baseline verdict + a populated preflop chart (not "no chart yet"); existing
      preflop `spot_signature()` values byte-unchanged (golden test); persona VPIP/PFR bands
      still hold for the new seats; `verify.sh` + build green.
      **Blocker to resolve in RES-A / spec, before build:** confirm the table engine's seat
      model can cleanly expose UTG+1/UTG+2 — if positions are a fixed enum that doesn't, R4 is a
      bigger structural slice than ~1 epic and must be re-appetited (don't silently absorb it).
      **Appetite:** ~1 epic (contingent on the seat-model check). **No-gos:** no signature-dim
      renumbering; no postflop (R5); no persona-adjusted squares on the chart (baseline +
      exploit note only, per the shipped-chart no-go).

- [ ] **R5 — Postflop range chart: openable call/fold/raise ranges for the current spot**
      *(consumes RES-C)*. ICE 9·6·4.
      **Problem:** no point-of-need postflop range view. **Outcome-link:** the deepest transfer
      gap — postflop strategy at the moment of decision. **Solution:** an openable panel (the
      preflop chart's interaction pattern) showing the call/fold/raise range (or category-
      frequency, approx-labeled) for hero's **current** postflop spot, backed by RES-C content;
      widen postflop grading coverage to match. Point-of-need only (current spot) so it stays
      inside the no-browsable-lessons no-go. **Pass/fail:** on a supported flop/turn/river spot,
      the chart opens and shows a call/fold/raise breakdown with approximate labeling; an
      unmapped spot shows "no chart for this spot yet" (never fabricated); grading of that spot
      matches the chart's stance (consistency test); `verify.sh` + build green; design-review
      both themes. **Reconciliation rule (tie-breaker):** RES-C's researched range/frequency
      spec is the **single source of truth** — where it disagrees with the existing S6/S7
      postflop heuristic graders, R5 re-points the grader at the RES-C content (graders and
      chart read the same spec); a spot RES-C can't cover stays "no baseline yet" on BOTH — never
      loosen one side to fake agreement. **Appetite:** ~1 large epic. **No-gos:** no solver
      tables; no browsable library; approximate labels mandatory; multiway handled or honestly
      "no baseline yet".

- [ ] **R6 — Coaching: leak-by-spot analytics view** *(after R2/R4/R5)*. ICE 9·6·5.
      **Problem:** feedback isn't spot-specific — the user can't find leaks by spot / position /
      street (gap #1 the user named). **Outcome-link:** the primary metric becomes *actionable*,
      not just measurable. **Solution:** a **leak-by-spot analytics view** — one aggregate
      read-model over `sim_decision` (EV-loss / mistake-rate grouped by street × position ×
      node family), surfacing hero's worst spots ("you over-fold BB vs steals"). Extends the S10
      per-street report; reuses its NULL-tolerant source filter. **Pass/fail:** the view ranks
      hero's spots by leak severity with real `sim_decision` data (excludes no-baseline rows
      from rates, shows them as a coverage count); numbers reconcile with the S10 per-street
      report; `verify.sh` + build green; design-review both themes. **Appetite:** ~1 epic.
      **No-gos:** no exploit-/persona-aware verdicts (ask-first if folding in the NEXT exploit
      layer); no trend/progress graphs (user ranked trend lower — stays NEXT); no SRS writes;
      no new `sim_decision` columns (read-model only — schema unchanged).

- [ ] **R7 — Coaching: why-it's-wrong recap depth** *(after R6; consumes RES-A/B/C rationales)*.
      ICE 8·6·5.
      **Problem:** verdicts say good/bad but don't teach the concept or the fix (gap #2 the user
      named). **Outcome-link:** mistakes become learnable, not just flagged. **Solution:**
      richer per-decision "why" in the recap — concept + concrete fix, drawn from the RES-A/B/C
      rationales **already authored as structured content** (RES specs must emit rationale text
      in a programmatically consumable shape — an explicit input contract for this slice, not a
      late discovery). **Pass/fail:** a mistake/blunder recap gives a spot-specific reason + a
      fix, not a generic verdict; the "why" is generated **live per request only** (no reload-
      durable text) so no schema change is needed; `verify.sh` + build green; design-review both
      themes. **Appetite:** ~1 epic. **No-gos:** **no migration 0011 / no `verdict`/`reasoning`
      columns on `sim_decision`** — reload-durable reasoning stays the deferred NEXT bet
      (ask-first if it becomes a real ask); no exploit-aware "why"; no SRS.

## NEXT — validated problems / opportunities (not yet spec'd)

- **Exploit-aware grading layer.** *(gate-mandated follow-on)* *Evidence:* personas are
  deliberately exploitable; baseline verdicts occasionally bless exploitatively-wrong plays
  (e.g. bluffing the station). `content/preflop/exploit.json` + N-slice exploit rationales are
  the seed. *Candidate slices:* persona-conditioned verdict adjustments per node family;
  recap note ("baseline-fine, but vs a station…"). *Open questions:* dual-verdict UI vs
  single adjusted verdict; content authoring volume.
- **Turn/river teaching surface in Practice.** *Evidence:* teacher-roadmap mandate — a street
  ships *with* teaching; S6/S7 add graders + tiered feedback but no drill modes/concept cards.
  *Candidate slices:* turn/river drill modes; concept cards for barrel/bluff-catch families.
  *(Partly realized by Epic-2 **R5** — the openable postflop range chart — inside Simulate;
  the Practice drill-mode + concept-card surface remains NEXT.)*
- **SRS integration for Simulate spots.** *Evidence:* sim blunders are exactly the reps worth
  scheduling; held out of v1 to protect the queue from off-depth/multiway noise.
  *Open questions:* which sim spots are signature-clean enough to seed; depth filter.
- **Hand replayer.** *Evidence:* per-hand persisted seeds make exact replay nearly free;
  recap covers only the freshest hand. *Candidate slices:* session hand list → step-through
  replay with verdicts.
- **Hidden-persona mode + read tagging.** *Evidence:* gate decision — visible badges v1,
  read-development later. *Open questions:* does tagging need showdown-history support.
  *(Epic-2 **R1**'s reveal buttons are a training wheel this mode would eventually gate —
  keep R1's reveal server-side + on-demand so hidden-persona mode can withhold it later.)*
- **Session analytics view (per-street decision quality).** *(promoted from Later
  2026-07-12 — explicit user vision: "track my decisions at each street, then show me
  analytics on whether I made good/bad/acceptable decisions at each street.")* *Evidence:*
  S10's `sim_decision` rows carry street + verdict tier + EV-loss per decision — the data
  exists the moment S10 ships; S10 includes only a minimal numbers-only per-street report.
  *Candidate slices:* winrate/EV-loss trend graph; per-street + per-position breakdown;
  per-session filtering; leak-category drill-down. *Open questions:* how much does the S10
  minimal report already answer (review after ~2 weeks of real use); charting approach
  (tokens-only CSS bars vs a library — library needs ask-first).
  *(Epic-2 **R6** promotes the spot-specific + leak-by-spot half of this into NOW — the
  trend/progress-graph half stays here, ranked lower by the user 2026-07-14.)*
- ~~Collapsible hero preflop range chart~~ **DONE 2026-07-12 → PR #36** *(built autonomously under the user's proceed-with-everything instruction: grade_map extended to vs_3bet/vs_4bet/vs_limpers (C0 — also widens S10 grading), GET /simulate/{id}/preflop-chart (grid byte-identical to Practice via the same _INDEX + range_grid; exploit note resolved facing→sim_seat persona, vs_limpers honestly note-less), SimRangeChart collapsed-default panel (fetch-on-expand, pot_bb-keyed per-decision refetch — refuter caught a same-hand stale-chart high), design-review SHIP zero issues; 504 tests green.)* *(user request 2026-07-12;
  gate decision: baseline chart + exploit note — NOT persona-adjusted squares, which would
  collide with the heuristic-only no-go and belongs to a Later bet after exploit-aware
  grading.)* *Evidence:* the pieces exist — baseline preflop packs
  (`content/preflop/*.json`), `RangeGrid.tsx` (Practice's 13×13 chart), and S10's spot
  mapper for current-spot lookup. Collapsed panel in Simulate; uncollapse → the baseline
  action-mix chart for hero's current preflop spot PLUS a one-line persona-aware note from
  `exploit.json` ("vs a Calling Station: value wider, bluff less"). Unmappable/off-content
  spots render "no chart for this spot yet" — never fabricate. Point-of-need only (current
  spot), so it stays inside the no-browsable-lessons-library no-go the same way concept
  cards do. *Candidate slices:* chart panel (reuse RangeGrid + mapper); exploit-note
  wiring. *Open questions:* which villain's note wins in multiway; collapse-state
  persistence.
- ~~Villain range reveal~~ **DONE 2026-07-12 → PR #37** *(range_estimate.py: card-free PublicActionHistory projection + chip-walk replay proven equivalent to live playouts; preflop EXACT pack posterior, postflop ≈ via sample_postflop_decision capture-rng; 11ms/estimate; NO-PEEK test-enforced (swapped villain cards ⇒ identical weights); through_action lockstep (domain_index = 2 + narrated count, FE cumulative bookkeeping proven 169→5 at the raise threshold); heat panel w/ staged-fold gating + hand-boundary close; refuter + design-review rounds all folded; 523 tests green.)* *(user request
  2026-07-12; gate decision: all streets from day one, postflop explicitly labeled an
  ESTIMATE.)* *Evidence:* persona preflop play is explicit-range-based (`personas.py`
  samples from parsed combo ranges) ⇒ the preflop reveal is EXACT conditioning — each
  raise/3-bet/4-bet filters the persona's own range and the chart narrows (the user's
  BTN-raise-wide vs BTN-4-bet-narrow example). Postflop bots decide via the merit ladder,
  not ranges ⇒ postflop chart = approximate category-weight conditioning, ≈-labeled.
  Button-gated per villain; folded villains excluded; updates as each villain acts on each
  street. *Candidate slices:* preflop-exact range tracker + per-villain RangeGrid overlay;
  postflop approximate conditioning; pacing-lockstep staging (S11's staged index governs
  when the chart may update). *Open questions:* combo-weight representation + per-action
  perf; disclaimer wording; interplay with hidden-persona mode (a reveal button is a
  training wheel that mode would gate); does always-available reveal soften the
  read-development goal.
- **Reload-durable recap reasoning (migration 0011).** *(W1 combined-refuter med-1,
  2026-07-12.)* `SimDecision` stores no verdict/reasoning text — the recap's "why" tiers
  exist only in-memory for the live request; a session reload rebuilds the recap with
  freq/EV/correctness intact but tiers=None for every row. If reload-durable reasoning
  becomes a real ask, add `verdict`/`reasoning` columns via migration 0011.
- **Simulate mobile responsiveness.** *(design-review 2026-07-11; deferred by the
  desktop-primary decision — desktop + tablet 768px ship premium/clean.)* *Evidence:* at
  ≤~600px the 9-seat felt collapses into overlap (measured 30 overlapping seat pairs at 375px;
  hero cards over the pot; persona meta chopped by card pucks), and a **pre-existing shared
  masthead** (`.masthead-right` EV-ledger widget, `flex-wrap:nowrap` at 416px — NOT S9 code)
  forces horizontal body scroll ≤~400px on *every* route (body scrollWidth 583 @375). Also a
  cramped stats-strip at mobile (app-shell). *Candidate slices:* felt `min-width` +
  horizontal-scroll wrapper OR a sub-600px compact/vertical seat layout; a shared app-shell
  mobile breakpoint (masthead wrap + stats reflow) — **note the masthead fix is app-wide, not
  Simulate-only**, so it wants its own design-review across Practice/Quiz too. *Open
  questions:* is portrait phone/tablet a real usage context for a localhost desktop trainer.

## LATER — bets / outcomes (unexplored · NO hard dates)

- **Bet: selectable table textures** (aggro online 9-max calibration as a second content
  set). *Segment:* self · confidence: med · assumptions to test: does the live-$2/$3 table
  keep producing enough 3-bet/4-bet reps, or is a tougher lineup wanted? · review-by: after
  ~2 weeks of real Simulate use.
- **Bet: depth-aware persona ranges + depth-aware grading** (beyond SPR commit logic).
  *Confidence:* lo · assumptions to test: how far stacks actually drift in real sessions
  (ledger data will show) · review-by: after carry-over sessions accumulate.
- ~~Bet: session analytics~~ *(promoted 2026-07-12: minimal per-street report folded into
  S10; the richer view — graphs, positional/session breakdowns — is now a NEXT item.)*
- **Bet: solver-grade baseline (Phase 3, unchanged)** — would upgrade both Practice and
  Simulate verdicts on the same `StrategyProvider` seam. *Confidence:* med · review-by:
  after heuristic turn/river grading proves/disproves sufficient.

## Out of scope / no-gos (global)

- 🚫 **No exploit-/persona-aware grading in v1** — baseline only; the exploit layer is the
  first Next item (explicit gate decision, must not silently creep into S10).
- 🚫 **No SRS writes from Simulate in v1.**
- 🚫 **No solver tables** — heuristic + interim EV only; EVs labeled *approximate*.
- 🚫 **No auth/accounts/hosting/billing/multiplayer; no hand-history imports** (unchanged).
- 🚫 **No straddles/antes/rake/tournaments; no real-money framing** — stakes in BB.
- 🚫 **Never grade an unmapped spot silently** (no HU-logic-with-caveat on multiway; no
  flop-truncation on turn/river) — "no baseline yet" is the only fallback.
- 🚫 **No deterministic persona behavior** — strength→action and strength→size stay
  frequency-sampled (anti-sizing-tell).
- ✅ **Invariants held throughout:** domain purity (test-enforced) · freq+EV never boolean ·
  one async `StrategyProvider` · strategy/personas as versioned `content/` data · tokens-only
  CSS, AA contrast + focus both themes · additive Alembic migration per schema change ·
  preflop `spot_signature()` byte-locked; postflop signature dims appended conditionally ·
  `types.ts` hand-maintained · per-hand isolated seeded RNG, seed persisted.
- ⚠️ **Ask-first:** `StrategyProvider` interface changes · new signature dimensions · row-
  rewriting migrations · new top-level dependencies · any caveat-labeled approximate grading
  of unmapped spots.
- **Process:** parallel agents per the track plan (one file = one owner per wave; refuter on
  every slice; design-reviewer on UI slices); may push + open PRs on `feat/*|fix/*|chore/*`
  autonomously; never push `main`, never force-push, never merge without confirmation.
