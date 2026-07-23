# 12 — Persona Engine Reference & Realism-Fix Implementation Guide

**Purpose.** A single, self-contained reference for how the Simulate **villain bots** (personas)
make decisions today — every lever, every merit table, every formula, with worked numbers — and a
detailed, implementation-ready guide to the realism gaps a future slice must fix. Written so a
**fresh sub-agent with zero prior context** can pick up the roadmap NEXT item *"Persona realism —
nit / fish / calling-station decision-making"* and know exactly what the engine does, what's wrong,
what real players do, and how to change it without breaking the invariants that hold the system
together.

**Scope.** **All six personas.** §1–§6 were written for the three **non-aggressive** personas
(`nit`, `passive_fish`, `calling_station`); **§9 (Part II)** extends the same engine reference +
findings to the three **aggressive** personas (`maniac`, `LAG`, `TAG`), reviewed in a second dual
pass 2026-07-23. The engine, tables, and invariants in §1–§6 apply to all six unchanged (personas
differ only in levers + preflop ranges). This is about the **bot decision engine**, i.e. how
villains *play* — **NOT** the grader/coach (`grade_map*.py`), which is a separate system (see §0.2).

**Provenance.** Findings come from a Claude engine audit + a dual adversarial review (web-capable
Claude Opus `general-purpose` refuter + Codex Sol `gpt-5.6-sol`), 2026-07-23. Verdicts: **Codex
FAIL, Claude PASS-WITH-ISSUES/leaning-FAIL**. Condensed findings also in
`docs/ai-dlc/research/RES-J-persona-realism.md`; the roadmap slice is in
`docs/ai-dlc/roadmap/simulate-table.md` (`## NEXT` → "Persona realism", just before Hidden-persona
mode). Player-type *strategy* content (how to exploit them) lives in
`docs/research/player-types-and-exploits.md` — this doc is the *engine* companion to it.

---

## 0. Orientation

### 0.1 Two-sentence mental model
Each persona's identity is **five scalar levers** in `content/personas/<name>.json`. Those levers
are multiplied into a set of **shared merit tables** in `backend/app/domain/personas_postflop.py`;
the bot buckets its hand into one of 7 strength tiers, looks up shared fold/call/raise "merit"
numbers, scales them by the levers, normalizes to probabilities, and draws with `rng.choices`.
**All personality lives in 5 numbers over one rulebook — that is the root constraint behind every
finding below.**

### 0.2 Bot engine vs. grader — do not conflate
- **Persona engine** (`personas.py`, `personas_postflop.py`) = how **villain bots act** at the
  table. **This is what the realism slice fixes.**
- **Grader / coach** (`table/grade_map*.py`, `domain/postflop.py` graders) = how the app **grades
  the hero's** decisions and shows verdicts. It uses a *different* hand taxonomy
  (`postflop.py::_hand_category()` → `strong/weak_made/draw/air`) than the persona engine's 7-rung
  `StrengthBucket`. **Changing personas does NOT change grading verdicts, `spot_signature()`, or
  `TAXONOMY_VERSION`.** Keep the blast radius on the bot side.
- Consequence: persona changes **do** shift the *statistical population* (VPIP/PFR/AF/WTSD) and the
  played hand-stream, so they trip the population-band + coverage-baseline harnesses (see §5.3).
  They do **not** touch grader tests.

### 0.3 File map (with line anchors, as of 2026-07-23)
| Path | Role |
|------|------|
| `backend/app/domain/archetypes.py` | `VillainType` enum (6 fixed slots) — `:8` |
| `content/personas/{nit,passive_fish,calling_station}.json` | the levers + preflop ranges (persona identity) |
| `content/schema/persona.schema.json` | JSON schema (note: postflop lever block is validated by the Pydantic model, **not** fully described in this schema file) |
| `backend/app/domain/content/models.py` | `PersonaPostflop` lever schema `:142`; `PersonaPack` `:174` |
| `backend/app/domain/personas.py` | **preflop** engine `sample_preflop_action` `:61`; loader `:40` |
| `backend/app/domain/personas_postflop.py` | **postflop** engine — the heart |
| `backend/app/domain/table/range_estimate.py` | villain-range reveal; **reuses** `sample_postflop_decision` `:278` (coupling — see §5.3) |
| `backend/app/services/sim_session.py` | live table loop calls the engines |
| `backend/tests/test_personas_postflop.py` | population-band harness + monotonicity/ordering invariants |
| `backend/tests/test_coverage_baseline.py` | fixed-seed graded-coverage regression gate |
| `backend/tests/test_personas.py` | preflop engine tests |

---

## 1. Preflop engine (`personas.py`)

Pure content lookup — **no merit math preflop**. `sample_preflop_action(pack, position, facing,
hole_cards, rng)`:

1. Classify the hand into a 169-class via `hole_cards_to_class`.
2. Scan `pack.preflop` **in list order**; pick the first node whose `facing` matches AND whose
   `positions` is `None` (wildcard) or contains `position`.
3. Within that node, scan `mixes` in order; the **first mix whose `combos` range contains the hand
   class wins**. Weights are action→probability; any remainder below 1.0 becomes implicit `fold`.
   `rng.choices` draws the action.
4. Node matched but no mix covers the hand ⇒ fold 1.0. No node matches ⇒ fold.

**`facing` values:** `unopened`, `vs_limpers`, `vs_rfi`, `vs_3bet`, `vs_4bet`.
**Action names → wire** (`_WIRE`, `:25`): `fold→FOLD`, `limp→CALL`, `call→CALL`, `raise→RAISE`,
`3bet→RAISE`, `4bet→RAISE`, `5bet_shove→RAISE`. (Content speaks "limp/3bet/…"; the wire only sees
FOLD/CALL/RAISE. Note: because everything raise-like collapses to `RAISE`, the persona's *chosen
size* is what differentiates a 3bet from a 4bet downstream.)

