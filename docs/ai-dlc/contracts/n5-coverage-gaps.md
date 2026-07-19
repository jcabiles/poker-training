# N5 contract map — "grade every action" coverage gaps (read-only scan, 2026-07-18, on N4b branch)

Verified anchors at `feat/simulate-n4b-facing-raise-sizing` HEAD. Full None-gate inventory + reachability levers for N5. Companion probe data (3000 hands, hero-BB flop facing nodes): 155 multiway · 41 non-standard preflop · 16 oversized opens · 3 non-canonical c-bets · 2 no-content.

## None-gate inventory (headline findings)
- **`map_flop_cbet` exact-open gate STILL LIVE** (`grade_map_postflop.py:71`): demands the exact per-seat canonical open (`_EPS`), while `_hu_srp_preflop` (:203-204, shared by ALL other 6 postflop mappers) accepts the `[2.0, _STD_OPEN_CAP=3.0]` band — a standard 3.0 open maps the turn barrel but NOT the flop c-bet on the same line. The roadmap-named N5 gap #1; one-line-scale, additive-safe.
- **The other roadmap-named gap (bet-gate 1-dp vs bot 2-dp) was fixed in N4b** (`_CANON_BET_TOL=0.06`); residual = genuine off-canonical persona fractions. N5 pass/fail (a) belt-test should verify rather than assume.
- Preflop None-gates: villain-ALLIN line (fidelity) · limp-raise/cold-call (coverage, no content shape) · 5-bet+ (no-go) · **open band rejects calling_station 3.5 / passive_fish 4.0 / maniac 4.5** (`content/personas/*.json:7` — 3 of 6 personas structurally excluded as openers; band comment `grade_map_preflop.py:41-50` calls widening a FIDELITY tradeoff) · **`blind_defense.json` has only 5 entries** (BB-vs-{BTN,CO,UTG}, SB-vs-{BTN,CO}) — 9 missing cells (`_map_vs_open:125-127`), RES-A §7 flagged.
- Postflop None-gates: multiway `len(live)!=2` (`map_flop_cbet:50`, `_hu_srp_preflop:174-176`) · strict check→bet(→call/raise) shapes (donk/delayed-cbet/probe/hero-as-check-raiser — RES-C §12, NO grader families exist) · pot-continuity + short-SPR gates (fidelity).

## The 3 reachability levers
1. **(b) Blind-defense content fills — best bang/risk.** 9 missing cells; each missing cell CASCADES: `_srp_ranges`/`map_flop_cbet:85` read BLIND_DEFENSE, so one missing row kills flop→river continuation coverage for that opener. `_OPEN_SIZE` puts UTG/UTG1/UTG2/LJ at 3.0 (in-band tight-persona opens) — likely highest-frequency lever. Pure additive content (R4's proven pattern, RES-A monotonic-tightening); no code/schema/signature impact. Effort low-med, risk low.
2. **(a) Open-band widening (station/fish/maniac opens).** Numeric-only for signatures but the code's own comments call defense-range fidelity "shifts materially" past 3.0 — needs either wider-open content entries or accepted coarser approximation. Own sign-off required. Effort med, risk med.
3. **(c) Multiway mappers.** Grader side COMPLETE (`_apply_multiway` in all 7 families; dormant "mw" signature append `srs.py:157-161` proven byte-safe) but no mapper ever builds a MW Spot — `_hu_srp_preflop`/`_check_bet*` action-sequence gates are HU-shaped. Real design work (MW action order, MW-shaped ranges), S8's "MW never persists" note must be explicitly superseded + persistence sweep-tested. Largest single frequency bucket; highest effort/risk. Split-candidate (own sub-slice).

## Decision-type matrix
Within any mapped node, grade() emits an ActionEval per legal action — coverage is a NODE-family problem, not an action-type problem. All 14 wired NodeContexts have grader+mapper post-N4b. **No grader family at all** (RES-C §12 + scan): hero limps-as-open · donk-leads · hero-initiated check-raise · delayed c-bet/probe/overbet · 3-bet/4-bet-pot postflop · limped-pot postflop · short-SPR jam trees · **SQUEEZE (enum member `spot.py:75` with NO mapper and NO grader — reserved/legacy, flag explicitly, don't assume "just a gap")**. These need new grader families (RES-D-scale) — NOT quick N5 wins.

## Additive-safety
Content fills + flop-gate alignment + tolerance tuning: signature-safe (content un-hashed; gates don't feed `_postflop_signature`; `faced_bet_bucket` reads pot-fraction buckets). New NodeContext members hash generically via `ctx` join but new signature DIMENSIONS must follow the append-only conditional rule (`srs.py:112-127`). MW lift needs no new dim ("mw" dormant) but TAXONOMY bump consideration if new leak categories. Spot-dims persistence for N1 drill-down = additive migration (the only schema-touching piece of N5).

## Top risks
1. Open-band widening = named fidelity tradeoff, not free coverage.
2. MW mapper generalization risks the "never silently HU-grade multiway" no-go if half-built.
3. Flop gate alignment shifts coverage-rate test assertions (grader pins unaffected).
4. Blind-defense authoring volume understated: 9 rows × 7-family cascade ⇒ RES-A-grade fidelity review, not copy-paste.
5. SQUEEZE/donk/etc. have zero grader infra — RES-D-scale, keep out of N5's quick wins.

## Ranked opportunities (frequency × risk)
1. `map_flop_cbet` band alignment (roadmap gap #1).
2. Blind-defense content fills (9 cells, cascades).
3. `_CANON_BET_TOL` residual belt-test (verify, don't assume).
4. Persona open-band widening (needs sign-off).
5. Multiway mappers (own sub-slice).
6. Per-decision spot dims migration (orthogonal, additive; N1 drill-down dependency).
