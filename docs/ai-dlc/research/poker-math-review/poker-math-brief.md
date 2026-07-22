# Poker-Coach Simulator — Math & Assumptions Brief (for adversarial review)

This is a **local NLHE (No-Limit Hold'em) trainer**. The "Simulate" feature seats a human
against 8 bot villains of fixed personality types. This brief painstakingly documents the
math and "intelligence" driving those bots so you can scrutinize its soundness against
credible poker theory. **Nothing here is solver-derived** — it is a hand-authored heuristic
engine deliberately tuned to be beginner-friendly, NOT game-theory-optimal (GTO). Your job
is to assess whether the math and assumptions are *reasonable, internally coherent, and
directionally consistent with real poker theory* — and to flag where they diverge from GTO
or from real population tendencies, distinguishing defensible simplifications from actual
errors.

Design philosophy (stated in the repo): "heuristic + interim EV only, label EVs approximate;
no solver tables." Strategy lives in versioned JSON data, not code. The engine's goal is
plausible, *archetype-distinct* opponents a beginner can learn reads against — not balanced
GTO play.

---

## 0. Where the code lives (for reference; you may be given read access)

- Preflop action sampler: `backend/app/domain/personas.py` → `sample_preflop_action()`
- Postflop engine (the interesting math): `backend/app/domain/personas_postflop.py`
- Bet-sizing math: `backend/app/domain/table/sizing.py`
- Hand-strength eval: `backend/app/domain/equity.py`
- Lever schema: `backend/app/domain/content/models.py` → `PersonaPostflop`, `PersonaNode`
- Per-persona numbers: `content/personas/*.json` (6 packs)
- Validation harness: `backend/tests/test_personas_postflop.py`
- Spec (intended behavior): `docs/ai-dlc/specs/simulate-s4.md`

The 6 personalities and the table lineup (8 bots): 2× passive_fish, 2× TAG, 1× calling_station,
1× nit, 1× LAG, 1× maniac.

---

## 1. PREFLOP MODEL

### 1.1 Structure
Each persona pack has a list of **preflop nodes** keyed by two things:
- **facing state**: `unopened` (first-in / RFI), `vs_limpers`, `vs_rfi` (facing a single raise
  = a 3-bet spot for the actor), `vs_3bet` (a 4-bet spot), `vs_4bet` (a 5-bet spot).
- **position**: UTG, UTG1, UTG2, LJ, HJ, CO, BTN, SB, BB (9-max). Nodes can be
  position-specific or wildcard (`positions: null`).

Within a node is an ordered list of **mixes**. Each mix is:
- a `combos` string in standard poker range notation (e.g. `"55+, A6s+, K9s+, QTs+, A9o+, KJo+"`,
  where `s`=suited, `o`=offsuit, `+`=and-better), and
- `weights`: a frequency distribution over actions, e.g. `{"raise": 0.85, "fold": 0.15}` or
  `{"limp": 1.0}` or `{"3bet": 0.45, "fold": 0.55}` or `{"call": 0.55, "fold": 0.45}`.

**Lookup is FIRST-MATCH-WINS** down the ordered mix list; a hand not in any combo string
defaults to fold 1.0. The action is then sampled from the matched mix's weights via the hand's
seeded RNG. So preflop is: (position, facing) → find the mix whose range contains this hand →
roll the dice over its action weights.

### 1.2 Preflop sizing (levers, in `PersonaSizing`)
Three numbers per persona: `open_bb` (raise-first-in size, e.g. maniac 4.5bb), `threebet_mult`
(3-bet = mult × last raise-to, e.g. maniac 5.5×), `fourbet_mult` (4-bet = mult × last raise-to,
e.g. maniac 3.0×). Computed in `sizing.py:preflop_raise_to()`:
- open → `open_bb`
- iso (vs limpers) → `open_bb + 1bb per limper`
- 3bet → `threebet_mult × last_raise_to`
- 4bet → `fourbet_mult × last_raise_to`
- 5bet → jam (max)
All clamped into the engine's legal `[min_bb, max_bb]` bracket.

### 1.3 Example: maniac preflop (from `content/personas/maniac.json`)
- UTG open range: `55+, A6s+, K9s+, QTs+, J9s+, T9s, A9o+, KJo+` at raise 0.85 / fold 0.15,
  PLUS a wide limp range (small suited kings, suited gappers, offsuit broadways).
- BTN: raises `22+, A2s+, K2s+, Q2s+, J2s+...` (extremely wide) at 0.70 raise / 0.30 fold.
- vs_rfi (facing a raise): 3-bets `TT+, AJs+, AQo+` at 100%, a merged/bluffy tier at 45% 3bet /
  55% fold, and everything else `call 0.55 / fold 0.45`.
- vs_3bet (4-bet spot): 4-bets `TT+, AJs+, AQo+` 100%, plus A-blocker bluff 4-bets at 50%.
- vs_4bet (5-bet spot): 5-bet-jams `QQ+, AKs, AKo` 100%.

### CLAIMS/ASSUMPTIONS TO SCRUTINIZE (preflop)
1. Position-and-facing lookup with first-match-wins mixes is a reasonable abstraction of
   preflop decision-making.
2. Static frequency mixes (no board, no stack-depth adjustment beyond the fixed 100bb start,
   no ICM, no dynamic opponent modeling) are acceptable for a beginner trainer.
3. The specific ranges — e.g. maniac 3-betting only value at 100% but merged hands at 45% —
   are directionally plausible for that archetype vs real "maniac" population data.
4. Sizing as a flat multiplier of last-raise-to (rather than pot-relative or a
   geometric/GTO-informed size) is an acceptable simplification.
5. Limping ranges for the "loose" personas — is a limp-heavy strategy realistic for these
   archetypes, and is limping ever GTO/defensible?

---

## 2. POSTFLOP MODEL — the core engine (`personas_postflop.py`)

Postflop, every bot decision is 4 steps: **(a) classify hand → (b) look up base "merit"
weights → (c) reshape by persona levers → (d) normalize + sample.** No Monte-Carlo equity in
the hot loop; everything is analytic.

### 2.1 Hand classification (`strength_bucket`)
A hand is placed on a **7-rung made-hand ladder**, disjoint by construction:
`AIR < ACE_HIGH < MIDDLE_PAIR < TOP_PAIR < OVERPAIR_TPTK < TWO_PAIR_PLUS < MONSTER`.
- Uses best-5-card rank tuples (`_eval5` from `equity.py`) + rank/suit counting. No equity sim.
- Disjointness rules: sets are ALWAYS monster (never two_pair); straights on paired boards stay
  monster; a pocket pair below the top board card is ALWAYS middle_pair. "MONSTER" is coarse —
  it lumps a straight, flush, full house, and quads together regardless of board texture
  (an explicitly accepted heuristic simplification).
- Plus a **draw category**: NONE / WEAK (gutshot, backdoor-flush+overcard) / STRONG (flush
  draw, open-ended straight draw, combo draw). On the RIVER draw is always NONE (busted draws
  fall to AIR/ACE_HIGH by made strength).

### 2.2 The shared "merit" tables (game mechanics, in code)
For each bucket there are pre-normalization base weights (merits) for each action. These are
SHARED across all personas — the personality comes only from multipliers applied on top. Key
tables (verbatim values):

**Unopened / bet-or-check spot:**
```
_AGG_BASE (bet merit):   MONSTER 0.85 · TWO_PAIR+ 0.75 · OVERPAIR 0.70 · TOP_PAIR 0.55 ·
                         MIDPAIR 0.30 · ACE_HIGH 0.05 · AIR 0.05
_CHECK_BASE:             MONSTER 0.15 · TWO_PAIR+ 0.25 · OVERPAIR 0.30 · TOP_PAIR 0.45 ·
                         MIDPAIR 0.70 · ACE_HIGH 0.95 · AIR 0.95
```

**Facing a bet (fold / call / raise merit):**
```
_FOLD_BASE:  MONSTER 0.0 · TWO_PAIR+ 0.05 · OVERPAIR 0.05 · TOP_PAIR 0.12 · MIDPAIR 0.35 ·
             ACE_HIGH 0.60 · AIR 0.75
_CALL_BASE:  MONSTER 0.35 · TWO_PAIR+ 0.55 · OVERPAIR 0.70 · TOP_PAIR 0.78 · MIDPAIR 0.60 ·
             ACE_HIGH 0.40 · AIR 0.25
_RAISE_BASE: MONSTER 0.65 · TWO_PAIR+ 0.40 · OVERPAIR 0.25 · TOP_PAIR 0.10 · MIDPAIR 0.05 ·
             ACE_HIGH 0.02 · AIR 0.02
```
Note MONSTER has a LOW call merit (0.35) and HIGH raise merit (0.65) — it prefers to raise, not
slowplay. TOP_PAIR peaks the call merit (0.78) — it mostly calls, rarely raises.

**Draw bonuses (added pre-lever, semi-bluff logic):**
```
_DRAW_AGG_BONUS:   WEAK +0.15 · STRONG +0.35   (adds to bet/raise merit)
_DRAW_RAISE_BONUS: WEAK +0.05 · STRONG +0.15
_DRAW_CALL_BONUS:  WEAK +0.20 · STRONG +0.55   (drawing hands want to continue)
```

**Structural constants:** `_BLUFF_RAISE_FACTOR = 0.3` (bluff-raising rarer than bluff-betting);
`_COMMIT_AGG_BOOST = 3.0` (the SPR-commit multiplier).

### 2.3 Persona levers (the only per-personality numbers, in the JSON packs)
- `aggression` (>0): multiplies bet/raise merit for made hands. 1.0 = neutral.
- `stickiness` (>0): multiplies call merit / resistance to folding.
- `bluff_freq` (0..1): for AIR / busted (bluff cell), this DIRECTLY SETS the bet/raise mass —
  `bluff_mass = bluff_freq × noise × multiway_bluff_damp^(opponents−1)`; check gets `1 − bluff_mass`.
- `multiway_bluff_damp` (0..1): decays bluffing per extra opponent (exponent = opponents−1).
- `spr_commit`: SPR (stack/pot) at or below which strong hands commit.
- `sizing` / `sizing_by_node`: pot-fraction → weight distributions for bet sizing.

### 2.4 The decision computation (`sample_postflop_decision`)
1. Classify → (bucket, draw). Identify facing state from the *legal action shapes*
   (unopened = CHECK+BET; matched-with-option = CHECK+RAISE; facing chips = FOLD+CALL[+RAISE]).
2. Is this a "bluff cell"? (bucket ∈ {AIR, ACE_HIGH} AND draw == NONE.)
3. Build a merit vector over the legal actions:
   - Facing chips: FOLD = `_FOLD_BASE[bucket]`; CALL = `(_CALL_BASE[bucket] + draw_call_bonus) ×
     stickiness`; RAISE = if bluff cell `0.3 × bluff_mass`, else `(_RAISE_BASE[bucket] +
     draw_raise_bonus) × aggression × noise`.
   - Unopened / matched: if bluff cell, bet merit = `bluff_mass`, check = `1 − bluff_mass`;
     else bet merit = `(_AGG_BASE[bucket] + draw_agg_bonus) × aggression × noise`, check =
     `_CHECK_BASE[bucket]`.
4. **SPR commit rule**: if `stack/pot ≤ spr_commit` AND (bucket ≥ OVERPAIR_TPTK OR draw STRONG),
   zero the FOLD mass and multiply bet/raise mass by 3.0 (`_COMMIT_AGG_BOOST`). Models
   "pot-committed, won't fold, jam it in."
5. **Normalize**: clamp each merit ≥ 0, divide by the sum. If sum is 0 → CHECK if legal else
   FOLD. Then **always `rng.choices`** over the frequency vector — mixed, never argmax
   (never deterministic "always take the highest-merit action").

### 2.5 Bet sizing (`sizing.py`)
- Sizing is drawn from a **pot-fraction distribution INDEPENDENT of hand strength** (deliberate
  anti-"sizing tell" — the size never leaks whether it's a value bet or bluff). A fraction `f`
  is sampled from the persona's weights.
- BET amount = `f × pot`. RAISE-to = `current_bet_to + f × (pot + to_call)` (textbook
  pot-raise: fraction of the pot AFTER calling).
- `sizing_by_node`: optional per-node overrides. A "node" is named by board texture + street via
  `postflop_node_key()` reading ONLY board + legal actions (never hole cards): `cbet_dry`,
  `cbet_wet`, `cbet_mono`, `turn_barrel`, `river_value`, `raise`, or `flat` (donk/lead — no
  persona size). Texture (dry/wet/monotone) comes from a shared `texture.classify()`.
- Rounded 2dp then clamped into the legal bracket; a jam bracket (min==max) collapses to it.

### CLAIMS/ASSUMPTIONS TO SCRUTINIZE (postflop)
6. The 7-rung analytic ladder (no equity-vs-range, no board-texture-adjusted hand value beyond
   the coarse buckets) adequately represents postflop hand strength for realistic decisions.
7. Multiplicative "shared merit × persona lever" is a sound way to generate archetype-distinct
   but coherent strategies. Does scaling a fixed merit table actually produce sensible ranges,
   or does a large multiplier distort/saturate the distribution? (See §3 maniac.)
8. Sizing being fully **independent of hand strength** — GTO uses mixed sizes but ranges are
   *balanced* at each size; here a single persona bets all buckets from the same size
   distribution. Is "constant size distribution across strength" a reasonable beginner
   simplification, or does it produce unrealistic/exploitable lines?
9. The **bluff cell = {AIR, ACE_HIGH, no draw}** and `bluff_freq` directly setting air-bet mass:
   does this produce a sane bluff-to-value ratio vs the board/bet size? Notably `bluff_freq` is
   NOT tied to bet size or pot odds / MDF — it's a flat per-persona constant. Compare to GTO
   where bluff frequency is a function of bet size (e.g. ~2:1 value:bluff for pot, higher for
   small bets) and defense to Minimum Defense Frequency (MDF).
10. The **SPR-commit rule** (fold mass → 0, aggression ×3 when SPR ≤ threshold with overpair+):
    is committing purely on an SPR threshold + made-hand bucket sound? It ignores equity vs the
    specific range, board, and number of opponents.
11. `multiway_bluff_damp^(opponents−1)`: is exponential decay of bluffing by opponent count a
    reasonable model of how bluff EV falls in multiway pots?
12. Fold/call/raise merits are **not derived from pot odds or MDF** — they're static per bucket.
    A bot's fold decision does not look at the price it's being laid. Assess this gap vs real
    theory (pot-odds-based calling, MDF-based defending).

---

## 3. THE 6 PERSONALITIES (lever values) + THE KNOWN MANIAC PROBLEM

| Persona | aggression | stickiness | bluff_freq | spr_commit | multiway_damp |
|---|---|---|---|---|---|
| nit | 0.6 | 0.6 | 0.04 | 1.2 | 0.30 |
| passive_fish | 0.6 | 1.4 | 0.12 | 2.0 | 0.40 |
| calling_station | 0.5 | 1.8 | 0.03 | 1.5 | 0.30 |
| TAG (tight-aggressive) | 2.4 | 0.6 | 0.22 | 2.5 | 0.55 |
| LAG (loose-aggressive) | 3.2 | 0.55 | 0.35 | 3.0 | 0.65 |
| maniac | 15.0 | 0.55 | 0.55 | 4.0 | 0.85 |

**The observed problem:** the maniac over-bluffs and over-commits unrealistically. Root cause
identified: `aggression = 15.0` is ~5× the next-highest persona and it multiplies the value/raise
merit while check/fold merit stays fixed, SATURATING the frequency mix into near-deterministic
aggression. Worked examples (heads-up):
- Top pair, can bet: `bet = 0.55 × 15 = 8.25` vs `check = 0.45` → bets ~95% (TAG ~75%, nit ~42%).
- Top pair, facing a bet: `raise = 0.10 × 15 = 1.5`, `call = 0.78 × 0.55 = 0.43`, `fold = 0.12`
  → raises ~73%. That's raising a marginal made hand at value frequency = spew.
- `bluff_freq 0.55` + `multiway_bluff_damp 0.85` → 3-way air-bet rate = `0.55 × 0.85 = 0.47`
  (still bluffs 47% into two opponents — real players slow down multiway far more).
- `spr_commit 4.0` fires in almost every postflop pot (SPR ≤ 4 common after one bet), so any
  overpair+ never folds.

The repo's own test file documents (`test_personas_postflop.py:554-561`) that "maniac's
aggression=15.0 is a tuning outcome that clears the PRD AF floor at this merit table's saturation
curve, NOT a statement that maniac is 15× normal... raw lever magnitudes are calibration
artifacts." So this is acknowledged, not hidden.

### CLAIMS/ASSUMPTIONS TO SCRUTINIZE (personalities)
13. Whether these 6 archetypes and their lever values map to REAL poker population reads.
    Research real stat profiles (VPIP/PFR, AF = aggression factor, WTSD = went-to-showdown, fold-
    to-cbet) for these archetypes and compare. Do "calling_station stickiness 1.8", "nit
    aggression 0.6", "TAG 2.4 / LAG 3.2" produce realistic behavior in the right direction?
14. Is a single scalar `aggression` multiplier a defensible model of a "playing style," or does
    the maniac saturation prove the model breaks at the extremes (i.e., style ≠ one dimension)?
15. Are 5 scalar levers (aggression, stickiness, bluff_freq, spr_commit, multiway_damp) a
    sufficient basis to span the realistic space of player types, or are important dimensions
    missing (e.g., position awareness, board-texture sensitivity, bet-size-reading)?

---

## 4. HOW GTO IS (AND ISN'T) INCORPORATED — the deliberate trade-offs

This engine is EXPLICITLY NOT GTO. Known, intentional trade-offs (assess whether each is a
defensible beginner-friendly simplification or a distortion that could teach bad habits):

- **No solver / no equilibrium.** Bots do not compute or approximate a Nash-equilibrium
  strategy (no CFR — counterfactual regret minimization). They sample from hand-authored
  frequency mixes. Trade-off: interpretable, fast, archetype-distinct, but not balanced/
  unexploitable.
- **Frequencies are archetype-flavored, not balanced.** A GTO range is constructed so it can't
  be exploited (correct bluff-to-value, correct defense frequency). Here the frequencies express
  a *personality* (exploitable on purpose) so a learner can practice exploiting reads.
- **Bluffing is a flat constant (`bluff_freq`), not a function of bet size / MDF.** GTO bluff
  frequency is pinned to bet size (bigger bet → more bluffs allowed → richer value); defense is
  pinned to MDF. This engine ignores both. Assess the size of this gap.
- **Defense/folding ignores pot odds and MDF.** Merits are static per bucket; the bot does not
  compare its equity to the price. A GTO/exploitative player folds as a function of price and
  range. This is probably the biggest theoretical gap — scrutinize it hard.
- **Sizing independent of hand strength but NOT range-balanced.** GTO mixes sizes with balanced
  ranges at each; here it's one size distribution for all buckets. Anti-sizing-tell is achieved
  but the ranges at each size aren't theory-balanced.
- **Coarse hand buckets, no equity-vs-range.** Real decisions hinge on equity vs the opponent's
  range; this uses absolute made-hand rungs. The "MONSTER" bucket ignores relative strength
  (nut vs non-nut flush treated identically).
- **EVs shown to the user are labeled "approximate."** The app grades the human's decisions with
  interim/heuristic EV, not solver EV.
- **Static 100bb, no ICM, no multi-street planning.** Bots decide street-by-street with no
  turn/river barreling plan, no range-vs-range projection, no ICM (tournament) considerations.

### CLAIMS/ASSUMPTIONS TO SCRUTINIZE (GTO trade-offs)
16. Is "learn to exploit archetypes first, GTO later" a pedagogically sound progression, or does
    training vs unbalanced bots instill exploitable habits that transfer poorly?
17. Which of the trade-offs above are HARMLESS simplifications vs which could actively MISLEAD a
    beginner (e.g., a bot that never folds correctly to price teaching the human wrong bluff
    sizing)?
18. Are the specific numeric heuristics (⅓ pot ≈ 4:1 value:bluff, pot bet ≈ 2:1, MDF = pot/
    (pot+bet), the ⅓-½-⅔ value-by-street rule) anywhere reflected in this engine — and should
    they be, for a trainer that claims to teach real poker?

---

## 5. YOUR TASK

Assess the MATHEMATICAL BASIS AND ASSUMPTIONS above. For each numbered claim/assumption:
- State whether it is **sound / defensible-simplification / questionable / wrong**.
- Back it with CREDIBLE sources (GTO Wizard, Upswing, PokerStrategy, Red Chip, academic CFR /
  game-theory papers, Will Tipton / Matthew Janda / Modern Poker Theory (Acevedo), 2+2 archives).
  Prefer primary/authoritative sources over blog SEO fluff.
- Where the engine diverges from GTO, say whether the divergence is JUSTIFIED by the stated
  beginner-friendly goal or is a genuine modeling error.
- Call out anything mathematically incoherent, any assumption with no theoretical support, and
  any place the "beginner-friendly" framing is used to excuse an actual bug.

Be adversarial and specific. Cite real numbers from theory (MDF %, bluff-to-value ratios,
archetype stat ranges) and compare them to this engine's numbers.