**Preflop sizing** is a separate `sizing` block per pack: `open_bb`, `threebet_mult`,
`fourbet_mult` (consumed by `table/sizing.py::preflop_raise_to`).

**⚠️ First-mix-wins is the trap behind the fold-aces bug (B1, §4).** If an earlier mix assigns a
premium a fold weight, a later "limp everything" mix can never rescue it.

---

## 2. Postflop engine (`personas_postflop.py`) — full pipeline

`sample_postflop_decision(pack, hole, board, legal, pot_bb, stack_bb, opponents, rng, noise=1.0,
current_bet_to=0.0, is_aggressor=False) -> Decision`. **The action draw is always the FIRST
`rng.choices` call** — this ordering is load-bearing (see §5.3, range_estimate coupling).

### 2.1 Strength bucketing (`strength_bucket` → `(StrengthBucket, DrawCategory)`)
Analytic (no Monte-Carlo). 7 disjoint made-hand rungs (`_RUNG` value in parens):
`AIR(0) < ACE_HIGH(1) < MIDDLE_PAIR(2) < TOP_PAIR(3) < OVERPAIR_TPTK(4) < TWO_PAIR_PLUS(5) <
MONSTER(6)`. Key rules (`_made_bucket` `:109`):
- Straight/flush/boat/quads/set (or trips w/ a hole card) → **MONSTER**.
- Pocket pair **above** top board card → OVERPAIR_TPTK; pocket pair **below** → MIDDLE_PAIR.
- A hole card pairs the board: top-board pair with top kicker (A, or K when the pair is aces) →
  OVERPAIR_TPTK, else TOP_PAIR; pair below top board card → MIDDLE_PAIR.
- No pair: `_high_card_bucket` → **ACE_HIGH if the hole high card ≥ King, else AIR**
  (⚠️ **king-high is lumped into ACE_HIGH** — a real showdown-value gap, see N4).
- Under-pocket-pair on a paired board (e.g. 22 on 883) is MIDDLE_PAIR, not two-pair (F7 fix, already
  landed in Epic 4).

**DrawCategory** (`_draw_category`, flop/turn only; river is always NONE):
- **STRONG** = flush draw or OESD/double-gutter (≥2 straight-completing ranks).
- **WEAK** = gutshot (1 rank) or (backdoor flush + overcard).
- **NONE** otherwise. Note the `overcard` flag exists here (`:189`) but only ever *upgrades a draw*;
  it never triggers a fold (relevant to F3).

### 2.2 Facing state (derived from `legal` shapes)
- **Facing chips** (FOLD present): FOLD + CALL [+ RAISE].
- **Unopened / matched-with-option** (no FOLD): CHECK + BET, or CHECK + RAISE.

### 2.3 Shared base merit tables (EXACT — the same for every persona)
```
bucket          AGG   CHECK  FOLD  CALL  RAISE
MONSTER         0.85  0.15   0.00  0.35  0.65
TWO_PAIR_PLUS   0.75  0.25   0.05  0.55  0.40
OVERPAIR_TPTK   0.70  0.30   0.05  0.70  0.25
TOP_PAIR        0.55  0.45   0.12  0.78  0.10
MIDDLE_PAIR     0.30  0.70   0.35  0.60  0.05
ACE_HIGH        0.05  0.95   0.60  0.40  0.02
AIR             0.05  0.95   0.75  0.25  0.02
```
Draw bonuses (added pre-lever): `AGG` +{none 0, weak .15, strong .35}; `RAISE` +{0, .05, .15};
`CALL` +{0, .20, .55}. Structural constants: `_BLUFF_RAISE_FACTOR=0.3`, `_COMMIT_AGG_BOOST=3.0`,
`_AGGRESSION_CAP=5.6`.

### 2.4 Merit computation
Let `agg_scale = min(aggression, 5.6) * noise`, and
`bluff_mass = bluff_freq * noise * multiway_bluff_damp**max(opponents-1,0)`.
`bluff_cell = bucket ∈ {AIR, ACE_HIGH} and draw == NONE`.

**Facing chips** (`:451`):
- `to_call = CALL.min_bb`; `faced_frac = to_call / max(pot_bb − max(current_bet_to, to_call), 0.01)`
  (the pot the aggressor bet *into*, so a raise/check-raise maps to the right size bucket).
- `fold_merit = _FOLD_BASE[bucket] × price_factor(faced_frac, stickiness)`;
  if bucket ∈ {AIR, ACE_HIGH, MIDDLE_PAIR}: `× 1.15**max(opponents−1,0)` (F4 multiway catch-tighten).
- `call_merit = (_CALL_BASE[bucket] + draw_call_bonus) × stickiness`.
- `raise_merit = 0.3 × bluff_mass` if `bluff_cell` else `(_RAISE_BASE[bucket] + draw_raise_bonus) ×
  agg_scale`.

**Unopened / matched** (`:493`):
- `bluff_cell`: `agg_merit = bluff_mass`, `check_merit = max(1 − bluff_mass, 0)`.
- else: `agg_merit = (_AGG_BASE[bucket] + draw_agg_bonus) × agg_scale`, `check_merit =
  _CHECK_BASE[bucket]`.

**price_factor** (`:372`) — the size→fold response:
```
price_factor(frac, stickiness) = 0.35 × (α_bucket / 0.375) ** (2.2 × stickiness**(-0.15))
α_bucket:  SMALL(≤0.40 pot) 0.25 · MEDIUM(≤0.70) 0.375 · LARGE(≤1.10) 0.47 · OVERBET(>1.10) 0.60
```
So fold merit rises with faced size; `stickiness` **damps** the exponent — but only weakly
(`**(-0.15)`). This weak coupling is the mechanical heart of **F1**.

### 2.5 SPR commit (`:506`)
If `stack_bb/pot_bb ≤ spr_commit` **and** (`_RUNG[bucket] ≥ _RUNG[OVERPAIR_TPTK]` **or** draw ==
STRONG): zero the FOLD merit and multiply BET/RAISE merit by `_COMMIT_AGG_BOOST=3.0` (CALL
unchanged). Binary cliff; identical 3.0 for every persona (**F8**).

