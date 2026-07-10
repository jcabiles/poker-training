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

- [ ] **S4 — Persona postflop engine + live-texture calibration.** ICE 9·6·3. *(Track B, W3 — strictly after S2+S3: its tests need the finished hand engine)*
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

- [ ] **S7 — River graders: value/bluff + facing river bets.** ICE 8·6·4. *(Track C, W3 — after S6)*
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

- [ ] **S8 — Multiway grading extension.** ICE 7·5·3. *(Track D, W4 — strictly after S7; same files as C track)*
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

- [ ] **S9 — Hero plays: session persistence, stacks, ledger.** ICE 9·7·4. *(Track E, W4 — strictly after S4: full hands need postflop bots)*
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

- [ ] **S10 — Grading wired in: live badge + end-of-hand recap + tagged attempts.** ICE 10·7·4. *(Track E, W5 — needs S9; consumes whatever graders exist)*
      **Problem:** the key value — Practice-grade verdicts inside the game — isn't wired.
      **Outcome-link:** primary metric becomes measurable in-sim.
      **Solution:** map each hero decision to a `Spot`, grade via the existing provider stack
      (baseline only), store verdicts on `sim_decision`; unmapped spots stored + shown
      "no baseline yet"; during hand: color badge per decision (verdict tier, no pause); hand
      end: per-street recap with freq/EV (≈ labels) + tiered "why" expanded for
      mistakes/blunders; attempts recorded tagged `source=simulate` — **`drill_attempt` has
      no `source` column today (verified), so this slice ships an additive Alembic migration
      adding it (default `'practice'`)** and threads it through `record_attempt` in
      `services/review.py` + stats reads; **no SRS writes**.
      **Pass/fail:** a deliberately-bad preflop play shows a red badge + blunder recap with
      reasoning; unmapped spot renders "no baseline yet"; migration applies up/down clean and
      existing attempt rows read back unchanged; attempt rows carry the simulate tag and
      appear in stats; zero SRS rows created (test); `verify.sh` + build green.
      **Appetite:** ~1 epic. **No-gos:** no exploit-aware verdicts; no SRS; recap only —
      no session-report view.

- [ ] **S11 — Pacing + table feel polish.** ICE 6·8·6. *(Track E, W6 — last)*
      **Problem:** instant 8-bot action is unreadable; folded hands waste time.
      **Outcome-link:** "feels like a real game" — the premise.
      **Solution:** randomized bot delays (~0.5–1.5s) with normal/fast/instant setting;
      hero-fold ⇒ instant resolution into the ledger + auto-deal next; tokens-only styling
      pass; `design-reviewer` run on the table across themes/breakpoints.
      **Pass/fail:** speed setting observably changes pacing; fold skips ahead; design-review
      verdict acceptable (AA contrast + focus both themes); build green.
      **Appetite:** ~1 small epic. **No-gos:** no sound; no avatars/art beyond badges; no
      animation library without ask-first.

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
- **SRS integration for Simulate spots.** *Evidence:* sim blunders are exactly the reps worth
  scheduling; held out of v1 to protect the queue from off-depth/multiway noise.
  *Open questions:* which sim spots are signature-clean enough to seed; depth filter.
- **Hand replayer.** *Evidence:* per-hand persisted seeds make exact replay nearly free;
  recap covers only the freshest hand. *Candidate slices:* session hand list → step-through
  replay with verdicts.
- **Hidden-persona mode + read tagging.** *Evidence:* gate decision — visible badges v1,
  read-development later. *Open questions:* does tagging need showdown-history support.

## LATER — bets / outcomes (unexplored · NO hard dates)

- **Bet: selectable table textures** (aggro online 9-max calibration as a second content
  set). *Segment:* self · confidence: med · assumptions to test: does the live-$2/$3 table
  keep producing enough 3-bet/4-bet reps, or is a tougher lineup wanted? · review-by: after
  ~2 weeks of real Simulate use.
- **Bet: depth-aware persona ranges + depth-aware grading** (beyond SPR commit logic).
  *Confidence:* lo · assumptions to test: how far stacks actually drift in real sessions
  (ledger data will show) · review-by: after carry-over sessions accumulate.
- **Bet: session analytics** (winrate graph, positional/street breakdown per session).
  *Confidence:* med · assumptions to test: does the recap + leak stats already answer it ·
  review-by: after S10 ships.
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
