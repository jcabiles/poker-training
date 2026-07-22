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

- [x] **RES-A — Preflop range research: RFI-by-position + all node contexts, live $2/$3.**
      *(done 2026-07-15, `docs/ai-dlc/research/RES-A-preflop-ranges.md`: 7 UTG1/UTG2 entries —
      RFI ×2, vs_RFI ×3, vs_3bet ×2 — all heuristic-derived via the CO→UTG monotonic-tightening
      interpolation, nesting-verified programmatically (UTG⊆UTG1⊆UTG2⊆LJ, combo-label counts
      23⊂27⊂29⊂30), shape-corroborated by 9-max solver grids. **Blocker resolved:** engine already
      models UTG1/UTG2 as first-class (`spot.py` enum + `_OPEN_SIZE`=3.0 + rotation/action-order/
      grading maps) — R4's only gap is content data + adding both to `RFI_POSITIONS`. `spot_signature()`
      hashes `position.value` raw ⇒ new rows mint non-colliding hashes, purely additive. **Corrected
      prior research:** doc 05 §3.2's UTG1/UTG2 strings don't nest (its UTG2 opened wider than authored
      LJ) — superseded. vs_4bet/blind_defense/vs_limpers for UTG1/UTG2 documented as non-spots (not
      chased). §10 gives R4 copy-verbatim entries. Open R4 call: single `vs BTN` 3-bet facing vs
      authoring SB/BB/CO facings (breadth, not strategy — shape identical). No app/content code touched.)*
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

- [x] **RES-B — Bet-sizing research: realistic fixed $2/$3 sizes, persona-flavored.**
      *(done 2026-07-15, `docs/ai-dlc/research/RES-B-bet-sizing.md`: 60 node×persona cells (preflop 24 +
      postflop 36), each sourced or heuristic-with-reasoning. **Key finding — existing persona sizing
      levers are ALREADY correct/defensible for $2/$3** (preflop `sizing` blocks + postflop bucket
      distributions both confirmed, not rewritten); the user-reported "unrealistic sizes" traces to (a)
      the node-agnostic FLAT postflop distribution and (b) missing turn/river sampling nodes — NOT wrong
      numbers. So R2's real work = wiring confirmed levers through the predetermined bot/hero path, not
      authoring values. "Sizes differ by level" resolved: stakes-calibrated ($2/$3) confirmed, per-hand
      strength→size dial refuted (anti-tell). **Schema flag for R2:** confirm `PersonaPack.postflop.sizing`
      accepts the maniac's `1.5` overbet key (verified present in `maniac.json`) — loosen if enum-locked.
      §5.3 node-agnostic limitation = R2 decision (Option A flat, no schema change, recommended; Option B
      `sizing_by_node` override = deferred). **7 R3 two-option nodes** flagged: c-bet (1/3·3/4), turn
      barrel (1/2·3/4), river value (1/2·pot), vs-3bet (4-bet·shove), check-raise (2.5x·3.5x), facing-bet
      raise (2.5x·3x), + vs-4bet call/jam; open excluded. Anti-sizing-tell verified respected. No code.)*
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

- [x] **RES-C — Postflop range research: call/fold/raise ranges by street & spot.**
      *(done 2026-07-15, `docs/ai-dlc/research/RES-C-postflop-ranges.md`: **representation = category
      weights, NOT combo strings** (postflop range is board-conditioned ⇒ a combo string would be a
      per-board solver table = no-go). Taxonomy frozen verbatim to `postflop.py::_hand_category()`:
      `strong`/`weak_made`/`draw`/`air` (incl. the river busted-draw→air demotion + the deliberate
      top-pair=weak_made-not-strong quirk). All 7 shipped grader node families specced HU + multiway
      (cbet 200, vs_cbet 201, vs_check_raise 202, turn_barrel 203, vs_turn_bet 204, river_barrel 205,
      vs_river_bet 206) as approximate category×texture/turn-class/river-class/price frequency tables,
      sourced doc-02/06 + live GTOW/ThinkGTO/PokerNews. Every multiway row is the direction S8's
      `_apply_multiway` already moves (0.6/1.15/1.3, positive-merit-only, applied last) — no second MW
      model. **"No baseline yet" list (§12):** donk/lead, delayed-cbet/probe/overbet, hero-as-check-raiser,
      3-bet/4-bet & limped pots, short-SPR jams, blocker/kicker resolution, post-check-raise 4-bet-on-paired
      raise leg, and any turn/river spot `grade_map` can't yet build (mapper covers preflop + HU flop c-bet
      today — R5 decides whether to widen). **Reconciliation recommendation:** keep the merit pipeline
      authoritative and have R5's chart render the grader's own `per_action` for the current spot ⇒
      chart==grader by construction; this spec becomes the merit-constant tuning target. No code.)*
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

- [x] **R2 — Realistic persona-flavored fixed bet sizes** *(done 2026-07-16, PR #42 / d9eacea:
      discovered persona preflop sizing levers were DEAD CODE — R2's core work was wiring them
      through the predetermined bot/hero path via new pure `domain/table/sizing.py`
      (`postflop_node_key`, `HERO_NODE_SIZE`, two-sided `preflop_raise_to` clamp,
      `pot_fraction_to_bb`). Added node-aware postflop sizing: `PersonaPostflop.sizing_by_node`
      override sampled only when `is_aggressor` (default False keeps S4 statistical bands +
      range_estimator byte-identical). `LegalAction.size_bb` seam added (feeds R3). grade_map
      bands widened (open→3.0/3bet→3.5×/4bet→2.4×) to fit realistic bot opens — user-approved over
      constraining bots. De-flaked a PYTHONHASHSEED-dependent grading test (cap 160→500, swept
      seeds 0-88 clean + deterministic band test). refuter FAIL→all 5 findings folded pre-build;
      541 tests + verify.sh green across randomized runs.)* ICE 8·7·5.
      **Problem:** unrealistic sizings make every price wrong. **Outcome-link:** decisions
      graded at real prices. **Solution:** replace predetermined bot/hero sizings with the
      RES-B size table — fixed, keyed by node, flavored per persona (levers in the persona
      packs, mechanics in code, per the S4 lever/code split). **Pass/fail:** bot open/3-bet/
      c-bet/barrel sizes match the researched table per persona (test asserts persona A sizes ≠
      persona B where research says so); sizes stay frequency-sampled where multiple are
      authored (no deterministic strength→size tell); chip-conservation + engine tests still
      green; `verify.sh` green. **Appetite:** ~1 epic. **No-gos:** no sliders; no rake/ante;
      hero *choice* is R3, not here — R2 keeps hero on a single predetermined size.