### 2.6 Normalize + size draw
Clamp merits ≥ 0, divide by sum (sum 0 ⇒ CHECK if legal else FOLD), `rng.choices`. If the action is
BET/RAISE, draw a pot-fraction `f` from the persona's `sizing` (or `sizing_by_node` when authored +
`is_aggressor`), then `BET = f×pot`, `RAISE` via `pot_fraction_to_bb(...)`, clamped into the legal
bracket. **F2 two-stage bluff:** for a `bluff_cell` bet, `bluff_mass` is pre-scaled by the expected
size factor and the size weights are tilted by `_bluff_size_factor` — this keeps the ACTION draw
first (range_estimate dependency) while making bigger bluff-bets carry proportionally more air.
**Value hands keep the authored size distribution byte-for-byte** — this is the deliberate
**anti-sizing-tell no-go** (pinned by `test_sizing_spread_no_deterministic_strength_to_size`); see
N6.

---

## 3. The five levers — deep dive

| Lever | Where it acts | Effect | nit | fish | station |
|-------|---------------|--------|-----|------|---------|
| `aggression` | `agg_scale` multiplies **value** BET/RAISE merit (`:499,487`); capped at 5.6; **air bluffs bypass it** | how often it value-bets/-raises made hands | 0.6 | 0.6 | 0.5 |
| `stickiness` | (a) flat × on CALL merit (`:484`); (b) damps price exponent (`:377`, DAMP 0.15) | how loose it calls **and** how little size scares it — **two jobs, one dial (F1)** | 0.6 | 1.4 | 1.8 |
| `bluff_freq` | sets the air BET/RAISE mass `bluff_mass` (`:430`) | pure-air bluff rate | 0.04 | **0.12** | 0.03 |
| `spr_commit` | SPR threshold for the commit rule (`:506`) | at/below this SPR, OVERPAIR+/strong-draw stops folding + 3× aggression | 1.2 | 2.0 | 1.5 |
| `sizing` / `sizing_by_node` | the pot-fraction draw (`:534`) | its own bet sizes | see below | flat | flat |
| `multiway_bluff_damp` | `**(opp−1)` on bluff_mass | bluffs less multiway | 0.3 | 0.4 | 0.3 |

Sizing dists: **nit** `sizing {0.5:.4, 0.75:.45, 1.0:.15}` + full `sizing_by_node` (cbet_dry/wet/mono,
turn_barrel, river_value, raise). **fish** & **station** share `{0.33:.6, 0.5:.3, 0.75:.1}`, no
node override (**N6** — identical own-sizing). Preflop sizing: nit `3.0 / 3.5× / 2.3×`; fish
`4.0 / 3.0× / 2.2×`; station `3.5 / 3.0× / 2.2×`.

---

## 4. What each persona currently PLAYS like (computed ground truth)

Reproducible facing-a-bet distributions (`fold / call / raise`), heads-up, legal raise present, at
each faced-size bucket — computed directly from §2.3 tables × levers. **A fresh agent can regenerate
these to verify any change.**

**NIT** (stickiness 0.6):
```
size     middle_pair            ace_high               air
small    0.107/0.824/0.069      0.241/0.723/0.036      0.382/0.572/0.046
medium   0.239/0.702/0.059      0.455/0.520/0.026      0.618/0.353/0.028
large    0.349/0.601/0.050      0.588/0.393/0.020      0.735/0.246/0.020
overbet  0.490/0.471/0.039      0.718/0.269/0.013      0.832/0.156/0.013
unopened: bet(monster) 0.773 · bet(overpair/tptk) 0.583 · bet(mid-pair) 0.205 · bet(air) 0.04
```
**FISH** (stickiness 1.4):
```
small    0.057/0.911/0.033      0.131/0.816/0.053      0.226/0.702/0.072
medium   0.123/0.846/0.030      0.261/0.695/0.045      0.405/0.540/0.056
large    0.184/0.788/0.028      0.361/0.600/0.039      0.522/0.434/0.045
overbet  0.273/0.702/0.025      0.485/0.484/0.031      0.645/0.322/0.033
unopened: bet(air) 0.12  (highest of the three — see F2)
```
**STATION** (stickiness 1.8):
```
small    0.047/0.932/0.022      0.113/0.876/0.011      0.202/0.783/0.016
medium   0.100/0.880/0.020      0.224/0.767/0.010      0.364/0.624/0.013
large    0.149/0.832/0.019      0.312/0.679/0.009      0.474/0.516/0.010
overbet  0.222/0.760/0.018      0.426/0.567/0.007      0.596/0.396/0.008
unopened: bet(air) 0.03
commit-mode facing (SPR≤commit, overpair+): fold 0 → call/raise only
```
**Read the tables:** every persona *does* fold more to bigger bets (fold rises left→right) — so none
is truly "inelastic," and every persona *calls pure air heavily* (station 78% air to a small bet;
even the nit 57%). Both are wrong per §4/§5. The station and fish differ almost entirely by a
uniform stickiness shift, not by a different *shape*.

---

## 5. Realism gaps (findings) — full detail + fix direction

Severity is the cross-review resolved value. "Both" = Claude + Codex independently. Each fix names
the file(s) and the tests it will move.

### Tier A — quick wins (small, high value)

**B1 — Calling station folds AA / KK / AKs 40% preflop, unopened.** *Severity: HIGH (bug).*
`content/personas/calling_station.json:21,32` — both the UTG and wildcard `unopened` nodes assign
premiums `{"raise": 0.6, "fold": 0.4}`. First-mix-wins (`personas.py:81`) means the later "limp
22+/suited-ace" mix never catches them, so 40% of the time the station **folds aces when first to
act**. A calling station folding premiums is simply broken.
→ **Fix:** change the 40% branch from `fold` to `limp`/`call` (stations open-limp their whole range,
including premiums, or occasionally raise). Add a test/validator for premium-hand fold rates and for
overlapping-combo mixes. *(Content-only; will shift the played stream → re-record coverage baseline,
§5.3.)*

