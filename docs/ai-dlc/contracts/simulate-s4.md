# Contract map — S4 persona postflop engine + live-texture calibration (at HEAD 2026-07-10)

> Read-only scan by contract-mapper on `feat/simulate-wave2` (S2 engine + S3 preflop personas
> + S6 turn graders all present). Slice S4 of `docs/ai-dlc/roadmap/simulate-table.md`.

## Contracts

**C1. PersonaPack has ZERO postflop fields — greenfield schema, not extension.**
`content/models.py:113-118` PersonaSizing{open_bb, threebet_mult, fourbet_mult} (preflop
only); `:121-128` PersonaPack{id, version, domain, persona, display_name, sizing, preflop}.
No aggression/stickiness/bluff_freq/SPR-threshold/multiway-dampener anywhere in models or
the 6 packs. S4 adds a new top-level field (e.g. `postflop` levers block). Hazard:
`_node_ordering` validator (`:130-154`) covers only `preflop` — new structure needs its own
validator without weakening the preflop first-match-wins guarantee.

**C2. Pack validation gate = Pydantic only; `persona.schema.json` is stale/decorative.**
Nothing regenerates it (zero refs to `model_json_schema()` for personas). Real gate:
`PersonaPack.model_validate_json` in `load_persona_packs` (`personas.py:40-53`) + duplicate
check (`:50-51`). Unresolved since S3 — spec must decide regenerate vs declare decorative.

**C3. `sample_preflop_action` is the pattern to mirror** (`personas.py:61-91`): rng-injected,
first-match-wins node scan, first-mix-containing-hand, implicit fold remainder,
`rng.choices`, content-name→wire translation via `_WIRE` (`:25-33`) — content never sees
ActionType. Hazard: `PersonaAction = NamedTuple(name, action)` (`:35-37`) has NO size —
postflop needs size attached; keep name (content) vs action (wire) split.

**C4. RNG: caller-injected `random.Random`, last arg, never module-level** (`personas.py:3-6`).
Postflop sampler must take the SAME hand's rng — no fresh Random per decision (breaks
same-seed determinism in the closed-loop test).

**C5. No EHS / 7-rung ladder exists — largest net-new surface.** `_hand_category`
(`postflop.py:179-233`) = 4 coarse buckets (strong/weak_made/draw/air), draws undifferentiated,
private. Zero EHS/PPOT/outs code repo-wide. Build fresh from `best7`/`_eval5` rank tuples
(`equity.py:30-79`) + `texture.classify` idioms — cheap analytic, no Monte-Carlo.

**C6. `equity_vs_range` = MC 2000 iters/call (`equity.py:111-145`) — too slow for the
per-bot-decision hot loop** at closed-loop volume (10k hands × personas × multiple decisions).
Reserve for grading UI; strength bucket must be deterministic/analytic.

**C7. Engine reads ONLY `Decision.size_bb` (raise-TO)** — `engine.py:277-278` raises
"engine requires size_bb"; `size_fraction` is dead weight to the engine. Persona pot-fraction
sizing must resolve to absolute bb before Decision.

**C8. LegalAction bracket is the hard boundary:** `engine.py:168-206` emits [min_bb, max_bb]
raise-TO brackets (2dp); `:284-287` rejects sizes outside. Jam encoding collapses
min==max (`:168-173`). No helper maps "X% pot" → legal size_bb — S4 writes the clamp/snap
translation.

**C9. AF / fold-to-cbet derived, not read:** `HistoryAction{street, position, action,
amount_bb}` (`spot.py:108-112`) — no seat/hero flag; harness cross-references
`SeatState.position` via `positions_for_button`. **WTSD direct:** `Settlement.showdown_seats`
(`engine.py:75`). Fold-to-cbet = fold rate facing street==FLOP BET as non-aggressor — new
analysis code; spec must pin exact formulas.

**C10. Purity allowlist module-exact** (`test_domain_purity.py:12-15`, 15 entries incl.
`app.domain.personas`, `app.domain.table.engine`). Note pre-existing gap: equity/postflop/
texture absent (transitively covered only). New `personas_postflop.py` needs an explicit
entry; growing `personas.py` in place needs none.

**C11. Two different SPR concepts — do not conflate.** `srs.spr_bucket` (`srs.py:36-45`)
buckets `Spot.spr` for the FROZEN SRS signature. S4's SPR-commit-threshold lever is live
`HandState` stack/pot at decision time — must never touch srs.py/Spot/spot_signature.

## Integration points

| Seam | Location | Note |
|---|---|---|
| sample_preflop_action / load_persona_packs | `personas.py:40-91` | preflop path stays byte-identical (S3 band test) |
| PersonaPack.sizing | `content/models.py:113-118` | add sibling postflop block; don't repurpose |
| start_hand/legal_actions/apply/settle | `engine.py:78,179,251,329` | sim harness drives this loop |
| Decision | `action.py:10-20` | size_bb required raise-TO |
| best7/_eval5 | `equity.py:30-82` | strength-bucket primitives |
| _hand_category | `postflop.py:179-233` | too coarse — build parallel, don't extend |
| texture.classify / turn_card_class | `texture.py:31-136` | slice boards deliberately (flop-only vs 4+) |
| purity allowlist | `test_domain_purity.py:12-15` | module-exact |
| S6 graders | `grading.py:96-118`, providers | must NOT read persona data (invariant) |
| srs.spot_signature/spr_bucket | `srs.py:28-68` | untouchable |
| test_engine._play_random_hand | `test_engine.py:381-396` | harness precedent — swap random policy for persona policy |
| test_personas bands | `test_personas.py:190-239` | preflop-only, cheap; postflop sim far costlier per sample |
| PRD §8 bands | `docs/ai-dlc/prd/simulate-table.md:172-184` | AF/fold-to-cbet/WTSD bands EXIST per persona; table-texture numeric targets roadmap-only |
| api/v1/simulate.py | — | does not call personas at all yet (S9 wires it) |

## Decisions the spec must freeze (ranked)

1. Postflop pack schema shape (facing vocabulary per street; node/mix vs lever-params vs
   both; strength-rung names referenced from content without numeric cutoffs in code).
2. Strength-bucket design (7 rungs + draw category; draw sub-granularity; analytic only).
3. Sizing-distribution → legal size_bb translation (sample within bucket, clamp to bracket,
   jam collapse; "no deterministic strength→size" pass/fail requires randomized-within-bucket).
4. Closed-loop test budget — full-hand engine playouts are costly; pick N + tolerances vs a
   slow-marker decision (unresolved since S3).
5. AF / fold-to-cbet / WTSD exact formulas against action_history + showdown_seats.
6. Module placement: grow personas.py (covered) vs new module (+allowlist entry).
7. persona.schema.json: regenerate or declare decorative.
8. Public vs private strength-bucket name (avoid third "private but test-imported" case).