- [x] **R3 — Hero bet-sizing feature: two size options — FLOP C-BET ONLY** *(done 2026-07-16, W1 / PR #44: `_hero_legal_actions` emits two fixed-pair BET legs 0.33/0.75 pot 1-dp via `min_bb` — matching `map_flop_cbet` byte-for-byte, NOT `HERO_NODE_SIZE` which collapses small==big on wet/mono; existing `grade_cbet` grades the choice, FE two-BET branch already renders B/V; 5 tests incl. wet/mono collapse regression + displayed==graded parity. vs-3bet/vs-4bet/turn-river sizing → R3b. Combined-refuter clean on this slice.)* *(consumes RES-B, after R2)*.
      ICE 8·7·5. *(Scope narrowed 2026-07-16 at Gate-2: W1 refuter proved the preflop grader
      `grading.py::grade()` matches by `ActionType` only and CANNOT distinguish a standard 4-bet
      from a shove — both grade byte-identically. So vs-3bet/vs-4bet size grading needs new
      size-matching built INTO the Practice-shared preflop grader, deferred to **R3b**. Flop
      c-bet has no such issue — `grade_cbet` already scores by size — so R3 ships that one node
      cleanly.)*
      **Problem:** hero can't choose a size — a real skill the trainer omits. **Outcome-link:**
      sizing decisions become gradeable. **Solution:** on the flop c-bet, surface **two size
      options (0.33 / 0.75 pot as a fixed pair)** in `_hero_legal_actions`; the existing
      `grade_cbet` grades the choice (freq+EV, approx); FE already renders two BETs (B/V keys).
      **Pass/fail:** hero c-betting the flop sees both sizes; choosing gets a freq+EV verdict;
      wet/mono boards still show two DISTINCT sizes (not the `HERO_NODE_SIZE`==0.75 collapse the
      refuter caught); illegal sizes rejected; `verify.sh` + build green; design-review both themes.
      **Appetite:** ~1 small epic. **No-gos:** no free-form slider; no more than two options; no
      solver EVs; no preflop/turn/river size grading here (R3b). Spec: `specs/r3-hero-bet-sizing.md`.

- [~] **R3b — Hero bet-sizing: preflop + turn/river size grading** — **⤳ SUPERSEDED by Epic 3 · N3 (preflop open/3-bet sizing) + N4 (postflop sizing).** *(consumes RES-B, after R3 + R5)*.
      ICE 7·6·4.
      **Problem:** R3 shipped only flop-c-bet sizing; the juicy sizing skills — 4-bet-vs-shove,
      barrel sizing, check-raise sizing — remain ungraded. **Outcome-link:** the full RES-B
      two-option node set becomes gradeable. **Solution:** (1) build size-matching into the
      preflop grader `grading.py::grade()` (a `_match()` like `postflop.py:555` — pick the chosen
      `ActionEval` by nearest `size_bb`, emit distinct evals per authored raise size) + a
      documented heuristic for the alternate size's approximate EV, WITH a Practice-safety
      regression test (grade() is shared with Practice drills); (2) surface the remaining RES-B
      two-option nodes — **vs-3bet** (4-bet 2.4× / shove), **vs-4bet** (call / shove), **turn
      barrel** (0.5 / 0.75), **river value** (0.5 / pot), **flop check-raise** (2.5× / 3.5×),
      **facing-bet raise** (2.5× / 3×) — the postflop ones riding R5's turn/river coverage;
      (3) FE `decisions.ts` gains a **RAISE-aware two-size branch** (the current one handles only
      two BETs; two RAISEs collide on key `R`) — must not regress Practice's single-RAISE flows.
      **Pass/fail:** each supported node grades the size choice freq+EV; standard-vs-shove no
      longer grade identically (direction test); Practice single-RAISE flows unchanged; illegal
      sizes rejected; `verify.sh` + build green; design-review both themes. **Appetite:** ~1 epic.
      **No-gos:** no slider; no >2 options; no solver EVs; **accepted limitation** — persisted
      `chosen_action` stores a bare `"raise"` so history can't distinguish 4-bet from shove after
      the fact (a `chosen_size_bb` column would be migration 0012, ask-first if it becomes a real
      need).

- [x] **R4 — Preflop coverage: fill UTG+1/UTG+2 + all node contexts** *(done 2026-07-16, W1 / PR #44: authored UTG1/UTG2 RFI + vs_RFI + vs_3bet content verbatim from RES-A §10; added both to `RFI_POSITIONS` (also grows Challenge sampling 6→8, intended); personas UNTOUCHED (nit/station/fish stay wildcard — stat bands safe); `spot_signature()` byte-stable for legacy seats (additive, new seats mint new hashes); repointed `test_off_pack_rfi_position_returns_none`; nesting UTG⊆UTG1⊆UTG2⊆LJ golden + chart-populated + non-spot tests. vs_3bet coverage partial by design (single representative facing per RES-A). No schema/persona/migration change.)* *(consumes RES-A)*.
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

- [x] **R5 — Postflop range chart: openable call/fold/raise ranges for the current spot**
      *(done 2026-07-16, W1 / PR #44: 4 canonical HU turn/river mappers (`map_turn_barrel`/`map_vs_turn_bet`/`map_river_barrel`/`map_vs_river_bet`) in `grade_map_postflop.py` mirroring `scenarios.build_*_spot`, strict multi-street None-on-doubt gates; dispatcher widened for TURN/RIVER. Read-only `GET /postflop-chart` renders the grader's own `per_action` via the SHARED provider singleton ⇒ chart==grader by construction, zero writes; new `SimPostflopChart` panel (reused chrome + action-mix render). Graders/`srs`/`leaks`/`grading` byte-unchanged; pins + `TAXONOMY_VERSION==5` intact; HU-only (multiway→"no baseline yet"). Combined-refuter HIGH fixed: widened the turn/river preflop-open gate to the `[2.0,3.0]` band (bots never open 2.5 — was zeroing HJ/CO/BTN coverage) + bot-driven belt test. **Two coverage followups tracked in NEXT** (`map_flop_cbet` still exact-open-gate ⇒ flop/turn inconsistency; vs-turn/river-bet mappers rarely fire vs bot 2-dp bets). **DESIGN-REVIEW of the chart panel NOT run** (sandbox can't drive Playwright — zombie servers).)* 
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

- [~] **R6 — Coaching: leak-by-spot analytics view** — **⤳ SUPERSEDED by Epic 3 · N1 (north-star dashboard) + N7 (leak-drill Practice).** *(after R2/R4/R5)*. ICE 9·6·5.
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

- [~] **R7 — Coaching: why-it's-wrong recap depth** — **⤳ SUPERSEDED by Epic 3 · N6 (LLM coach).** *(after R6; consumes RES-A/B/C rationales)*.
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

---

## NOW — Epic 3: Grade every decision · measure the rate · coach the leaks (added 2026-07-16)

> Third epic. Re-centers Simulate on the user's explicit **north-star metric** and supersedes the
> thinner Epic-2 tail — **R3b/R6/R7 fold into the slices below**. Same primary outcome (become a
> winning $2/$3 player), now with a measurable proxy the user named and a full
> **grade → measure → coach** loop. Every page eventually supports the decisions hero makes in
> Simulate (N7 makes Simulate the app home).
>
> **North-star metric (user-stated 2026-07-16):**
> - **Good Decision Rate = (optimal + acceptable) / graded** — PRIMARY (the one metric if forced).
> - **Optimal Play Rate = optimal / graded** — secondary.
> - Both **exclude "no baseline yet"** from the denominator (shown as a coverage count), trended
>   and broken out **by street** (v1).
>
> **Locked interview decisions (2026-07-16):**
> - Dashboard v1 breaks the two rates **by street** (preflop/flop/turn/river); finer **by-spot-type**
>   drill-down is a fast-follow (needs per-decision spot dims not stored today — ties to N5).
> - **Two SEPARATE verdicts per decision** — one for the **action** (fold/call/raise/bet), one for
>   the **sizing** — each optimal/acceptable/blunder, at every action and street.
> - **Raise-depth cap: grade full sizing through the 3rd bet** (preflop open→3-bet; postflop
>   bet→raise→re-raise); **beyond that hero gets shove/call/fold only, no sizing grade.**
> - Grading display is **toggleable** (coach mode ↔ real-play mode); data is recorded either way.
> - **Simulate becomes the app home AFTER** grading + dashboard land (N7), not before.
> - **LLM coach (N6) built right after** the metrics; API-vs-local + prompt design settled at its
>   own interview.
> - **TBD (user-flagged for a future interview):** whether Practice-page reps count toward the
>   cumulative Good-Decision/Optimal-Play totals, or the totals stay Simulate-only (resolved in N7).
>
> **Cross-cutting constraints (inherit into every slice):** heuristic / GTO-*simplified* only, no
> solver tables · EVs labeled approximate · domain purity · results freq+EV never boolean · one
> async `StrategyProvider` seam · strategy in versioned `content/` data · `spot_signature()` FROZEN
> (the new sizing verdict rides an **additive** column, never a signature dim) · additive Alembic
> migration per schema change · anti-sizing-tell (bot strength→size stays frequency-sampled) · CSS
> from design tokens · AA contrast + visible focus both themes.

### Build slices (ICE = Impact·Confidence·Ease, 1–10)

- [x] **N1 — North-star dashboard: Good-Decision-Rate + Optimal-Play-Rate, by street.** ICE 10·8·6. *(DONE 2026-07-16 — `#/dashboard` view + slimmed side panel; FE-only, no migration; spec `specs/n1-north-star-dashboard.md`. Design-review PASS both themes.)*
      *(Supersedes R6. Contract map: `contracts/*` R6 scan — `sim_decision` already carries
      `correctness`/`street`/`coverage`/`ev_loss_bb`; NO migration.)*
      **Problem:** the user's own north-star metric is visible nowhere — no way to see how solid
      play is or track it. **Outcome-link:** makes the primary outcome *measurable* (can't improve
      what you can't see) — the measurement backbone every later slice feeds.
      **Solution:** a dedicated **dashboard page** — two KPI cards (Good-Decision-Rate =
      (optimal+acceptable)/graded; Optimal-Play-Rate = optimal/graded) and a tokens-only
      **by-street breakout** (preflop/flop/turn/river) below the cards, each street showing both
      rates + graded count. Read-model over existing `sim_decision` (reuses the S10 street report's
      no-baseline-exclusion contract). *(Scope revised at the 2026-07-16 `/ai-dlc` interview: the
      over-time **trend** chart is DEFERRED to a Next slice — it needs a new date-bucketed
      aggregation; v1 is the by-street "mix" breakout only. Spec: `specs/n1-north-star-dashboard.md`.)* **Pass/fail:** page shows both rates as cards with no-baseline
      rows as a coverage count (never in the denominator); a per-street table/chart matches the S10
      street-report numbers exactly; tokens-only CSS, AA + focus both themes; `verify.sh` + build
      green; design-review both themes. **Appetite:** ~1 epic. **No-gos:** no by-spot-type
      drill-down yet (fast-follow, needs N5's stored spot dims); no persona split (L1); the
      **sizing-rate card lands with N3/N4** (no sizing verdict exists to chart yet); charts are
      tokens-only CSS bars unless a library is ask-first'd; no SRS writes; read-model only (no new
      columns).

- [x] **N2 — Grading visibility toggle: coach mode ↔ real-play mode.** ICE 8·9·8. *(DONE 2026-07-17 — Coach↔Real-play pill in Simulate topbar; hides live badge + recap, keeps recording; default real-play; FE-only, no migration; spec `specs/n2-grading-visibility-toggle.md`. Refuter PASS, design-review PASS both themes.)*
      **Problem:** the live verdict badges + recap make it impossible to rehearse a hand "for real";
      a coaching user wants them ON. **Outcome-link:** the same table serves rehearsal *and*
      coaching. **Solution:** a persistent toggle that hides/shows all in-hand verdict badges + the
      end-of-hand recap grading; **grading is still computed + recorded when hidden** (the dashboard
      keeps filling). **Pass/fail:** toggling hides/shows every verdict badge + recap tier;
      preference persists across reload; with grading hidden a played hand still writes
      `sim_decision` rows (assert rows created); AA + focus both themes; `verify.sh` + build green;
      design-review. **Appetite:** ~1 small epic. **No-gos:** no per-decision/per-street granular
      toggles (one global switch); no change to what's recorded; no new endpoint if a client-only
      preference suffices.

- [x] **N3 — Preflop sizing grades: open + 3-bet (4-bet+ = shove/call/fold).** ICE 9·7·5. *(DONE 2026-07-17 — two graded open/3-bet sizes (rec=optimal, alt=acceptable) via graded-spot inject in apply_hero_action; grader collision fixed (4bet≠shove); sizing_correctness col + migration 0011; FE two-raise + sizing sub-note. Refuter PASS on diff; design-review HIGH+MED folded. Spec `specs/n3-preflop-sizing-grades.md`.)*
      *(Supersedes R3b preflop half. Consumes RES-B. Contract map: this session's R3b scan.)*
      **Problem:** hero can't choose or be graded on preflop sizing — the app picks the size.
      **Outcome-link:** the sizing-verdict half of the north-star, preflop. **Solution:** emit two
      size options for RFI-open and 3-bet in `_hero_legal_actions`; build size-matching into the
      **Practice-shared** preflop grader `grading.py::grade()` (a `_match()` by nearest `size_bb` +
      fix the `ActionType`-keyed `sizes` dict collision the R3 refuter caught — standard-4bet vs
      shove grade byte-identically today); FE `decisions.ts` gains a **RAISE-aware two-size branch**
      (two raises collide on key `R` today, second unreachable); **at 4-bet+ hero gets only
      shove/call/fold, no sizing grade** (the cap). Persist the sizing verdict as a **SEPARATE
      additive column** (migration; `spot_signature()` untouched). **Pass/fail:** hero opening/
      3-betting sees two graded size options; standard-4bet vs shove no longer grade identically
      (direction test); at 4-bet+ only shove/call/fold offered; **Practice single-raise flows
      byte-unchanged** (the existing `test_grading.py` suite stays green — the new `_match()` path
      must be a strict superset: identical output when ≤1 raise size is legal, incl. the untouched
      CALL/BET/FOLD sizes — plus a new standard-vs-shove direction test); migration up/down clean,
      existing rows read back unchanged; `verify.sh` + build green; design-review. **Appetite:** ~1 epic.
      **No-gos:** no slider; no >2 sizes; no sizing grade past the 3-bet cap; anti-sizing-tell
      intact; no signature-dim change. **⚠️ Interview at /ai-dlc:** the action-vs-sizing verdict
      data model (blended row vs two verdict columns vs two rows) — decide before touching schema.

- [x] **N4 — Postflop sizing grades: bet / raise / re-raise, up to the 3-bet cap.** ICE 8·6·4. *(SPLIT at /ai-dlc 2026-07-17 → **N4a (barrels)** + **N4b (facing-raises)** — cleanly separable, no shared function bodies. Both sub-slices done 2026-07-18.)*
    - [x] **N4a — Barrel sizing grades (turn/river barrels + flop c-bet consistency).** *(DONE 2026-07-18)* Two-size turn/river barrel offer + a SEPARATE additive `sizing_correctness` on the 3 aggressor bet graders (reuses N3 plumbing — no migration/schema/FE); fixed the `_barrel_spot` 0.33/0.75 bug → RES-B pairs (turn 0.5/0.75, river 0.5/1.0) via `POSTFLOP_BET_FRACS` + street-aware canonical-bet gate (refuter HIGH — a new turn size would've orphaned the river mapper). 617 tests, pins byte-unchanged, refuter+design-review PASS. Spec: `specs/n4a-barrel-sizing-grades.md`.
    - [x] **N4b — Facing-raise sizing grades (vs-cbet / vs-check-raise / vs-turn-bet / vs-river-bet).** *(DONE 2026-07-18)* Two RAISE legs at all 4 facing nodes (`FACING_RAISE_MULTS`: check-raise 2.5/3.5 flop-scoped, raise 2.5/3.0 — the 3.0 big keeps turn/river `per_action` byte-identical); texture-overlay `_raise_sizing_verdict` (dry→small, wet→big, medium→both-acceptable); two NEW flop mappers (`map_flop_vs_cbet`, `map_flop_vs_check_raise` with the INCREMENTAL call leg) + dispatcher widening; Practice on the shared const (vs-cbet drills 3×→3.5×); all-in-TO raise ceiling (refuter-on-diff HIGH); `_CANON_BET_TOL` reachability fix (design-review HIGH — bot 2-dp bet rounding never matched the 1-dp canonical gate, which also had the live turn/river facing nodes dead since R5). 646 tests. **→ N5 inherits:** live facing coverage still throttled by pre-existing gates (loose persona mix → multiway pots; oversized persona opens vs the R5 open band; BB-defense content only vs UTG/CO/BTN). Spec: `specs/n4b-facing-raise-sizing.md`.
      *(Supersedes R3b postflop half. Consumes RES-B/RES-C. Contract map: this session's R3b scan.
      May split at /ai-dlc — barrels vs facing-raises.)*
      **Problem:** postflop sizing is graded only on the flop c-bet (R3); barrels, check-raises,
      facing-bet raises aren't. **Outcome-link:** the sizing-verdict half, postflop. **Solution:**
      two-size choices + grading for turn/river barrel (fix `_barrel_spot` to the RES-B 0.5/0.75 &
      0.5/pot pairs — it hard-codes 0.33/0.75, a displayed≠graded bug), vs-cbet raise, flop
      check-raise (2.5×/3.5×), facing-bet raise (2.5×/3×) — the last two need **new live flop
      `VS_CBET`/`VS_CHECK_RAISE` mappers** (none exist) + `_match()` fixes on the four facing-side
      graders (`grade_vs_cbet/_check_raise/_turn_bet/_river_bet` share the same ActionType-only RAISE
      collapse). Capped at the 3rd bet. Reconcile the live-vs-graded raise-size formula (two exist:
      `pot_fraction_to_bb` vs `_faced_bet_spot`'s flat `3×bet`). **Pass/fail:** each supported
      postflop node up to the 3-bet grades the size choice freq+EV; **displayed==graded parity** per
      node; beyond the 3-bet = shove/call/fold; postflop grader **hash-pins +
      `TAXONOMY_VERSION`==5 unchanged**; `verify.sh` + build green; design-review. **Appetite:** ~1
      large epic (split candidate). **No-gos:** no solver EVs; no sizing past the cap; multiway stays
      "no baseline yet" if unmapped; never silently HU-grade multiway.

- [x] **N5 — Grade every action: close the high-frequency "no baseline yet" gaps (within the cap).** ICE 7·6·4. *(DONE 2026-07-18 — spec `specs/n5-coverage-expansion.md`.)* Shipped: flop c-bet open gate → the `[2.0,3.0]` band with ACTUAL-open pot math; 9 blind-defense content fills (v2, nesting-tested, SB stays 3-bet-or-fold); `sim_decision` spot dims (migration 0012, position-always/unmappable-nulls); `_MW_THIN_VALUE_DAMPEN=0.7` + HU-shaped-input annotations; **3-way multiway BB-defense mappers** (hero=BB closes — engine sim disproved the cold-caller-closes plan; caller entry gate-only; caller-folded degrades to 2-live; dormant "mw" signature dim now live, HU hashes byte-identical); fixed-seed coverage baseline (225→228/1220). Refuter-on-diff PASS + 1 MED documented: MW mappers 0 fires in the 400-hand probe (shape ×4, chain variance — watch live; dominant chokes = the deferred persona-mix/open-band levers). 669 tests. Still-None enumerated + pinned: limped MW, donk leads, 4+-way, caller raises, delayed c-bets, non-closing spots.
      **Problem (original):** the vision is a rating at *each* action/street, but many live spots still show
      "no baseline yet" (RES-C §12 non-spot list) — thinning the north-star denominator + blocking
      N1's by-spot-type drill-down. **Outcome-link:** raises graded-decision coverage (the
      north-star's honest coverage floor) and unlocks the by-spot dashboard cut. **Solution:** close
      the two W1-surfaced gate gaps — `map_flop_cbet` exact-open-gate → the `[2.0,3.0]` band (to
      match the widened turn/river mappers; a standard 3.0 open currently maps the turn barrel but
      not the flop c-bet on the same line) and `map_vs_turn_bet`/`map_vs_river_bet` bet-gate
      tolerance (they demand a 1-dp bucket but bots bet `round(frac*pot,2)`, so BB turn/river charts
      are near-empty) — then author + map the highest-frequency missing node families within the
      3-bet cap (**research-gated: may need a RES-D spike** for donk/delayed-cbet/probe). Store the
      per-decision spot dims N1's by-spot drill-down needs (additive). **Pass/fail (all runnable, no invented number):**
      (a) the two named gate gaps demonstrably fire in a bot-driven belt test — `map_flop_cbet` maps
      a standard 3.0 open, and `map_vs_turn_bet`/`map_vs_river_bet` fire against a bot
      `round(frac*pot,2)` bet; (b) an **enumerated** set of previously-"no baseline" node families
      within the cap now map (list fixed in the spec, asserted one-by-one); (c) measured
      graded-decision coverage over a **fixed-seed** N-hand sim does **not regress** vs the pre-N5
      baseline recorded in the slice notes; (d) every still-uncovered line stays honest "no baseline
      yet"; (e) grader/`srs` pins + `TAXONOMY_VERSION`==5 unchanged; `verify.sh` green. **⚠️ Set the
      numeric coverage-floor target (aspirational) at N5's /ai-dlc interview** — the checks above do
      not depend on it. **Appetite:** ~1 epic (+ RES-D spike if needed). **No-gos:** never grade an unmapped spot silently; heuristics stay simplified
      (no solver); state the hard ceiling (some lines never covered), don't fake it.

### After the Build slices — sequenced, NOT yet spec-ready

> These carry the user's ordering intent (N6 right after the metrics; N7 after grading + dashboard;
> L1 much later) but are **not spec-ready vertical slices** — each needs its own interview before
> `/ai-dlc`. Listed here only for sequence; their canonical homes are the doc's `## NEXT` / `## LATER`
> columns below (cross-referenced there). **Do NOT hand these to `/ai-dlc` until N1–N5 land + the
> flagged interview happens.**

- [x] **N6 — LLM coach (feedback on good/bad decisions).** *(DONE 2026-07-18 — spec
  `specs/n6-llm-coach.md`. Interview locked: Claude API behind a swappable `CoachProvider` seam +
  deterministic templated fallback (default when no key); on-demand "Explain this" button per recap
  row.)* Shipped: `app/services/coach.py` (`CoachContext`/`CoachProvider` Protocol, `TemplateCoach`
  offline default, `AnthropicCoach` via **stdlib urllib** — no new dependency; `ANTHROPIC_API_KEY`/
  `ANTHROPIC_MODEL` env, `asyncio.to_thread`, singleton + `reset_coach`); `explain_decision` always
  returns text (falls back to template on any primary failure). `POST /simulate/{id}/explain`
  (`assert_session_active` 404 idiom; hero-only `CoachExplainRequest` — **no villain-card slot**,
  live-per-request, **no persistence/migration**). GradeView gained node_context/position/
  facing_position (from the N5 sim_decision dims) so the live coach prompt matches what's tested
  (refuter-on-diff med). FE: per-row "Explain this" in SimRecap (coach-mode gated) + loading/error
  states + tokens-only CSS. 682 backend tests + verify.sh + FE typecheck/build green. Spec-refuter
  PASS-w-issues (3 folded pre-build), refuter-on-diff PASS (1 med folded). Design-review: first
  pass FAIL → 3 CSS fixes applied verbatim (align-items:flex-start; mobile indent reset; light
  border →3:1); **re-review blocked** by an un-killable orphaned dev-server (sandbox can't signal
  cross-session PIDs) — fixes verified in source + build + hand-computed contrast; browser re-review
  offered on request. No `spot_signature()`/grader/pin/`TAXONOMY_VERSION` change.

- [x] **N7 — IA restructure: Simulate as home + Practice organized around leaks.** *(DONE 2026-07-18
  — spec `specs/n7-simulate-home-leak-practice.md`. Interview: Practice reps stay **OUT** of the
  cumulative totals — Simulate-only, resolving the standing TBD.)* Shipped: (A) Simulate is the
  default/first view (hashRoute fallback home→simulate; VIEWS reorder; old hub relabeled "Learn",
  still reachable — all `view==="home"` guards key on the unchanged id, no ripple). (B) Metric-only-
  Simulate **lock** — `street_report`/`leak_by_spot` read `SimDecision` only; a regression test proves
  a `source='simulate'` `DrillAttempt` moves neither report. (C) `leak_by_spot` read-model (groups
  graded rows by node_context×position, worst-first by Good-rate, min_sample 5 / top 6, null-node
  defensive skip) + `GET /simulate/report/leaks` + a Dashboard **"Your leaks"** panel: each family
  links into the matching Practice drill mode (`_NODE_TO_DRILL_MODE`, all 8 real modes) or shows
  "Simulate only" (turn/river barrels have no Practice drill). **No migration** (reuses N5 dims);
  no `spot_signature()`/grader/pin/`TAXONOMY_VERSION` change. 688 tests + verify.sh + FE typecheck/
  build green. Spec-refuter PASS (3 low folded), refuter-on-diff PASS (0 issues). Design-review on a
  fresh :5174 server (orphaned :5173 stale-server worked around). **v1 interpretation:** Practice's
  own drill selection is not rewired — the dashboard leak links carry the "organized around leaks"
  intent (lower risk).

- **L1 — Persona-aware metrics + per-player-type ranges.** *Much later. Absorbs the pre-existing
  "Exploit-aware grading layer" NEXT item.* Problem (P6): baseline grading is blind to opponent type
  — optimal play vs a maniac ≠ vs a nit. Bet: persona-conditioned verdicts + predefined
  per-player-type ranges across spots; dashboard sliceable by villain type. *Confidence:* med ·
  *assumptions to test:* does it change enough decisions to matter at $2/$3; per-persona authoring
  volume · *review-by:* after N1–N6 ship + real data accrues. **⚠️ NEEDS EXTENSIVE INTERVIEW.** →
  lives in `## LATER` (canonical).

---

## NOW — Epic 4: Bot-math correctness — price-aware defense, size-linked bluffing, bounded aggression, theory-calibrated grading (added 2026-07-21)

> Fourth epic on the shipped Simulate table. Same north-star (become a winning $2/$3 player).
> Where Epics 1–3 built the table, coverage, and grading *pipeline*, Epic 4 fixes the **decision
> math inside it** — two confirmed-wrong behaviors plus the calibration that makes bots feel like
> players and makes grades trustworthy. **Grounded on a vetted yardstick:** the three poker-math
> docs (Obsidian vault: *Comprehensive Reference*, *Calibration & Numbers (Spec)*, *Persona &
> Multiway Modeling*) were adversarially reviewed by **two independent reviewers (Sol + Opus,
> 2026-07-21)** who found **zero arithmetic errors** and confirmed the docs give the RIGHT targets
> for this fix. Review synthesis + findings: `docs/ai-dlc/research/poker-math-review/`
> (`SYNTHESIS.md`, `sol-findings-raw.md`, `opus-findings.md`).
>
> **Interview decisions (locked):** fix **properly** (re-derive the S4 postflop calibration bands to
> theory, don't paper over) · fix **BOTH** opponent behavior **AND** hero grading · **one large
> epic** · **spikes front-loaded** (each seeds a build slice) · stays **heuristic + interim EV**, no
> solver tables, EVs labeled *approximate* · results stay **freq + EV, never boolean** · strength→
> action and strength→size stay **frequency-sampled** (anti-sizing-tell no-go holds).
>
> **Scope (locked):** (1) **price-blind defense** — bots fold/call ignoring bet size, pot odds, and
> the α fold-ceiling [CONFIRMED WRONG]; (2) **bluff frequency decoupled from bet size** — a flat
> per-persona `bluff_freq` instead of a size-linked one [CONFIRMED WRONG]; (3) **maniac aggression
> saturation** — an unbounded aggression multiplier drives near-argmax play; (4) **multiway
> mis-calibration** — the n-th-root/dampening applied as if a per-opponent constant; (5)
> **theory-calibrated hero grading** + re-derived S4 bands; (6) **min-bet legality bug** ("20BB pot
> but hero can only bet 1BB"); coarse hand-ladder handled as a sub-concern of (1)/(3), promoted to
> its own slice only if a spike shows it's the root cause.
>
> **⭐ The #1 cross-cutting guardrail (from the Sol+Opus review — inject into every defense/grading
> slice brief): MDF/α is a FOLD-CEILING sanity check, NOT a "fold ≈ MDF" defend-floor.** `P/(P+B)`
> is the flat-call form (it "doesn't work with a raise" — GTO Wizard), and real solver defense often
> sits *below* raw MDF pre-river. Use α to catch the price-blind bug (a bot/hero that folds the same
> regardless of size is unambiguously wrong); do **NOT** grade a fold as too tight merely because it
> beat MDF on the flop/turn or vs a capped/polar bettor — use pot-odds-vs-*actual* value:bluff
> there. This is exactly what keeps the price-blind FIX from over-correcting into a new bug.
>
> **Cross-cutting hazards to inject into every Epic-4 slice brief:**
> - **Domain purity (test-enforced):** all decision math stays in `app/domain/` — no web/DB imports.
> - **`spot_signature()` frozen:** re-calibration tunes *constants/frequencies*, not signature dims;
>   changing the signature orphans SRS history. Postflop signature dims append conditionally only.
> - **Grading behind the one async `StrategyProvider`:** hero-grading changes flow through that seam
>   (swappable heuristic→solver later); don't fork a second grading path.
> - **Frequency-mixed, never argmax:** every fix must preserve `rng.choices` mixing — the maniac cap
>   (F3) must *lower* saturation, not replace the mix with a threshold.
> - **Anti-sizing-tell:** strength→size stays decoupled; F2 links bluff *frequency* to size, it must
>   NOT leak hand strength into the chosen size.
> - **Multiway = direction, not constant:** the n-th-root is a symmetric-independent idealization
>   (both reviewers) — F4 encodes "bluff less / value-lean multiway," never a per-opponent MDF number.
> - **RES-B already answered "realistic sizes":** Epic-2's RES-B found the persona sizing levers are
>   already correct/defensible for $2/$3 (the issue was flat distribution + missing nodes, not wrong
>   numbers). So the user's "optimal bet sizes" spike is **largely pre-answered** — RES-E only
>   resolves the residual (which size buckets the corrected defense/bluff logic keys on).

### Research spikes (front-loaded, parallel — output = decision doc + numbers, no app code)

- [x] **RES-D — Theory→engine calibration: price-aware defense + size-linked bluff bands + re-derived
      S4.** *(done 2026-07-21, `docs/ai-dlc/research/RES-D-calibration.md`. Root-caused both confirmed
      bugs in `personas_postflop.py`: facing a bet, fold/call/raise merits read `_FOLD_BASE/_CALL_BASE/
      _RAISE_BASE[bucket]` ONLY — zero size/pot-odds input (price-blind); bluff mass is flat `bluff_freq`
      with size drawn independently after (bluff-freq decoupled). Maniac saturation quantified: aggression
      15.0 vs ≤3.2 for every other persona. Delivered: (a) per-persona × 4-size-bucket **fold-to-bet target
      bands** anchored to the α fold-ceiling with hard invariants F1 must reproduce — monotone-in-size,
      ordering station<fish≈maniac<lag<tag<nit, ceiling-not-floor; (b) per-persona **chosen-size→value:bluff
      curves** anchored to polar f/(1+2f) with size-linked + anti-sizing-tell invariants for F2; (c)
      re-derived S4 bands — fold-to-cbet becomes size-conditional (slope-checked), WTSD re-anchored toward
      the PRD population bands via a measure-then-anchor procedure keyed to F1 (current bands are inflated
      BECAUSE price-blind defense keeps pots to showdown — the doc proves the causal link); (d) the A1
      fold-ceiling guardrail written as a concrete F5 grading rule. Every number tagged SOLVED/SOURCED/
      DERIVED; no app code. Open calls handed down: RES-E finalizes size-bucket cutoffs; F1 picks the
      mechanism (price multiplier vs pot-odds gate) — this doc fixes targets, not code shape.)*
      **Problem:** the postflop merit tables (`_FOLD_BASE`/`_CALL_BASE`/`_RAISE_BASE`/`_AGG_BASE`
      in `personas_postflop.py`) and the S4 WTSD bands (`test_personas_postflop.py`) were tuned to
      *engine-anchored* targets, not to first-principles price theory — so bots don't move with bet
      size and grading can't cite a theory bar. **Outcome-link:** every defense decision and every
      grade rests on a defensible number. **Solution:** from the vetted docs (Spec §1/§3/§9, Reference
      §2–§3), produce, for each persona × node family, the **target fold/call/raise frequency as a
      function of FACED bet size** (pot-odds break-even + α fold-ceiling, tempered by realization) and
      the **target bluff fraction as a function of hero's CHOSEN bet size** (polar `f/(1+2f)`, persona-
      skewed). Re-derive the S4 bands to these. **Bake in the A1 guardrail explicitly** (α = ceiling,
      not floor; pot-odds-vs-actual on flop/turn). **Pass/fail:** a decision doc under
      `docs/ai-dlc/research/` gives (a) a faced-size→{fold/call/raise} band per persona×node, (b) a
      chosen-size→bluff-fraction curve per persona, (c) the re-derived S4 band targets with their
      theory citation, (d) a written statement of the A1 guardrail as a grading rule; every number
      tagged SOLVED/SOURCED/DERIVED; no app code touched. **Appetite:** ~1 large spike. **No-gos:** no
      solver tables; no code; approximate labels mandatory.

- [x] **RES-E — "Optimal bet sizes per spot" (residual only — RES-B pre-answered the bulk).**
      *(done 2026-07-21, `docs/ai-dlc/research/RES-E-size-buckets.md`. Confirmed the engine's size
      vocabulary is `{0.33, 0.5, 0.75, 1.0, 1.5}` + per-street `POSTFLOP_BET_FRACS` (sizing.py) and
      mapped it onto RES-D's 4 buckets: SMALL ≤0.40 / MEDIUM 0.41–0.70 / LARGE 0.71–1.10 / OVERBET
      >1.10. Locked rulings: cutoffs are on live **pot-fraction = bet_bb/pot_bb** computed at decision
      time (not the discrete authored keys — so F1 responds to ANY faced size); 1.0=pot lives in LARGE;
      maniac 1.5 is the sole OVERBET. Cites RES-B for the values — invents NO new sizing numbers. No code.)*
      **Problem:** the user asked for a bet-sizing spike; Epic-2's RES-B (`docs/ai-dlc/research/
      RES-B-bet-sizing.md`) already found the persona sizes correct/defensible — the open residual is
      *which discrete size buckets* F1's defense and F2's bluffing should key on (e.g. small ≤⅓ /
      medium ½–⅔ / large ≥pot / overbet), so the size→frequency logic has stable inputs.
      **Outcome-link:** F1/F2 need a fixed size-bucket vocabulary to be testable. **Solution:** confirm
      (or minimally extend) RES-B's node×persona size table into a small **size-bucket taxonomy** the
      corrected logic maps faced/chosen sizes onto, reconciled with `sizing.py` and the existing
      postflop sampling buckets. **Pass/fail:** a short decision doc names the size buckets + their pot-
      fraction cutoffs and maps each existing node's sizes onto them; explicitly cites RES-B for the
      values; no code. **Appetite:** ~½ spike (mostly reconciliation). **No-gos:** no new sizing
      numbers beyond RES-B unless a gap is found; no bet-size sliders; sizes stay FIXED.

- [x] **RES-F — Min-bet legality root-cause ("20BB pot but hero can only bet 1BB").** *(done
      2026-07-21, `docs/ai-dlc/research/RES-F-min-bet-legality.md`. Root cause = a degenerate OFFER, not
      an illegality: `sim_session.py::_hero_postflop_size_bb` (:354-362) reads `HERO_NODE_SIZE.get(node)`
      which has only 6 aggressor-node keys → any unmapped/non-aggressor node (donk/lead/probe/delayed-cbet)
      misses → returns None → FE falls back to the engine min BET (`engine.py:187-192` = `min_raise_to_bb`
      = 1BB, which is the CORRECT legal min). So a 1BB bet into a 20BB pot is legal but is the ONLY thing
      offered. Recommended fix (F6) = **offer-layer default**: when the node is unmapped, offer the street's
      small `POSTFLOP_BET_FRACS` fraction × pot (clamped), so hero gets a pot-proportional size that the
      canonical-bet grader still maps (or honest "no baseline yet"); reject touching `engine.legal_actions`
      (high blast radius — bots/range-estimate/grading read it; 1BB IS the real min). No code.)*
      **Problem:**
      in some spots hero's legal bet options are degenerate — a tiny min-bet into a large pot — which
      is unrealistic and distorts both play and grading. **Outcome-link:** hero always faces sensible,
      realistic sizing choices. **Solution:** trace the legal-action / sizing path (`sizing.py`,
      `table/play.py`, the `LegalAction`/`Decision` sizing shape) to root-cause: is it a min-bet floor,
      chip rounding, a short-SPR/stack-cap interaction, or a pot-fraction option that collapses when
      stack≪pot. Enumerate fix options (e.g. snap to nearest legal size bucket; clamp min-bet to a
      pot-fraction floor; suppress degenerate options) with their blast radius on grading + the
      canonical-bet mapper. **Pass/fail:** a decision doc identifies the exact code path + the trigger
      condition (with a reproducing spot) and recommends a fix with trade-offs; no app code. **Appetite:**
      ~½ spike. **No-gos:** no code in the spike; no change to `spot_signature()`.

### Build slices (ICE = Impact·Confidence·Ease, 1–10)

- [x] **F1 — Price-aware bot defense (fixes the price-blind-defense bug).** *(done 2026-07-22:
      multiplicative price factor on the fold merit only — faced_frac = to_call/(pot −
      max(current_bet_to, to_call)) → RES-E bucket → α anchor, factor = 0.35·(α_b/α_MED)^(2.2·
      stickiness^−0.15), constants fitted numerically against min(RES-D §2 band top, α−0.01);
      call/raise merits, sizing choice, SPR-commit, `rng.choices` mixing all untouched. Tests:
      monotone SMALL→OVERBET all 6 personas (pot vs ⅓-pot gap 0.17–0.26 ≥ mandated 0.10); α
      ceiling ≤ f/(1+f)+0.03 (nit exempt, documented); ordering station<fish≈maniac<lag<tag<nit;
      NO fold floor from α/MDF anywhere (A1). **Refuter cycle:** initial FAIL — faced_frac
      denominator wrong for raise-over-bet/check-raise (engine repro: 5/15 SMALL vs true 5/12
      MEDIUM) + tests only covered simple bets; fixed via existing `current_bet_to` (no signature
      change), 3 regression tests on the exact repros (stash-verified non-tautological), re-refute
      PASS-w-issues. **Documented deviations:** (1) WTSD re-anchored UP (station→(0.66,0.83) etc.)
      — RES-D §4 predicted a fall assuming under-folding; measurement showed the engine OVER-folded
      the α ceiling at every size, so the ceiling-respecting fix folds less → more showdowns;
      ceiling kept as the hard contract per A1 (RES-D §7 flagged this tension). (2) nit measures
      under-α (tightest folder, ordering intact) — §2's over-α leak unreachable with shared
      constants. (3) tag/lag OVERBET ~0.53–0.54 — §2 assumed 2×-pot α=0.667, engine overbet is
      1.5× (α=0.60). (4) nit ftc band (0.10,0.90) documented-unmeasurable at this N — re-measure
      follow-up. **Known limitation (refuter MED, in-code comment):** same-street 3-bet+ lines
      understate faced_frac (aggressor's own earlier street chips in current_bet_to; exact fix
      needs per-action pot history the engine doesn't keep; error conservative — under-folding).
      coverage_baseline re-recorded 1220/225→1260/237 per its documented procedure (refuter
      reproduced byte-for-byte). 711 backend tests + ruff green.)* ICE 9·8·5.

- [x] **F2 — Size-linked bot bluffing (fixes flat `bluff_freq`).** *(done 2026-07-22: joint
      (action,size) law via two-stage factorization — (1) bluff_mass × E_w[bucket_factor] over the
      persona's AUTHORED sizing dist before the action draw, (2) bluff-cell (AIR/ACE_HIGH no-draw)
      size-draw weights tilted by factor(s) = share(bucket)/0.27; mathematically identical to
      "pre-draw size, condition bluff on it" (refuter confirmed algebraically + 200k-sample sim,
      exact to noise, no double-counting) but keeps the action draw as the FIRST rng.choices call
      so range_estimate's _CaptureRng stays sound. Bluff-share targets per RES-D §3 polar curve:
      SMALL 0.20 / MEDIUM 0.27 / LARGE 0.32 / OVERBET 0.375 (f/(1+2f) at bucket-representative
      sizes mirroring _BUCKET_ALPHA). **Direction note:** roadmap wording "lower bluff-to-value
      ratio" was a slip — RES-D §3 (authoritative) has bluff SHARE rising with size, i.e.
      value:bluff falling toward 1:1; tests assert bluff freq strictly INCREASING SMALL→OVERBET.
      Anti-sizing-tell: value-hand size draw stays authored byte-for-byte (regression test
      unmodified; refuter measured 0.4998 vs authored 0.5 at n=486k); the air-range big-size lean
      (P(1.5×|air,bet)≈0.65 maniac) is the intended Bayes consequence of RES-D §1b, not a leak.
      Bot raises draw from authored sizing (FACING_RAISE_MULTS is hero-only — spec's
      _BLUFF_RAISE_FACTOR mention was off; tilt applies to the raise-size draw consistently).
      **Documented side effect (refuter LOW):** stage-1 E_w[factor] shifts overall per-persona
      bluff mass (station/fish −13.7%, nit +11.1%, tag +0.9%, lag +6.3%, maniac +23.6%; up to
      +26.7% on maniac's raise node) — intentional-by-construction; BANDS absorbed it unmodified
      (5× stable). coverage_baseline re-recorded 1260/237→1275/228 per its documented procedure
      (refuter isolated: revert-personas-only reproduces old fixture exactly; new-ungraded
      decisions spread broadly across streets/shapes — stream drift, no mapper regression;
      graded ratchet now guards from 228). 4 new tests incl. a scale-then-redraw killer. 720
      backend tests + ruff + verify.sh green; refuter PASS.)* ICE 8·7·5.

- [x] **F3 — Bounded maniac aggression (fixes saturation → near-argmax).** *(done 2026-07-22:
      `_AGGRESSION_CAP = 5.6` in code (S4 mechanic — levers stay in packs, maniac.json keeps 15.0
      as "above the cap"), applied `min(pf.aggression, cap)` at the single site where the lever is
      read; `_COMMIT_AGG_BOOST` interaction bounded as a consequence (45×→16.8×). Knee chosen by
      measured sweep: 4.8 dropped maniac AF to lag-level (2.03–2.39 vs lag ~2.1–2.5), violating
      "clearly most aggressive"; 5.6 = 1.75× lag keeps AF 3.19–3.32. Entropy roughly doubled in
      the pinned spots (top-pair unopened 0.294→0.551 bits; overpair facing ½-pot 0.484→0.824;
      floor 0.5 bits ≈ mix no more extreme than 89:11, pre-fix values pinned in-test). Monster-
      SPR-commit spot deliberately NOT floored (H 0.168 post-fix — commit-boost mechanics, even
      tag is P≈0.976 there; not maniac saturation). Non-maniac personas byte-unchanged (maker:
      2,000 decisions × 5 personas × 10 shapes JSON-identical; refuter independently confirmed —
      all other levers ≤3.2 < knee ⇒ min() is identity; noise param never non-default in codebase).
      Maniac AF band re-anchored (2.4,999)→(2.4,4.5) — the ∞ top was a saturation artifact;
      delta-method 3σ CIs at N=399/N=670 + small-n headroom (in-file comment). WTSD 0.56–0.57
      mid-band, (0.47,0.65) kept. Per-node strict most-aggressive ordering test (maniac BET weight
      > lag/tag, refuter-verified across 5 spot types). coverage_baseline re-recorded 1275/228→
      1196/242 (refuter reproduced exactly; graded share ROSE 17.9%→20.2% — maniac betting less ⇒
      more mappable spots; spot-checked, no double-grading). F1 fold-ordering (fish≈maniac) + F2
      bluff-ordering (maniac tops) orthogonal and passing. 723 backend tests + ruff + verify.sh
      green, 5× stable; refuter PASS (2 LOW: brief-citation traceability, pre-existing
      coverage-baseline docstring scoped to mapper-only changes).)* ICE 7·8·6.

- [x] **F4 — Multiway calibration correction (direction, not constant).** Ensure the multiway path
      (`_apply_multiway` / `multiway_bluff_damp`) encodes "**bluff less + value-lean** with each added
      opponent" as a **direction**, never a per-opponent MDF/defense constant (both reviewers: the
      n-th-root is a symmetric-independent idealization). **Pass/fail:** multiway c-bet/bluff frequency
      is **lower** than the HU baseline for the same spot (test-asserted), no per-opponent MDF number
      is asserted anywhere, and value-hand continuation is at least as tight as HU. **Appetite:** ~1
      slice. **No-gos:** no second multiway model; no n-th-root constant baked as a target. ICE 6·6·5.
      *(Done 2026-07-22, PR #69. Audit: the bet-side directions were already true — existing
      `multiway_bluff_damp` monotonically cuts bluff frequency per added opponent and value
      continuation is never looser than HU (both now test-asserted, opponents 1→2→3). Gap closed:
      the CALL-side had no multiway response — bluff-catchers defended bets at HU frequency
      regardless of field size. Added `_MW_CATCH_TIGHTEN = 1.15` applied as
      `fold_merit *= 1.15 ** max(opponents-1, 0)` on the facing-a-bet path only, scoped to catcher
      buckets (AIR, ACE_HIGH, MIDDLE_PAIR) — a direction multiplier, not a defense-share constant
      (guard test greps source for `1/opponents` MDF patterns and bounds the constant). HU behavior
      byte-identical (refuter: 1920 paired samples, exact; exponent 0 at opponents=1). F1 α-ceiling
      test HU-scoped by construction, unaffected. coverage_baseline re-recorded 1196/242→1266/231
      (refuter reproduced exactly, double-grading spot-check clean). Refuter PASS (1 LOW:
      passive_fish WTSD floor margin thinned 0.084→0.024 — inside band, 5×71/71 stable; noted for
      RES-D §4 re-anchor if later slices add multiway fold pressure). 742 backend tests + ruff +
      verify.sh green.)* ICE 6·6·5.

- [x] **F5 — Theory-calibrated hero grading + re-derived S4 bands (fixes hero grading; bakes the A1
      guardrail).** Route the re-derived RES-D bands through the async `StrategyProvider`/`grade_map`
      so hero grading is **price-aware** and uses α as a **fold-ceiling sanity check** — explicitly NOT
      a fold≈MDF assertion on flop/turn or vs capped/polar bettors. Re-anchor the S4 bands in
      `test_personas_postflop.py` to theory. **Pass/fail:** the grader no longer marks a
      theoretically-correct **below-MDF fold** as wrong on the flop/turn (A1 regression test); a hero
      call/fold facing different sizes grades against pot-odds + the fold-ceiling (not merit alone);
      grades stay freq+EV with EV labeled *approximate*; all `grade_map`/S10 tests green. **Appetite:**
      ~1 slice. **No-gos:** grading stays behind the one provider seam; no boolean verdicts; no
      exploit/persona-aware grading (that's L1). ICE 9·7·5.
      *(Done 2026-07-22, PR #70. Audit: the `_merits_vs_*` functions already carried linear price
      terms, so the real gap was α-anchoring — pre-F5 the marginal catcher's graded fold share ran
      well OVER the ceiling (weak_made vs ¾-pot: ~0.74 vs α=0.43; the grader recommended
      over-folding). Fix: `_calibrate_catcher_fold` (postflop.py), a merit-space clamp bounding the
      weak_made tier's FOLD share into [min(0.25, α), α] using size-exact α — which equals `price`
      since the facing-node pot includes the faced bet (RES-E §2), so no duplicated bucket
      constants. Applied in `grade_vs_cbet` + `grade_vs_turn_bet` only, before `_apply_multiway`
      (multiway may fold past the HU ceiling per F4). A1 floor: fold credit 0.25 (α at SMALL,
      RES-D §1a row 1) > POST_MIX 0.20 ⇒ a below-MDF flop/turn fold grades ≥ ACCEPTABLE via the
      frequency rule (A1 regression test cites RES-D §1c/§5.2). Deviations, documented in-code:
      (1) per-hand α as proxy for the range-aggregate ceiling, scoped to weak_made (air may fold
      above α; strong-hand folds stay punished — scope-guard test); (2) `grade_vs_check_raise`
      exempt (RES-D §1c: α is the flat-call form); (3) river untouched (RES-D §5.2 scopes the rule
      to flop/turn); (4) S4 bands NOT re-anchored again — F1–F4 already did, personas byte-
      untouched. Refuter cycle: initial FAIL (HIGH — docstring promised an unconditional
      ACCEPTABLE floor but α<0.25 tiny bets fall to the EV ladder; reachable via the drill path's
      arbitrary bet fracs). Adjudicated behavior-correct: α-ceiling and 0.25-floor are jointly
      unsatisfiable below ⅓-pot, the ceiling is the binding A1 contract, and folding a catcher at
      ~12:1 is a genuine mistake — docs re-scoped to α ≥ 0.25 and tiny-bet / POST_MIX-boundary /
      degenerate-α behavior pinned by 3 regression tests. coverage_baseline unchanged (grading ≠
      mappability). 751 backend tests + ruff + verify.sh green, 3× stable.)*

- [x] **F6 — Min-bet legality fix (from RES-F).** *(done 2026-07-21: RES-F Option 1 verbatim —
      `sim_session.py::_hero_postflop_size_bb` `HERO_NODE_SIZE` miss (donk/lead, probe, delayed
      c-bet — any non-aggressor node) now falls back to the street's small `POSTFLOP_BET_FRACS`
      fraction × pot instead of returning None, clamped caller-side into the legal [min_bb, max_bb]
      bracket; collapse ⇒ single legal size, no fabricated second option. `engine.py` UNTOUCHED —
      1BB stays the legal min (correct NLHE rule; the bug was the offer). Refuter PASS (0 issues):
      single caller, FE `size_bb ?? min_bb` backward-compatible; graders gate on hand shape never
      offered size ⇒ no mis-grade possible (donk/lead structurally fails every BET grader → honest
      "no baseline yet"); fallback provably reachable only on the unmapped `flat` node; preflop
      structurally unreachable; stash-check proved both new tests fail on old code. Tests:
      donk-lead 24.5BB pot offers ≈⅓-pot in-bracket; short-stack clamp collapses to single legal
      size. 698 backend tests + ruff green. Note: RES-F corrected the slice's presumed touch-list —
      fix lives in `sim_session.py`, not `sizing.py`/`play.py`.)* ICE 7·6·6.

### After the Build slices — sequenced, NOT yet spec-ready

> Promoted to its own slice ONLY if a spike shows it's the root cause; otherwise handled inside F1/F3.

- [x] **F7 — Finer hand-strength ladder (coarse-ladder smoothing).** *Evidence:* the 7-rung analytic
  ladder (`strength_bucket` AIR→…→MONSTER) can create action *cliffs* at bucket edges that F1/F3 may
  only partly mask. *Open questions (spike-gated):* is the coarseness a *root* cause of any residual
  unrealistic decision after F1–F5, or cosmetic; would a finer/interpolated ladder change grades
  enough to matter; does it touch `spot_signature()` (must not). **Do NOT hand to `/ai-dlc` until
  F1–F5 land and a diagnostic shows a real cliff.** *(Ranked lowest in Epic 4; may close as "not
  needed" if F1/F3 resolve the observed behavior.)*
  *(Resolved 2026-07-22, PR #71. Diagnostic ran post-F1–F5 (deterministic exact-distribution +
  N=2000 sweeps, 3 boards, 2 personas; hero-grading sweeps; scratchpad-only): **finer ladder =
  NO-GO** — within-bucket flatness is structural (the ladder is the bot's only hand input) and most
  boundary jumps align with real strategic thresholds (pair vs no-pair, monster edges); rung count
  is not the root cause. `spot_signature()` confirmed untouched by either ladder (srs.py hashes
  texture/SPR/faced-bucket, never hole cards). The diagnostic instead root-caused the two worst
  unrealistic behaviors (cliff ratios 8–38× the equity jump) to **two paired-board classification
  rules, both fixed in this slice**: (1) `strength_bucket` classed an under-pocket-pair on a paired
  board as TWO_PAIR_PLUS — tag raised 22 on 883r at .734 facing MEDIUM (equity .375); now
  TWO_PAIR_PLUS only when the pocket is the top pair of the best five, else MIDDLE_PAIR — tag
  raise .199/fold .203, sane vs true middle pairs. (2) `_hand_category` classed one-hole-card trips
  as `weak_made` — folding 98 on 883r (.94 equity) graded ACCEPTABLE with raise freq 0 (and F5's
  clamp then pinned its fold at α); trips → `strong`, boat-vs-trips grade inversion gone. Refuter
  PASS, 0 issues: exhaustive 10,504-combo (bot) + 44,616-combo (grader) pre/post audit — ONLY the
  claimed transitions occur, no AIR/ACE_HIGH membership changes, unpaired boards byte-stable;
  bonus: A3-on-8833x boat was also misclassified weak_made pre-fix, now correctly strong. Maniac
  ftc band top re-anchored 0.430→0.56 per RES-D §4 (post-fix center ~0.40–0.44 clipped the old
  top; refuter confirmed necessity + all other bands hold). coverage_baseline re-recorded
  1266/231→1233/242 (refuter isolated: Bug 1 alone drives the delta; graded share rose 18.2%→19.6%
  — more catcher-class spots mappable). All 5 new tests proven to fail on pre-fix code. 757
  backend tests + ruff + verify.sh green, 3×/5× stable.)*

---

## NOW — Epic 5: Multiway coverage — limped pots, activated 3-way grading, 4+-way directions, caller re-raises (added 2026-07-22)

> Fifth epic on the shipped Simulate table. Same north-star. Epics 1–4 built the table, the
> grading pipeline, and correct decision math — but the N5 census shows the biggest remaining
> ungraded pile is **multiway**: limped pots (~45% of MW volume, zero reference material),
> N5's 3-way mappers firing ~0 live, 4+ player fields, and the caller-raises-your-c-bet node.
> **Grounded on three fresh research spikes (all done 2026-07-22, all sim-measured):**
> `docs/ai-dlc/research/RES-G-limped-pots.md`, `RES-H-mw-extension.md`, `RES-I-mw-funnel.md`.
> Spike docs are LAW — build slices copy from them; refuters verify against them.
>
> **Interview decisions (locked 2026-07-22):** scope = ALL FOUR shapes (limped pots · activate
> 3-way graders · 4+ fields · caller re-raises) · **research first** (spike docs become law) ·
> **fully autonomous** run (worker→refuter→stacked PRs, user merges at end).
>
> **Cross-cutting law (carried from RES-D/Epic 4 — inject into every slice brief):**
> - Multiway = **DIRECTION only** — never per-opponent MDF / n-th-root constants. F4 precedent:
>   geometric `base ** max(opp-1, 0)` multipliers.
> - α is a fold-**CEILING** (flat-call form). **α does NOT apply to responding to a raise**
>   (RES-H §3.4) — a capped value-heavy raising range is graded on pot-odds-vs-actual value:bluff.
> - "No baseline yet" (`None`) is a first-class answer — never silently HU-grade a multiway pot
>   or fabricate a 4-way frequency.
> - Domain purity · `spot_signature()` frozen · freq+EV never boolean · EVs approximate ·
>   `StrategyProvider` seam · frequency-mixed never argmax · anti-sizing-tell.
> - **RES-E is live law:** any newly recognized faced size (M1-L4) must map to a defined
>   RES-E bucket/price — never silently collapse into the 0.33 bucket (RES-I §5, HIGH flag).
> - S4 band stats: M1/M2 levers change ZERO bot behavior (content + recognition only) —
>   lineup and open-band levers were measured zero-effect and are **rejected** (RES-I §4).

### Research spikes (front-loaded, parallel — output = decision doc + numbers, no app code)

- [x] **RES-G — Limped-pot baselines ($2/$3).** *(done 2026-07-22,
      `docs/ai-dlc/research/RES-G-limped-pots.md`. Measured (3 seeds × 3000 hands): limped pots =
      **41.8% of all flops** (~274/1000 hands), **69% multiway** (modal 3-way 47%, HU 31%); ~90% of
      limps from passive_fish + calling_station (persona limp levers already well-authored — no bug).
      Headline: limped pots are **already partly built** — `limp` is a first-class engine action and a
      `vs_limpers` content pack + working `_map_vs_limpers` iso/over-limp grader exist, but content
      only covers CO×1, BTN×1, BTN×2. Postflop is a hard "no baseline yet" everywhere (hero must be
      sole preflop raiser; HU-only). Delivered copy-ready, schema-validated `vs_limpers` JSON for the
      missing seats (§3), BB-check direction (§3d), HU limped-flop postflop directions (§4b),
      feasibility map (§5), slice cut A→B→C→defer-D (§6). Sources: Upswing 4bb+1/limper, GTO Wizard.)*

- [x] **RES-H — 4+-way directions + caller-re-raise grader design.** *(done 2026-07-22,
      `docs/ai-dlc/research/RES-H-mw-extension.md`. Measured (N=6000 seeded): 4+-way flops = 11.8% of
      hands (10.0% four-way, thin 5/6-way tail). **N5's "BB closes" rule is NOT general** — BB is last
      responder to a MW c-bet only ~17% overall, ~53% in the SRP cold-caller shape → any 4-way
      extension must gate on the ACTUAL closing seat (verified by sims per the N5 lesson).
      **Caller-raises-c-bet = 16.8 decision points/1000 hands** — the most reachable uncovered
      postflop node (~5× BB check-raise, ~9× the N5 3-way mapper). Web-confirmed NO published 4-way
      baseline exists → extend F4-style geometric multipliers inside `_apply_multiway`, direction-only,
      HU/3-way byte-identical (§2). Caller-re-raise grader design (§3): sibling of
      `grade_vs_check_raise`, value-skewed prior (cold-caller range capped → raise ≈ sets/two-pair,
      sourced), **α explicitly NOT applied** (§3.4). Slice cut: H1 caller-re-raise first (high
      confidence, high reach), H2 4-way second (§5).)*

- [x] **RES-I — 3-way mapper funnel diagnostic (fresh, post-Epic-4/#53/#54).** *(done 2026-07-22,
      `docs/ai-dlc/research/RES-I-mw-funnel.md`. ~180k hands, 18 seeded configs, instrumenting the
      REAL `map_decision_point` path with in-process monkeypatch counterfactuals; hero proxied
      tag (tight bound) / calling_station (loose bound). **Refutes the N5-refuter MED hypothesis:**
      persona mix and open band are ~zero-effect post-Epic-4 (0 band kills; fires flat across
      lineups) — both levers REJECTED. Real chokes: hero-seat scope (BB-only → 0.7–3.7 MW pots/1000),
      strict line/size gates, and **12 missing `VS_RFI` caller pairs** (killed 100% of baseline
      canonical arrivals). Even with every in-scope gate relaxed, BB-only fires cap at ~1.5–3.2/1000.
      Threshold set at **≥5 graded MW decisions/1000 hands** (≈1 rep per session; N7-rankable at
      2–3k hands); reachable only via hero-seat widening (measured ceiling 6–11/1000, not built).
      Recommends: M1 = L3 (content pairs) + L4 (size-grid recognition) with a **≥30k-hand re-measure
      gate**; L5 hero-seat widening = separate go/no-go slice decided on that measurement (§4).
      HIGH flag: L4 must extend RES-E faced-size buckets, and `_is_canonical_bet` blast radius hits
      HU turn/river mappers + S10/S11 display==grade gates (§5).)*

### Build slices (ICE = Impact·Confidence·Ease, 1–10)

- [x] **M1 — MW funnel levers: `VS_RFI` content pairs + size-grid recognition (RES-I L3+L4).**
      *(done 2026-07-22, PR #73. 12 new VS_RFI pairs (UTG1/UTG2 equal-shape to UTG per RES-A
      precedent; LJ rows per doc-05 §3.3, containment parser-verified); new recognition-only
      `RECOGNIZED_BET_FRACS=(0.33,0.5,0.75,1.0,1.5)` consumed by `_is_canonical_bet` — graders
      already price the TRUE faced amount so RES-E needed no grader change (pinned by tests);
      off-grid still None (grid gaps ≥0.17·pot vs 0.06bb tol — double-match impossible). Mapper
      fires 1→9/2000-hand belt. **30k re-measure: tag 0.23–0.27, station 1.93–2.73 per 1000 —
      below ≥5/1000 threshold ⇒ RES-I §6 records GO for M7.** Zero bot-behavior change (baseline
      total 1233 stable, graded 242→267). Refuter PASS 0 issues. 765 tests 3× stable.)*
      (I8·C8·E7) **Scope:** author the 12 missing `VS_RFI` caller pairs (RES-A-grade ranges, not
      filler — they're grading baselines + Practice content); widen `_is_canonical_bet` size
      recognition to the persona grid, extending RES-E bucket/price treatment to newly recognized
      0.5/1.0-pot faced bets (never collapse into 0.33). Hero OFFERED sizes (`POSTFLOP_BET_FRACS`)
      stay 2-button. **Pass/fail:** (a) 3-way mapper fires move ~0 → measurable (RES-I §3 bands);
      (b) **≥30k-hand seeded re-measure** with the RES-I harness reports the fresh rate + which hero
      proxy it assumes; (c) every newly recognized faced size maps to a defined RES-E bucket (test);
      (d) S10/S11 display==grade invariant re-verified; (e) zero bot-behavior change (S4 bands
      byte-stable); verify.sh + build green; refuter PASS.
- [x] **M2 — Limper iso/over-limp coverage fill (RES-G Slice A, content-only).**
      *(done 2026-07-22, PR #74. 6 entries added (pack v1→2): faces-1 @ UTG2/LJ/HJ/SB, faces-2 @
      CO/SB — verbatim from RES-G §3 with ONE refuter-forced correction: the spike authored the EP
      entry at "UTG", which is organically unreachable (first non-blind to act) AND live-broken in
      Practice (`build_spot` seats limpers from `_before(position)`; `_before(UTG)==[]` → phantom
      limp chip, empty history). RES-G §1d itself measured UTG2 → entry renamed UTG2 (fires 99/4000
      organic hands); correction note added to RES-G. New belt test (all 6 pairs fire) + build_spot
      coherence test over EVERY vs_limpers entry (would have caught the bug; sed-revert-proven).
      Baseline total 1233 stable, graded 267→313. Refuter PASS-w-issues, both folded. 767 tests.)*
      (I8·C9·E9)
      **Scope:** add the missing `vs_limpers` entries from RES-G §3 (UTG/LJ/HJ/SB ×1; CO/SB ×2);
      bump pack version 1→2; zero code. **Pass/fail:** RES-G §6-A verbatim — named (position,count)
      pairs map where they returned `None`; coverage graded count UP, total UNCHANGED; schema-valid;
      `spot_signature()` + `TAXONOMY_VERSION` untouched.
- [x] **M3 — BB-check node vs limpers (RES-G Slice B, small new grader).**
      *(done 2026-07-22. BB×1/2/3 vs_limpers entries (pack v2→3) {raise, check} — NO fold leg;
      ranges are [DERIVED-ASSUMPTION] per RES-G §3d direction (no copy-ready JSON existed): iso
      tightens 55+→77+→99+ with count, 4bb+1/limper sizing, check = complement. build_spot hero-BB
      branch (SB folds at chronological slot; legal = CHECK+RAISE). **Documented deviation:** the
      roadmap's "lift the blind-seat gate" needed NO code change — the gate keys on the LIMPERS'
      seats (only excludes SB-complete), never hero's; BB×N was dark purely for missing content
      (refuter-verified). Real gate lifted = `grading.py` synthetic-FOLD append: new `check_is_free`
      fallback (CHECK offered + no FOLD → unassigned chart mass checks, no phantom fold eval) —
      refuter proved unreachable for every pre-existing node (grade() is preflop-gated; only
      vs_limpers BB entries author "check"). SB-complete stays None (SB's CALL carries a blind
      position — gate catches it unconditionally). BB fires 80/54/10 per 4000 organic hands; 9
      pre-M3 belt counts pinned identical. Baseline total 1233 stable, graded 313→327. Refuter
      PASS 0 issues incl. live API round-trip (no FOLD offered/evaluated). 777 tests 3× stable.)*
      (I6·C7·E6) **Scope:**
      BB `vs_limpers` entries with `{iso, check}` (NO fold leg — checking is free), `build_spot`
      branch seating hero=BB behind limpers, lift the blind-seat `None` gate for BB-check only.
      **Pass/fail:** RES-G §6-B verbatim — BB facing 1–3 limpers grades iso vs check freq+EV; fold
      never offered; all non-BB limped shapes byte-unchanged.
> **RUN PAUSED HERE (2026-07-22, user call: token budget).** M1–M3 shipped; M4–M7 below are
> spec-ready and unstarted — resume by handing M4 to the standard worker→refuter cycle on a branch
> off the tip of the merged chain. Note for M7: its go/no-go input already exists (RES-I §6 M1
> re-measure = GO — L3+L4 landed 0.23–2.73/1000 vs the ≥5/1000 threshold; L5 build is warranted).

- [x] **M4 — Caller-re-raises-c-bet grader (RES-H H1).** *(done 2026-07-22, W1 PR — `feat/epic5-m4-m5`.
      `_merits_vs_caller_raise` + `grade_vs_caller_raise` (check-raise sibling; fold baseline 1.9 vs
      1.6, halved bluffy/semibluff credits, §3.2 value-skewed prior) + `_flop_caller_raise_preflop`
      gate + `map_flop_vs_caller_raise` (SRP, hero=opener, non-BB caller RAISED the canonical c-bet,
      hero faces/closes; incremental CALL leg = raise_to−cbet; `_calibrate_catcher_fold` NOT called).
      Fires 11/2000 any-seat-as-opener (in-band; 16.8/1000 is the any-seat upper bound). NodeContext/
      LeakCategory=207 additive; provider routing additive; spot_signature frozen. **Refuter FAIL→1
      HIGH fixed:** the weak_made CALL term halved `bluffy` unconditionally — on dry boards bluffy<0
      so halving SHRANK the penalty → caller-raise folded LESS than check-raise at price≥0.4
      (asymmetry inversion). Fix: halve the CREDIT on wet, keep FULL penalty on dry
      (`(bluffy*0.25) if bluffy>0 else (bluffy*0.5)`); 231-cell grid scan 0 inversions. 796 tests.)*
      (I8·C8·E5) **Scope:**
      `_merits_vs_caller_raise` + `grade_vs_caller_raise` (sibling of `grade_vs_check_raise`) with
      the §3.2 value-skewed prior; `map_flop_vs_caller_raise` mapper (SRP, hero=opener, canonical
      c-bet, non-BB caller raised, hero faces/closes); `_calibrate_catcher_fold` NOT called.
      **Pass/fail:** RES-H §5-H1 verbatim — incl. fires ≥~5/1000 in-band (measured 16.8);
      range-asymmetry direction test (fold freq ≥ check-raise grader's for fixed marginal hand);
      α-not-applied assertion; off-shape lines return `None`; HU/3-way hash-pins unchanged.
- [x] **M5 — HU limped-pot flop grader (RES-G Slice C, new node family).** *(done 2026-07-22, W1 PR
      — `feat/epic5-m4-m5`. App's FIRST limped-pot postflop grader, HU only. `_limped_flop_hu_preflop`
      gate (0-raise pot, PREFLOP-entrant count==2 — derived from preflop actions not flop statuses;
      3+-entrant OR degraded-to-2-live → `None`) + `map_limped_flop_lead`/`map_limped_flop_vs_lead` +
      `grade_limped_lead`/`grade_limped_vs_lead` (§4b directions as DATA in new `content/postflop/
      limped.json` v1; small polar lead, mostly-check OOP, texture edge from score=0). Fires ~86 lead
      / ~21 vs-lead per 1500 organic hands. Additive/append-only (raised-pot byte-unchanged),
      spot_signature frozen, NodeContext/LeakCategory=208/209, provider routing additive, schema
      regenerated. **Refuter FAIL→1 HIGH fixed:** the draw RAISE merit was flat/price-independent
      while call+fold decayed with price → RAISE won for a draw at big bets even on dry/villain-edge
      (inverts §4b's "defend draws at a price; semibluff only wet+hero-edge"). Fix: cap draw-raise ≤
      draw-call outside the wet+hero-edge §4b condition + bump `value.draw` 1.2→1.4 so CALL beats FOLD
      to 1.0-pot; sweep confirms RAISE best ONLY in wet+hero cells. Deviation from spec: gate keys on
      PREFLOP-entrant count (not flop-live) so degrade-to-2 stays `None` — refuter-verified airtight.)*
      (I7·C6·E4) **Scope:**
      first limped-pot postflop grader, **HU only** (the tractable 31%); `map_limped_flop_lead` /
      `map_limped_flop_vs_lead` per RES-G §4b directions. **Pass/fail:** RES-G §6-C verbatim —
      0-raise HU flop grades freq+EV; **any 3+ limped flop still returns `None`** (explicit
      `len(live) != 2 → None`); raised-pot graders byte-unchanged; flop only (no turn/river v1).
- [x] **M6 — 4-way merit extension (RES-H H2, direction-only).** *(done 2026-07-22, W2 PR —
      `feat/epic5-m6`, stacked on W1. `_apply_multiway` gains a required `opp` kw; each `_MW_*`
      scalar → `base ** max(opp-1,0)` with `base` = the exact pre-M6 flat constant (so opp=2/3-way
      ⇒ `base**1` bit-identical, opp=1/HU never enters the gate) — new `opponent_count(spot) =
      players_in_pot-1` threaded through all **10** call sites. `_mw_srp_preflop` generalized from
      1 to 1–2 cold-callers (3+ → None), `_mw_check_bet_*` require a response from EVERY caller
      between the opener's bet and hero (action-order closing gate — never "BB closes"); `map_mw_*`
      pot math n-way. 4-way-hero-closes now maps+grades; 4-way with a live player behind hero → None;
      5+ → binary bucket. Reverses the N5 "4-way stays None" pin (intended). **Refuter PASS** (0
      HIGH/MED; 2 LOW doc-staleness fixed) — independently confirmed byte-identity via `float.hex()`
      in a second worktree, proved BB structurally always closes inside `_mw_srp_preflop`'s gate
      (no §1.2 leak), monotone 2→6-way. 822 tests 3× stable.)*
      (I5·C5·E6) **Scope:**
      `_apply_multiway` scalars become opponent-count-aware via geometric `base ** max(opp-1, 0)`
      (F4 shape); extend `map_mw_*` to fire when hero closes a **4-way** SRP shape, gated on the
      ACTUAL closing seat (never "BB closes"); 5+ stays binary bucket / "no baseline yet."
      **Pass/fail:** RES-H §5-H2 verbatim — HU byte-identical (opp=1 ⇒ scalar 1.0) AND 3-way
      byte-identical (base pinned); monotone-in-opponents invariant; direction-only (no MDF
      constants); 4-way with live player behind hero returns `None`.
- [ ] **M7 — Hero-seat widening go/no-go (RES-I L5) — gated on M1's 30k re-measure.** (I7·C4·E3)
      **Scope:** decision slice: if M1's re-measure leaves graded-MW below the ≥5/1000 threshold
      (expected: L3+L4 alone cap ~0.3–3/1000), build opener + caller MW mappers (measured ceiling
      6–11/1000); else close as not-needed. **Pass/fail:** the go/no-go is decided FROM the M1
      measurement (documented in the done-note); if built: threshold met at ≥30k hands with stated
      hero proxy; existing BB-path outputs byte-unchanged; refuter PASS.

### After the Build slices — sequenced, NOT yet spec-ready

- **Multiway limped-pot postflop (RES-G Slice D) — DEFER.** The app's first multiway postflop
  grader (69% of limped pots). Deepest lift in the app; natural trigger to revisit the
  solver-baseline no-go; stays honest "no baseline yet" until M1–M5 land and real usage justifies
  it. Probably its own epic (RES-G §6-D).

---

## NEXT — validated problems / opportunities (not yet spec'd)

- **Exploit-aware grading layer.** *(gate-mandated follow-on; → promoted to Epic 3 **L1**)* *Evidence:* personas are
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
- **Sizing + postflop coverage beyond the "c-bet-and-called" line.** *(user ask 2026-07-16:
  "will there ever be a way to understand optimal strategy/sizing for the other scenarios
  beyond flop c-bet?")* *Evidence:* the heuristic graders cover only ~7 node families
  (flop c-bet/vs-c-bet/vs-check-raise, turn barrel/vs, river barrel/vs), ALL on the single line
  "opener c-bet the flop and got called." Every other live shape — **donk/lead bets, delayed
  c-bet, probe bets, hero-as-check-raiser, 3-bet/4-bet pots, limped pots, short-SPR jams,
  overbets** — has no grader and shows "no baseline yet" forever (RES-C §12's non-spot list).
  R3b + R5 push the frontier (preflop 4-bet-vs-shove sizing; turn/river barrels) but do NOT
  lift this ceiling. *Candidate slices:* per-node-family heuristic graders for donk / 3-bet-pot /
  delayed-c-bet / check-raiser, each with content-pack thresholds + a grade_map mapper + an
  R5-style chart; more sizing nodes into R3b's framework. *Open questions:* authoring volume
  (each family is a mini-slice); how many families before diminishing returns at $2/$3; does the
  heuristic stay defensible that deep, or does this become the trigger to revisit the
  solver-baseline no-go. **Hard ceiling:** truly optimal-for-every-spot sizing/strategy needs
  the **solver-grade baseline** (LATER bet below) — heuristics get "simplified-but-winning,"
  never GTO-exact; EVs stay labeled approximate throughout.
  **Two concrete gate-coverage followups surfaced by W1 (2026-07-16, R5 combined-refuter):**
  (a) ~~`map_flop_cbet` still uses an EXACT per-seat open gate…~~ **DONE 2026-07-19 → PR #53 + #54.**
  #53 widened the preflop facing-open band to the oversize cap 4.5bb (`_OVERSIZE_OPEN_CAP`) so
  oversized persona opens (station/fish/maniac 3.5–4.5) grade preflop; #54 aligned all three
  postflop open gates (`map_flop_cbet`, HU-SRP, 3-way-MW) to the same 4.5bb cap so an oversized
  open now grades preflop AND flop/turn/river on one line — no more graded-preflop-but-blank-flop
  split. S10 grade_map tests re-verified (692 green). EVs stay ≈approximate (grading a 4.5bb open
  against the 3.0-open chart is coarser). (b) `map_vs_turn_bet`/`map_vs_river_bet` almost never fire
  organically: bots bet `round(frac*pot, 2)` (`personas_postflop.py:350`) but the mapper's
  `_is_canonical_bet` demands the 1-dp bucket within 1e-6 — so hero-as-BB turn/river charts are
  near-empty in live play. Fix = either snap bot postflop bets to the 1-dp bucket, or widen the
  mapper's bet gate to nearest-bucket tolerance (risks mis-labeling a 0.5-pot bet as a 0.33
  node — needs care). Both are coverage (safe "no baseline yet"), not correctness.
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