**A1 — Loose personas call pure AIR (no pair, no draw) at implausible rates.** *Severity: HIGH.
Both.* Root: `_CALL_BASE[AIR]=0.25 × stickiness` (`:244,484`). Station calls ~78% with 72o on QJ9 to
a small bet; even the nit calls ~57% air. Compounded by the king-high→ACE_HIGH lumping (N4):
`_CALL_BASE[ACE_HIGH]=0.40 × 1.8 = 0.72` station call merit for king-high. On the river, busted
draws are returned as AIR/ACE_HIGH (`:195`) so these are literal no-pair showdown calls. Research is
explicit: stations call *weak made hands and any pair/piece*, **not literally no-pair-no-draw**.
→ **Fix:** drop `_CALL_BASE[AIR]` toward ~0.05–0.10 and gate any air-continue behind a real draw
(`_DRAW_CALL_BONUS`). Optionally split king-high out of ACE_HIGH into a showdown-value class, and
zero river no-pair calls except explicitly-modeled bluff-catch ace-high nodes. *(One-table edit;
moves the `test_fold_to_bet_*` numbers and population bands.)*

### Tier B — the core structural fix

**F1 — Elasticity collapse (the defining flaw).** *Severity: HIGH. Both.* Documented reality:
**calling station = *inelastic*** (calls/folds roughly regardless of bet size), **fish = *elastic* /
fit-or-fold** (calls small, folds big). Our engine controls **both** looseness and size-response
with the single `stickiness` dial: it sets the flat CALL multiplier (`:484`) **and** the price-fold
exponent (`:377`, DAMP 0.15). Net: both personas swing fold-rate ~4.7–4.8× from SMALL→OVERBET —
neither is flat, and you cannot make the station inelastic-but-loose while the fish is
elastic-but-scared. The one axis that *defines* the difference is welded shut.
→ **Fix:** split the dial into (at least) two independent levers: `call_looseness` (the flat CALL
multiplier) and `size_elasticity` (drives the `price_factor` exponent, decoupled from looseness).
Set station `size_elasticity ≈ 0` (near-flat fold across sizes) with high looseness; fish high
elasticity with moderate looseness. Prefer a continuous faced-size function over the 4 abrupt α
buckets. *(Touches `personas_postflop.py` `_price_factor` + `PersonaPostflop` model + all 3 packs;
moves `test_fold_to_bet_monotone_in_faced_size`, `test_fold_to_bet_respects_alpha_ceiling`,
`test_fold_to_bet_persona_ordering_at_fixed_size` — keep fold monotone in size and respect the α
ceiling; deliberately re-anchor persona ordering.)*

### Tier C — structural (bigger)

**F3 / N3 — Memoryless engine, no street or scare-card term.** *Severity: HIGH. Both* (Codex: F3
PARTIAL — see nuance). The engine re-buckets each street from scratch and takes **no street /
action-history / initiative argument** (`:381`); `is_aggressor` only changes *sizing* (`:363`), not
whether it bets. So flop = turn = river given the same bucket, and "runs scared when an overcard
hits the turn" is unrepresentable. *Nuance (Codex F3):* there IS partial scare behavior via
re-bucketing — a flop top pair auto-downgrades to MIDDLE_PAIR when a bigger turn card lands (`:101`)
— but no explicit fear response and no "give up on later streets" pattern.
→ **Fix:** thread street + prior-street bucket + prior aggression into the facing-fold term; add a
scare-card multiplier (new overcard / flush- or straight-completing card / paired board) on the
fold merit for pair-class buckets, with **persona-specific scare sensitivity** (strong for nit/fish,
near-zero for the inelastic station). This is the enabler for the documented nit "one-and-done
barrel fold." *(Requires a new argument to `sample_postflop_decision` — mirror the `is_aggressor`
default-off pattern so existing callers stay byte-identical until deliberately re-baselined; see
§5.3.)*

**N2-pf — Preflop calling ignores raise size / pot odds / effective stack / all-in.** *Severity:
HIGH (Codex).* `sample_preflop_action` sees only categorical `facing` (`personas.py:61`): a min-open
and a 10× open both resolve to `vs_rfi`; a small 3-bet and an all-in 3-bet both `vs_3bet`. Real
players' continue frequency is price- and stack-sensitive.
→ **Fix:** pass raise size, pot, effective stack, and all-in state into the preflop sampler; author
defense elasticity separately for opens / 3-bets / 4-bets / shoves. *(Larger; changes the preflop
engine signature.)*

**F5 — One pack per archetype (enum-locked) → blocks sub-types.** *Severity: MED. Both.*
`VillainType` has one `passive_fish` / `calling_station` slot (`archetypes.py:8`); the loader keys
by that enum and **raises on duplicates** (`personas.py:40`). You cannot ship a "good-range sticky"
station beside an "any-two" station, nor multiple fish sub-types (fit-or-fold vs. any-size). *(Note:
F4 in RES-J — "range quality welded to stickiness" — was **REFUTED**: preflop nodes and
`PersonaPostflop` are independent fields (`models.py:174`); the true blocker is this enum
uniqueness. The user explicitly wants sub-types.)*
→ **Fix:** separate a stable `profile_id` from a broad `archetype`; let several profiles share
`passive_fish`/`calling_station`, archetype used only for grouping. Requires touching the loader,
the reveal/label plumbing, and Hidden-persona mode's read model. **This is the direct enabler for
Hidden-persona mode's richer reads.**

### Tier D — deeper realism (larger, more judgment)

