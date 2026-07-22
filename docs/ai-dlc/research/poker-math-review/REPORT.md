# Poker-Coach Simulator — Math & Assumptions Review (Final Report)

**Date:** 2026-07-21
**Question asked:** Are the mathematical basis and assumptions of the Simulate bot engine
sound, coherent, and directionally consistent with real poker theory — and where they diverge
from GTO, is the divergence justified by the beginner-friendly goal or is it a real error?

## Method & provenance

- A painstaking math brief was authored documenting every part of the engine (preflop
  range/position/3bet-4bet-5bet model, postflop 7-rung strength ladder, shared merit tables,
  the 5 persona levers, sizing, SPR-commit, the 6 personalities, and the GTO trade-offs). It
  poses **18 numbered claims/assumptions** to scrutinize. See `poker-math-brief.md`.
- **Reviewer 1 — Opus refuter (web-capable, adversarial).** Verified the brief against the
  actual code, then researched each claim against credible sources (GTO Wizard, SplitSuit, Red
  Chip, PokerStrategy, PokerVIP, DeucesCracked, plus Miller/Flynn/Mehta and Janda). Full output:
  `refuter-opus-findings.md`.
- **Reviewer 2 — Codex refuter (intended independent engine).** COULD NOT RUN. Two failures:
  first a Claude Code write-path block (fixed), then **nested macOS sandboxing**
  (`sandbox-exec: sandbox_apply: Operation not permitted`) — Codex cannot apply its own seatbelt
  profile inside Claude Code's sandbox, so it could not read the repo or write files. Per
  decision, we shipped the single-reviewer result.

> **Limitation:** this report is **single-reviewer**. The independent cross-check that would
> have caught Reviewer 1's blind spots did not run. Treat the two WRONG verdicts as
> high-confidence (they are backed by first-order theory + the engine's own admissions) and the
> QUESTIONABLE verdicts as one expert opinion, not a consensus.

## Headline verdict

The brief is an **honest** description of the engine — Reviewer 1 verified every merit table,
lever value, formula, and the maniac worked-examples against the code and found no
misrepresentation (the brief actually *under-sells* known problems the test file already
admits). Of the 18 claims: **~4 SOUND · ~6 DEFENSIBLE-SIMPLIFICATION · ~6 QUESTIONABLE · 2
WRONG.** The engine's taxonomy and anti-tell design are sound; its two real errors sit exactly
on the skills the app claims to teach, and both are cheap to fix.

## Per-claim summary

| # | Claim (abbreviated) | Verdict |
|---|---|---|
| 1 | Position+facing first-match-wins range lookup | **SOUND** (abstraction) |
| 2 | Static mixes, no board/stack/ICM, fixed 100bb | DEFENSIBLE |
| 3 | Maniac 3-bet shape (value 100% + bluffy tier) | DEFENSIBLE (mislabel quibble) |
| 4 | Sizing as flat multiple of last-raise-to | DEFENSIBLE |
| 5 | Limp-heavy ranges for loose personas | QUESTIONABLE (theory) / DEFENSIBLE (fish-caricature) |
| 6 | 7-rung ladder, no equity-vs-range, coarse MONSTER | **QUESTIONABLE** (2nd-biggest gap) |
| 7 | Multiplicative merit×lever produces archetypes | **QUESTIONABLE** (breaks at maniac extreme) |
| 8 | Sizing independent of hand strength | **SOUND** (genuine anti-tell) |
| 9 | Flat `bluff_freq`, decoupled from bet size/MDF | **WRONG** (co-biggest gap) |
| 10 | SPR-commit: fold→0, agg×3 at low SPR | QUESTIONABLE → WRONG at high thresholds (LAG/maniac) |
| 11 | `multiway_damp^(opp−1)` bluff decay | DEFENSIBLE form, MIS-CALIBRATED constants |
| 12 | Fold/call/raise static, ignore pot odds/MDF | **WRONG** (single most important omission) |
| 13 | 6 archetypes map to real population reads | DEFENSIBLE (ordering right, magnitudes fuzzy) |
| 14 | Single scalar `aggression` models "style" | QUESTIONABLE (insufficient at extreme) |
| 15 | 5 scalar levers span the player-type space | QUESTIONABLE (missing position/texture/size axes) |
| 16 | "Exploit archetypes first, GTO later" pedagogy | **SOUND** |
| 17 | Which trade-offs harmless vs misleading | MIXED (2 misleading: §9, §12) |
| 18 | Are MDF / size↔bluff laws in the engine? | ABSENT — the defense/bluff ones SHOULD be added |

## The most serious problems, ranked

1. **Price-blind defense (Claim 12).** Bots fold/call at a static per-bucket rate that never
   looks at bet size / pot odds / MDF — they fold top pair to a ¼-pot bet at the same rate as to
   a 2×-pot overbet. This deletes the single most important beginner lesson ("am I priced in?")
   and can actively **mis-train** that sizing doesn't affect fold equity.
   *Theory:* MDF = pot/(pot+bet) → defend 75% vs ⅓-pot, 50% vs pot. *Fix:* scale `_FOLD_BASE`
   by a price term from the faced size the engine already knows (one-line).

2. **Bluff frequency decoupled from bet size (Claims 9 & 18).** `bluff_freq` is a flat constant;
   the size is sampled independently afterward. Real bluff-to-value scales with size
   (⅓-pot ≈ 20% bluffs, pot ≈ 33%, overbet ≈ 40%). A bot can overbet with a 22% bluff rate
   theory says should be ~40%. Undermines exactly the read the app teaches. *Fix:* make effective
   bluff mass a function of the sampled fraction (one-line).

3. **Aggression-lever saturation / the maniac (Claims 7, 10, 11, 14).** An unbounded
   multiplicative `aggression` on one side of an un-normalized ratio saturates toward argmax:
   maniac=15 value-bets/raises marginal hands at spew frequency (top pair bets 95%, raises 73%
   facing a bet); `spr_commit 4.0` makes overpairs never fold; `multiway_damp 0.85` barely slows
   multiway bluffing (47% into two opponents vs theory's ~half). The team's own test file admits
   this is a saturation artifact. *Fix:* bounded/logit-space aggression; lower maniac spr_commit
   to ~1.5–2 and damp to ~0.6.

4. **Absolute made-hand ladder ignores equity-vs-range and texture (Claim 6).** Value decisions
   are texture-blind and MONSTER collapses nut and non-nut flushes into one bucket.

5. **Multiway decay mis-calibration (Claim 11).** Right functional form, wrong constants (nit
   drops 91% by 3-way, maniac only 28%, vs theory ~50%).

## The single biggest thing the engine gets RIGHT

**Sizing decoupled from hand strength (Claim 8)** — a genuine GTO property, correctly
implemented as an anti-sizing-tell (`postflop_node_key` reads only board + legal actions, never
hole cards), so a bot's bet size never leaks value-vs-bluff. Runner-up: the **correct
directional ordering of all six archetypes' levers** against real population VPIP/PFR/AF
profiles — the taxonomy itself is sound; only the extreme magnitudes and the missing price/size
linkages fail.

## Sources

Full source list (with URLs) is at the bottom of `refuter-opus-findings.md`. Key anchors:
GTO Wizard (MDF & Alpha, 3-way heuristics, flop c-bet heuristics, open-limping), SplitSuit (MDF
101, Perfect GTO Bluffing), Red Chip (multiple bet sizes, SPR), PokerStrategy, DeucesCracked,
PokerVIP / Pokerology / PokerCoaching (archetype VPIP/PFR/AF profiles), PokerTube (pot-committed
fallacy), PokerNews (SB limp), plus Miller/Flynn/Mehta *Professional NLHE Vol I* and Janda
*Applications of No-Limit Hold'em*.

## Companion files (this folder)

- `poker-math-brief.md` — the full engine math documentation + the 18 claims.
- `refuter-opus-findings.md` — Reviewer 1's complete per-claim analysis with citations.
- `REPORT.md` — this synthesis.