**N5 — Faced price never meets hand equity / draw odds.** *Severity: MED-HIGH (Codex).* Bet size
scales `_FOLD_BASE` alone (`:451`); call and draw bonuses are flat across sizes. A gutshot and a
flush draw defend through the same generic fold-price mechanism rather than comparing required
equity (pot odds) with estimated equity/outs. → Add coarse pot-odds-vs-outs logic, then
persona-specific deviations (chase too wide / overfold scary runouts).

**N4 — Bucket collapse (kicker- and equity-blind).** *Severity: MED-HIGH (Codex).* All top pairs
share TOP_PAIR (kicker-blind); every set/straight/flush/boat/quads is one MONSTER blob; king-high
lumps into ACE_HIGH (`:97`). Very different equities behave identically. → Add kicker strength,
relative-nut class, board vulnerability, blockers, and approximate equity. (Note: the *grader* has
its own separate 4-way taxonomy; this is only the bot engine.)

**F8 — SPR commit is binary + persona-insensitive.** *Severity: MED-HIGH. Both* (Codex: PARTIAL —
commit ≠ forced stack-off; the boosted raise still uses ordinary sizing and a call may be small, so
"SPR≤2 stacks off" overstates it, but fold merit IS zeroed). A scared fish (spr_commit 2.0) never
folds an overpair below SPR 2; identical 3.0 boost for all. → Replace the hard threshold with a
smooth commitment curve over SPR × equity × draw × street, with a per-persona commit strength
(station commits hard, scared fish weakly).

**F6 — `aggression` is one all-buckets/all-streets scalar.** *Severity: MED. Both* (Codex: PARTIAL —
it does not control the air-bluff, which uses `bluff_freq`). Nit's 0.6 also shrinks MONSTER
value-betting: unopened P(bet | monster) = 0.773 vs neutral 0.85; P(bet | top pair) = 0.42. A nit
slow-checking sets is unrealistic. → Split into `value_agg` (made ≥ TOP_PAIR) and the existing
bluff term; set nit value_agg ≥ 1.0, bluff near 0.

**F2 — "passive" fish bluffs more than nit AND station.** *Severity: MED (label/ordering, not a math
bug). Both.* `bluff_freq` 0.12 > 0.04 > 0.03; realized unopened P(bet|air) ≈ 0.104 for fish. A
*passive* profile being the biggest bluffer of the three contradicts the label — though recreational
fish do make loose stabs, so nonzero is fine, just not highest. → Either drop fish `bluff_freq`
below nit and model fish stabs as a separate reactive term, or rename to a spewy-fish sub-type
(pairs with F5). Moves `test_bluff_ordering_across_personas_at_fixed_size` (currently pins
`station < nit < fish < tag < lag < maniac`).

**N6 — Value bet-sizing is strength-independent; fish & station share identical own-sizing.**
*Severity: MED (Codex).* Sizing is independent of strength by design (`:530`) and both packs author
`{0.33:.6, 0.5:.3, 0.75:.1}`. → Permit value/bluff/street/texture sizing **overrides** while
retaining controlled overlap. **⚠️ Constraint:** a naive strength→size map is the deliberate
**anti-sizing-tell no-go** and is pinned by `test_sizing_spread_no_deterministic_strength_to_size`.
Any sizing realism must preserve enough overlap that strength isn't readable from size (the existing
F2 two-stage factorization is the template).

**N2-claude — Same-street 3-bet+ under-folds.** *Severity: LOW.* Already acknowledged in-code
(`:468-474`): when the aggressor re-raises their own street bet, `faced_frac` over-subtracts and
understates the faced size by up to one bucket. Confined to same-street 3bet+ lines; conservative
(under-folds). Document / fix if the memory rework touches that path.

---

## 6. Implementation guide for the fixer

### 6.1 Recommended sequence (ranked, both reviewers)
1. **B1** — fix the fold-aces content bug. Tiny; do first.
2. **A1** — lower `_CALL_BASE[AIR]`, gate air-continue behind a draw. One table edit; biggest
   realism-per-keystroke.
3. **F1** — split `stickiness` → `call_looseness` + `size_elasticity`. The core unlock (fish vs.
   station).
4. **F3 / N3** — add street + scare-card memory to the facing-fold term.
5. **F5** — multiple packs per archetype (`profile_id` vs `archetype`). Also the Hidden-persona
   enabler.
Deeper follow-ups (own slices): N5 (price-meets-equity), N4 (bucket/kicker granularity), F8
(gradient commit), F6 (value/bluff split), N6 (sizing overrides, respecting the no-go), N2-pf
(preflop price/stack awareness).

Each of 1–5 is small enough to be its own ticket. B1+A1 could ship together as a "correctness patch"
even before the larger realism work.

### 6.2 How to add a new lever (the established pattern)
1. Add an **optional** field to `PersonaPostflop` in `content/models.py` (default = current behavior,
   so unauthored packs are byte-identical). Add a `field_validator` if it has a legal range.
2. Wire it into `personas_postflop.py` at the exact merit it should shape. **Do not** insert a new
   `rng` draw before the action `rng.choices` (breaks range_estimate — §6.3).
3. Author values in each of `content/personas/*.json` (and consider tag/lag/maniac for consistency
   even if you don't change their behavior — set the identity-map default).
4. Regenerate/verify `content/schema/persona.schema.json` if that's how the repo surfaces it
   (schema currently under-describes the postflop block — check whether the slice should also
   complete it).
5. Add unit tests; **re-anchor population bands** and **re-record the coverage baseline** (§6.3).

For a **new street/history argument**: give `sample_postflop_decision` a new keyword arg with a
**default that reproduces today's behavior** (mirror `is_aggressor=False`), so the statistical
harness and `range_estimate` stay byte-identical until the live loop (`sim_session.py` /
`table/play.py`) opts in. Only re-baseline when you intend the population to move.

### 6.3 INVARIANTS — do not silently break
- **Domain purity.** `personas.py` / `personas_postflop.py` are pure domain — no web/DB imports
  (`tests/test_domain_purity.py` enforces).
- **Action draw stays the FIRST `rng.choices`.** `range_estimate.py:278` replays
  `sample_postflop_decision` with a duck-typed **capture rng** that grabs the first `choices` call to
  recover the action distribution. Any new randomness must come *after* the action draw (that's why
  F2 bluff-sizing is a two-stage factorization, not a pre-draw).
- **`_AGGRESSION_CAP = 5.6` is the identity map for every non-maniac persona** (all levers ≤ 3.2).
  `test_aggression_cap_binds_maniac_only` + `test_maniac_entropy_floor_in_pinned_spots` pin this.
  Don't lower the cap under 3.2 or raise a non-maniac lever above it without re-checking.
- **Monotonicity guarantees** (pinned): aggression↑ never lowers bet/raise freq
  (`test_monotonicity_aggression_never_lowers_bet_raise_freq`); stickiness↑ (or its successor
  looseness↑) never lowers call freq (`test_monotonicity_stickiness_never_lowers_call_freq`); fold↑
  monotone in faced size (`test_fold_to_bet_monotone_in_faced_size`); fold respects the α ceiling
  (`test_fold_to_bet_respects_alpha_ceiling`). If you split stickiness, update these to the new
  levers while keeping the directional guarantees.
- **Anti-sizing-tell no-go** — `test_sizing_spread_no_deterministic_strength_to_size`. Value hands
  must not become size-readable. Constrains N6.
- **Population bands** — `test_personas_postflop.py` runs a closed-loop full-hand harness against PRD
  §8 VPIP/PFR/AF/WTSD bands + a live-table-texture lineup, at 3σ binomial tolerance. Its header rule:
  **"tune pack levers first, widen test bands only with justification."** Changing levers/tables
  *will* move these; re-anchor with in-file comments (RES-D §4 in Epic 4 is the precedent).
- **Coverage baseline** — `test_coverage_baseline.py` (fixed seed, 400 hands,
  `tests/data/coverage_baseline.json`). It asserts the played `total` is unchanged (harness
  invariant) and `graded ≥ baseline`. **Any persona-play change (preflop B1 included) alters the
  hand stream → `total` shifts → you MUST re-record** deliberately via
  `python -c "from tests.test_coverage_baseline import _record; _record()"` from `backend/`, and
  commit the fixture with the slice. Verify graded coverage did not regress.
- **Grader untouched.** Do not edit `grade_map*.py` / `postflop.py` graders for persona realism.
  `spot_signature()` and `TAXONOMY_VERSION` stay frozen (they're the grader's, not the bots').
- **Bluff ordering** — `test_bluff_ordering_across_personas_at_fixed_size` pins the persona bluff
  ranking; F2 relabel must update it deliberately.

### 6.4 Verification checklist
- `cd backend && ruff check .`
- `./scripts/verify.sh` (backend tests + boot probe).
- Targeted: `pytest tests/test_personas_postflop.py tests/test_personas.py tests/test_coverage_baseline.py -q`.
- Re-record `coverage_baseline.json` (§6.3) if the hand stream changed; eyeball the graded delta.
- Re-anchor population bands in `test_personas_postflop.py` with a comment justifying each moved
  band (levers-first).
- Regenerate the computed distribution tables in §4 for the changed personas and sanity-check them
  against the intended behavior (e.g. station fold-rate should be roughly *flat* across sizes after
  F1; air-call should be near zero after A1).
- If FE-visible (unlikely for pure bot-behavior work): confirm no wire/type change; the persona
  engine has no direct FE surface.

---

## 7. Research anchors (reputable)
- **Calling station = "inelastic calling range … call or fold regardless of the bet size"**; WTSD
  ≥ 36, W$SD < 45, VPIP−PFR gap ≥ 15 —
  [Upswing](https://upswingpoker.com/calling-stations-poker-strategy/),
  [PokerCoaching VPIP](https://pokercoaching.com/blog/vpip-poker-stat/),
  [ThePokerBank elastic/inelastic](https://www.thepokerbank.com/strategy/concepts/elastic-inelastic/).
- **Fish / fit-or-fold recreational = wide VPIP, folds when it misses; ≥ 2 sub-types** (folds-to-big
  vs. treats-big-as-normal) —
  [BlackRain79](https://www.blackrain79.com/2015/08/flop-strategies-versus-bad-poker.html),
  [Upswing bad players](https://upswingpoker.com/snowball-winnings-bad-poker-players/).
- **Nit = VPIP < 15 / PFR < 12, near-nut raises only, "runs scared when an overcard hits the
  turn"** — [Upswing nits](https://upswingpoker.com/nits-tight-player-poker-strategy/),
  [PokerCoaching nits](https://pokercoaching.com/blog/poker-nits/).
- **Opponent-modeling literature** uses board-texture-conditioned reaction trees / equity-aware
  nodes as the standard primitive — [Bayes' Bluff](https://arxiv.org/pdf/1207.1411),
  [Pluribus](https://www.science.org/doi/10.1126/science.aay2400).

## 8. Open questions for the fixer's requirements interview
- How deep before diminishing returns at live $2/$3 — do we fix all of A–D, or ship A+B and stop?
- Does equity-vs-price (N5) / kicker granularity (N4) stay heuristic, or is this the trigger to
  revisit the **solver-baseline no-go**? (Heuristics get "simplified-but-winning," never GTO-exact;
  EVs stay labeled *approximate*.)
- Sub-type roster (F5): how many fish/station variants, and what distinguishes each — and how does
  Hidden-persona mode surface/hide them?
- Sizing realism (N6) vs. the anti-sizing-tell no-go — how much size signal is acceptable?
- Sequencing vs. Hidden-persona mode: confirm the prerequisite (fake tells → fake reads) and which
  realism fixes must land before it.

---

## 9. Part II — the aggressive personas (maniac / LAG / TAG)

Second dual review, 2026-07-23 (same method; both reviewers verified every number against live
code). Verdicts: **Codex FAIL, Claude PASS-WITH-ISSUES**. The engine (§2) is unchanged — these three
differ only in levers + preflop ranges. **The two root causes are identical to §5's:** the engine is
street-blind/memoryless, and single scalars (`stickiness`, `aggression`) each do too much. So the
Part-I fixes repair all six personas; the river-specific damage is just *louder* on the aggressive
three because their `aggression`/`bluff_freq` are high.

### 9.1 Authored levers
| Lever | maniac | LAG | TAG | note |
|-------|--------|-----|-----|------|
| `aggression` | **15.0 → capped 5.6** | 3.2 | 2.4 | `agg_scale = min(aggression, 5.6)` — see M1 |
| `stickiness` | 0.55 | 0.55 | 0.60 | low → these fold to size somewhat |
| `bluff_freq` | 0.55 | 0.35 | 0.22 | drives air bet/raise mass |
| `spr_commit` | **4.0** | 3.0 | 2.5 | maniac commits OVERPAIR+ at SPR≤4 (most pots) |
| `multiway_bluff_damp` | 0.85 | 0.65 | 0.55 | maniac barely damps multiway |
| postflop `sizing` | 0.75/1.0/1.5 (big) | 0.33/0.5/0.75/1.0 | 0.33/0.5/0.75 (small-lean) | + full `sizing_by_node` each |
| preflop `sizing` | open 4.5 / 3bet **5.5×** / 4bet 3.0× | 3.0 / 3.5× / 2.4× | 3.0 / 3.5× / 2.4× | maniac 3bet ≈ 24.75bb is oversized (N4) |

Preflop ranges: **maniac** raises ~85% of its top mixes every seat **but also has a `limp 1.0` mix
every position**; **LAG** opens `raise 1.0 / raise .4 / limp .7` of suited connectors from UTG on;
**TAG** is `raise 1.0 / raise .5`, **no limp** (correct). Response nodes (`vs_rfi/3bet/4bet`) are all
`positions: null` (position-blind — N1).

### 9.2 Computed ground truth — facing a medium river bet (fold / call / raise, heads-up)
Recomputed from live code (Codex, independently); §4's method regenerates them. River ⇒ draw NONE.
```
MANIAC  middle_pair  0.167 / 0.450 / 0.382
        top_pair     0.041 / 0.416 / 0.543
        air (code)   0.435 / 0.228 / 0.338     # F2 two-stage bluff-sizing ×1.236 lifts the air-raise
LAG     top_pair     0.053 / 0.542 / 0.405
TAG     top_pair     0.056 / 0.624 / 0.320
```
**Read it:** the maniac raises medium/one-pair hands for "value" on the river (MP 38%, TP 54%) and
calls busted air 23% — it essentially cannot fold a pair. Rivers should be *polarized* (raise nuts
or bluff, never a medium hand). LAG/TAG raise one pair 40%/32% — also far too high.

### 9.3 Findings (aggressive) — severity is the cross-review resolved value

**M2 — Maniac river over-raise / over-call; cannot fold a pair.** *HIGH. Both (Codex Critical).*
Streetless merits (`:235,477`) reuse the flop rulebook on the river. Raises MP 38% / TP 54%, calls
air 23%. **Attribution fix vs the earlier ledger:** the *air*-raise runs the bluff path
`0.3×bluff_mass` (driven by `bluff_freq` 0.55, `:488`), **not** the aggression cap; only MP/TP raises
use capped agg. → **Fix:** street gate — on the river floor `_RAISE_BASE[MIDDLE_PAIR]` and
`[TOP_PAIR]` to ≈0 (bet/check/call, not raise); near-zero air calls; polarize raises to
TWO_PAIR_PLUS+ / bluff-cell. *This is the direct fix for the user-reported "over-calls river / weird
choices."*

**M7 — TAG/LAG raise one pair facing bets too often (40% / 32%).** *HIGH. Both.* `RAISE_BASE[top_pair]
× agg_scale` (`:490`) inflates once fold merit collapses under price and everything normalizes. Real
TAG/LAG mostly *call* one pair; raises are polarized. → Same street/polarization fix as M2.

**M3 — Maniac & LAG open-limp preflop.** *HIGH. Both (Codex: partial — an intentional SB limp can be
sound).* maniac `limp 1.0` mix every seat; LAG limps 70% of SCs from UTG (`lag.json:31,40,49`).
Aggressive archetypes are **raise-or-fold** (PFR tracks VPIP within ~5%). → **Fix:** delete the
non-SB open-limp mixes for maniac/LAG (fold or fold-into-raise). Pure content edit; TAG already
correct.

**M5 — Memoryless barreling; `bluff_mass` constant flop = turn = river.** *HIGH. Both (Codex/Claude:
literal "55% each street" is loose — draws, buckets, and `sizing_by_node` shift the *effective* rate;
the missing give-up model is the real defect).* No street/history arg (`:381`); raw mass `:430`. Real
bluff frequency **declines** by street (river most selective). → **Fix:** thread street (from
`len(board)`) and decay `bluff_mass` per street; add explicit give-up / continuation logic keyed to
prior aggression + runout.

**N1 — Preflop response ranges are position/size/stack-blind.** *HIGH. Both (Codex Critical).* Every
`vs_rfi/3bet/4bet` node is `positions: null` and keys only on categorical `facing` (`personas.py:61`)
— a TAG answers a UTG open exactly like a BTN open, and a min-raise exactly like a shove. This is the
aggressive-side face of §5's **N2-pf**. → **Fix (shared with N2-pf):** pass raise size + position +
effective stack into the preflop sampler; author position-split response nodes.

**M1 — Maniac aggression 15.0 is dead above 5.6.** *MED. Both (Codex HIGH).* `min(aggression, 5.6)`
(`:431`) clamps the value-raise multiplier; the extra 9.4 does nothing. Worse, the maniac's
*signature* air-barreling uses `bluff_freq`, not `aggression` (`:487,495`), so the lever that *names*
the maniac barely touches its play (only value-raises of made hands). The merit multiplier also isn't
directly comparable to the observed AF≈5. → **Fix:** re-author a meaningful ≤5.6 value, or replace the
hard cap with a soft saturation (tanh) so a higher lever still strictly orders maniac above LAG at
every merit; calibrate against observable AF/action-rates, not lever magnitude.

**M4 — One `aggression` scalar spans every bucket & street.** *MED. Both (both corrected the ledger:
value & bluff are NOT welded — air uses `bluff_freq`, made hands use `aggression`, `:487`).* The real
flaw: a single dial multiplies every non-bluff bucket's raise merit uniformly, so 5.6× hits weak made
hands the same as monsters. → **Fix:** split into value/bluff × bucket (and street), or scale
`_RAISE_BASE` by rung so weak buckets get a fraction of `agg_scale`.

**M6 — Maniac `spr_commit 4.0` overplays OVERPAIR+/TPTK.** *MED. Both (Codex: "most pots" overstated —
SPR≤4 is mainly 3bet pots; still, a committed maniac overpair raises ~92% facing a bet).* Binary cliff
+ shared 3.0 boost (`:504-517`). → **Fix:** graded commitment over (spr_commit − live SPR) × equity ×
draw × street; keep TPTK able to fold rivers. (Same as §5's F8.)

**N3 — Maniac 4bet/5bet range tighter-or-equal to LAG's (archetype inversion).** *MED. Both.* Maniac
5bet-shove range == LAG's (QQ+/AK; `maniac.json:191`, `lag.json:168`); maniac 4bets TT+/AJs+/AQo pure
and never light-jams. A maniac should re-jam *lighter* (Axs / small-pair bluff-shoves), not tighter.
→ **Fix:** widen maniac's 4bet value+bluff split; add light 5bet-shove bluffs; position-split the
3bet node; mix some KK/AA flats for traps.

**N2 — Authored preflop mixes silently shadowed.** *MED. Codex.* First-match-wins (`personas.py:81`)
makes overlapping combos in later mixes unreachable — e.g. TAG `ATs/KJs/KQo` sit in a later call-mix
behind an earlier 3bet mix (`tag.json:117`), so those calls never fire; the authored range ≠ the
played range. Overlaps also exist in open/limp lists. → **Fix:** add a content validator that rejects
overlapping combos across mixes in a node (pairs with the B1 overlap validator in §4).

**M8 — `stickiness` double-duty.** *LOW. Both.* Same as §5's **F1** (`:484` + `:377`). Splitting it
(`call_looseness` + `size_elasticity`) also lets aggressive personas' fold-to-size be tuned
independently.

**N4/N5 — Maniac air aggression caps at `bluff_freq`; oversized 3bet.** *LOW. Claude.* Unopened air
bet ≈ 0.55 (`:495`, bluff_cell `agg = bluff_mass`) so the maniac's relentless c-bet under-fires vs a
real ≈80-90%; and 3bet `5.5×` a 4.5bb open ≈ 24.75bb is off the charts. → **Fix:** let the bluff-bet
floor scale with an agg-derived term for high-agg personas; drop `threebet_mult` to ~3.0-3.5 (or
randomize if "erratic sizing" is the goal, don't fix it huge).

### 9.4 Aggressive fix sequence (folds into §6.1)
0. **Street-aware refactor** — the single highest-value change; repairs M2 + M7 + half of M5 **for
   all six personas** (thread street from `len(board)`; river polarization + no one-pair raises + no
   air calls). Slot it as the new §6.1 step 0, ahead of the non-aggressive quick wins.
1. **Delete open-limp mixes** for maniac/LAG (M3) — trivial content.
2. **Position/size-aware preflop responses** (N1 / N2-pf) + rebuild maniac 4bet/5bet + 3bet-sizing
   (N3, N4) + overlap validator (N2).
3. **Decay `bluff_mass` by street + give-up lines** (M5 remainder).
Shared deeper work (with §5): value/bluff × bucket/street split (M4), graded SPR commit (M6),
`stickiness` split (M8).

All §6.3 **INVARIANTS** apply unchanged. Note especially: a `street` argument must default to
today's behavior (mirror `is_aggressor=False`) so `range_estimate` + the population harness stay
byte-identical until deliberately re-baselined; and `test_bluff_ordering_across_personas_at_fixed_size`
currently pins `station < nit < fish < tag < lag < maniac` — any bluff-path change to the aggressive
three must re-anchor it deliberately. Changing maniac/LAG/TAG **will** move the population bands
(VPIP/PFR/AF/WTSD) and the coverage baseline — re-record per §6.3.

### 9.5 Research anchors (aggressive)
- Maniac VPIP ~55 / PFR ~37 / **AF ≈ 5**, raises-or-folds (no open-limp) —
  [ThePokerBank styles](https://www.thepokerbank.com/strategy/general/playing-styles/),
  [BlackRain79](https://www.blackrain79.com/2015/11/what-to-do-when-fish-fight-back.html).
- TAG ~15-20% / LAG ~25-40%; LAG same-or-greater postflop aggression on a wider range, near-TAG from
  EP — [SplitSuit LAG](https://www.splitsuit.com/playing-lag-loose-aggressive-poker),
  [Upswing TAG](https://upswingpoker.com/tight-aggressive-tag-strategy-passive/).
- Rivers polarized (omit medium-strength); bluff freq declines by street —
  [Upswing polarized/linear](https://upswingpoker.com/polarized-vs-linear-ranges/),
  [GTO Wizard river play](https://blog.gtowizard.com/principles-of-river-play/).

---
*Companion docs: `docs/ai-dlc/research/RES-J-persona-realism.md` (findings summary — Part I
non-aggressive + Part II aggressive), `docs/research/player-types-and-exploits.md` (exploit strategy
content), the roadmap "Persona realism" NEXT slice (now all 6 personas). This doc is the
engine-and-implementation reference; RES-J is the review record.*
