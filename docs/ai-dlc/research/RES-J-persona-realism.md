# RES-J — Persona realism review (nit / passive_fish / calling_station)

**Date:** 2026-07-23 · **Trigger:** user-reported unrealistic decision-making before building
Hidden-persona mode. **Method:** Claude engine audit + dual adversarial review — a web-capable
Claude Opus `general-purpose` refuter + Codex Sol (`gpt-5.6-sol`, direct `codex exec`), each fed
the same engine explainer + an 8-item flaw ledger and told to distrust it. Scope: the three
NON-aggressive personas only (nit, passive_fish, calling_station); lag/tag/maniac untouched.

**Verdicts:** Codex Sol = **FAIL**. Claude Opus = **PASS-WITH-ISSUES (leaning FAIL)**. Both agree
the two loose types (fish, station) are modeled unrealistically; the nit is closer but shares the
structural gaps.

## The engine in one paragraph
Persona identity = **5 scalar levers** (`aggression`, `stickiness`, `bluff_freq`, `spr_commit`,
`sizing`) in `content/personas/*.json`, multiplied into **shared** merit tables in
`backend/app/domain/personas_postflop.py`. The bot buckets its hand into 7 made tiers
(MONSTER…AIR) + a draw class, looks up shared fold/call/raise merits, scales by the levers,
normalizes, and `rng.choices`. Preflop (`personas.py`) is pure content range lookup. **All
personality lives in 5 numbers over one rulebook — that is the root constraint.**

## Findings (cross-review consensus)

| ID | Issue | Claude | Codex | Resolved | Root |
|----|-------|--------|-------|----------|------|
| **N1-pf** | Calling station **folds AA/KK/AKs 40%** unopened preflop | — | **HIGH (new)** | **HIGH — bug** | `calling_station.json:21,32` premiums tagged `raise .6/fold .4`; first-mix-wins (`personas.py:81`) means the limp mix never catches them |
| **F7 / N1-air** | Loose personas **call pure air** (no pair/draw) absurdly — station ~78% w/ 72o on QJ9; nit ~57% air to a small bet; live river showdown calls with nothing | CONF HIGH | CONF HIGH | **HIGH** | `_CALL_BASE[AIR]=0.25 × stickiness` (`personas_postflop.py:244,484`); also king-high buckets as ACE_HIGH (`:97`) → .40 base |
| **F1** | **Elasticity collapse** — station should be *inelastic* (calls any size), fish *elastic* (folds to big); both welded to one `stickiness` dial → both mildly elastic, can't diverge | CONF HIGH | CONF HIGH | **HIGH** | `stickiness` sets BOTH the flat call multiplier (`:484`) AND the price-damp exponent (`:372-378`, DAMP 0.15) |
| **F3 / N3** | **Memoryless** — no street/history/initiative/scare-card term; flop=turn=river given same bucket; "runs scared when an overcard hits" is unrepresentable | CONF HIGH (F3) + MED (N3) | PARTIAL HIGH (F3) + HIGH (N3) | **HIGH** | `sample_postflop_decision` takes no street/history args (`:381`); `is_aggressor` only changes sizing (`:363`). *Partial* scare exists via per-street re-bucketing (top pair→middle pair) |
| **N2-pf** | Preflop calling **ignores raise size / pot odds / eff. stack / all-in** — a min-open and a 10× open both resolve to `vs_rfi`; small 3-bet == shove | — | HIGH (new) | **HIGH** | `sample_preflop_action` only sees categorical `facing` (`personas.py:61`) |
| **N5** | Faced **price never meets equity/outs** — a gutshot and a flush draw defend through the same generic fold-price mechanism | — | HIGH (new) | **MED-HIGH** | bet size scales `_FOLD_BASE` alone (`:451`); call/draw bonuses flat across sizes |
| **N4** | **Bucket collapse** — all top pairs identical (kicker-blind); every set/straight/flush = one MONSTER blob | — | HIGH (new) | **MED-HIGH** | `_made_bucket` (`:101,118`) — no kicker/relative-nut/equity granularity |
| **F8** | **SPR commit binary + shared 3× boost** — fold merit zeroed at `SPR ≤ spr_commit` for OVERPAIR+/strong-draw, identical `_COMMIT_AGG_BOOST=3.0` for all; a "scared" fish shouldn't commit like a station | MED-HIGH | PARTIAL HIGH | **MED-HIGH** | `:506-517`. Codex nuance: commit ≠ forced stack-off (call may be small, boosted raise uses normal sizing) |
| **F6** | `aggression` is one all-buckets/all-streets scalar — nit 0.6 also shrinks MONSTER value-betting (can't say "bet value hard, never bluff") | MED | PARTIAL MED | **MED** | `:499,487`. Nuance: air-bluff uses `bluff_freq`, not aggression |
| **N6** | Value bet-sizing is strength-independent; fish & station author **identical** own-sizing (`.33/.5/.75 = .6/.3/.1`) | — | MED (new) | **MED** | `:530`; `passive_fish.json:12` == `calling_station.json:12` |
| **F2** | "Passive" fish bluffs MORE than nit AND station (0.12 > 0.04 > 0.03) — contradicts the label | MED (downgrade) | PARTIAL MED | **MED — label** | authored `bluff_freq`. Both: real recreational fish DO stab, just not *most* |
| **F5** | **One pack per archetype** — `VillainType` has a single fish/station slot; loader rejects duplicates → can't ship "good-range sticky" + "any-two" variants | LOW | MED | **MED** | `archetypes.py:8`, `personas.py:40` |
| **F4** | Range quality "welded" to stickiness | CONF MED | **REFUTED LOW** | **DOWNGRADED → folds into F5** | Codex correct: preflop nodes & `PersonaPostflop` are independent fields (`models.py:174`); the real blocker is F5 (one pack per type) |
| **N2-claude** | Same-street 3-bet+ under-folds (already acknowledged in-code) | LOW-MED | (≈ F8 area) | **LOW** | `:468-474` comment |

## Ranked fix list (both reviewers' consensus)
1. **Station folding aces 40%** — tiny content fix. It's a bug.
2. **Kill pure-air calls** — drop `_CALL_BASE[AIR]` toward ~0.05–0.10, gate air-continue behind a draw. One table edit, biggest realism-per-keystroke.
3. **Split `stickiness` → `call_looseness` + `size_elasticity`** — the axis that *defines* station (inelastic) vs fish (elastic). Unlocks the whole documented distinction.
4. **Add memory** — thread street + prior action + scare-card (new overcard / flush-straight completion / paired board) into the facing-fold term; persona-specific scare sensitivity.
5. **Multiple packs per archetype** — separate `profile_id` from `archetype`; lets sub-types (good-range sticky station, fit-or-fold fish vs any-two fish) coexist. Also the enabler for richer Hidden-persona reads.

Deeper (larger): equity-vs-price interaction (N5), bucket granularity/kickers (N4), gradient SPR commit + per-persona commit strength (F8), split value/bluff aggression (F6).

## Dependency on Hidden-persona mode
Hidden-persona mode hides the villain label so the player **develops reads from play**. If the
bots play unrealistically (fold aces, call 78% air, no scare-card behavior), the reads trained are
**against tells that don't exist in real poker**. Persona realism is therefore a **prerequisite/
strong companion** to Hidden-persona mode teaching anything real — the two are coupled, not
independent.

## Research anchors (reputable)
- Calling station = "**inelastic** calling range … call or fold regardless of bet size"; WTSD ≥36,
  W$SD <45, VPIP−PFR gap ≥15 — [Upswing](https://upswingpoker.com/calling-stations-poker-strategy/),
  [ThePokerBank elastic/inelastic](https://www.thepokerbank.com/strategy/concepts/elastic-inelastic/).
- Fish / fit-or-fold recreational = wide VPIP, folds when misses; **≥2 sub-types** (folds-to-big vs
  treats-big-as-normal) — [BlackRain79](https://www.blackrain79.com/2015/08/flop-strategies-versus-bad-poker.html),
  [Upswing bad players](https://upswingpoker.com/snowball-winnings-bad-poker-players/).
- Nit = VPIP<15/PFR<12, near-nut raises only, "**runs scared when an overcard hits the turn**" —
  [Upswing nits](https://upswingpoker.com/nits-tight-player-poker-strategy/),
  [PokerCoaching](https://pokercoaching.com/blog/poker-nits/).
- Opponent-modeling literature uses board-texture-conditioned reaction trees / equity-aware nodes
  as the standard primitive — [Bayes' Bluff](https://arxiv.org/pdf/1207.1411),
  [Pluribus](https://www.science.org/doi/10.1126/science.aay2400).

---

# RES-J (Part II) — Aggressive personas (maniac / LAG / TAG)

**Date:** 2026-07-23 · **Trigger:** same user, second pass — "maniac over-calls at the river / makes
weird choices; LAG & TAG don't play within their range realistically." **Method:** identical dual
adversarial review (web-capable Claude Opus `general-purpose` + Codex Sol `gpt-5.6-sol`, direct
`codex exec`), each fed an engine explainer + an M1–M8 flaw ledger + research anchors, told to
distrust it and to /research reputable sources. **Both verified every ledger number against live
code** and recomputed the distributions.

**Verdicts:** Codex Sol = **FAIL**. Claude Opus = **PASS-WITH-ISSUES**. Both: the three aggressive
personas are materially unrealistic, **river play worst**; two root causes (memoryless/street-blind
engine + one-dial-does-two-jobs) are the **same** as Part I — the fixes are shared across all six
personas.

## Authored levers (aggressive three)
| Persona | aggression | stickiness | bluff_freq | spr_commit | mw_damp | postflop sizing |
|---|---|---|---|---|---|---|
| MANIAC | **15.0 → capped 5.6** | 0.55 | 0.55 | 4.0 | 0.85 | 0.75/1.0/1.5 (big) |
| LAG | 3.2 | 0.55 | 0.35 | 3.0 | 0.65 | 0.33/0.5/0.75/1.0 |
| TAG | 2.4 | 0.60 | 0.22 | 2.5 | 0.55 | 0.33/0.5/0.75 |

## Verified facing-a-river-bet distributions (fold / call / raise, heads-up, medium bet)
Recomputed independently by Codex from live code (`personas_postflop.py`); ledger reproduced exactly
except maniac-air (F2 two-stage bluff-sizing ×1.236 lifts the air-raise):
- MANIAC middle_pair **0.167 / 0.450 / 0.382** · top_pair **0.041 / 0.416 / 0.543** ·
  air (actual code) **0.435 / 0.228 / 0.338**
- LAG top_pair **0.053 / 0.542 / 0.405** · TAG top_pair **0.056 / 0.624 / 0.320**

## Findings (cross-review consensus)
| ID | Issue | Claude | Codex | Resolved | Root |
|----|-------|--------|-------|----------|------|
| **M2** | Maniac **river over-raise/over-call**, can't fold a pair (raises MP 38% / TP 54%, calls air 23%) | CONF (partial attr.) | CONF (Critical) | **HIGH** | streetless merits + `_CALL_BASE[AIR]` + capped-agg raise on weak made hands (`:235,477`). River should be *polarized*. **Attribution fix:** the air-*raise* runs the bluff path `0.3×bluff_mass` (driven by `bluff_freq`, `:488`), NOT the agg cap — only MP/TP raises use capped agg |
| **M7** | TAG/LAG **raise one pair** far too often (40% / 32% facing a bet) | CONF HIGH | CONF HIGH | **HIGH** | `RAISE_BASE[top_pair]×agg_scale` inflates once fold collapses under price (`:490`); real TAG/LAG mostly *call* one pair |
| **M3** | Maniac & LAG **open-limp** preflop | CONF HIGH | PARTIAL (SB-limp can be OK) | **HIGH** | maniac limp-1.0 mix every seat (`maniac.json:32…`); LAG limps 70% SCs UTG+ (`lag.json:31,40,49`). Aggressive archetypes are raise-or-fold |
| **M5** | **Memoryless barreling** — `bluff_mass` constant flop=turn=river, no give-up | CONF HIGH | PARTIAL ("55%/street" loose — draws/sizing shift effective rate) | **HIGH** | no street/history arg (`:381`); raw mass at `:430`. Real bluff freq declines by street |
| **N1** | Preflop **response ranges position/size/stack-blind** — TAG answers a UTG open == a BTN open; min-raise == shove | NEW HIGH | NEW Critical | **HIGH** | all `vs_rfi/3bet/4bet` nodes `positions:null`; categorical `facing` only (`personas.py:61`; `maniac.json:161`, `lag.json:137`, `tag.json:112`). *(This is the aggressive-side face of Part-I's N2-pf.)* |
| **M1** | Maniac **aggression 15.0 is dead above 5.6** | CONF MED | CONF HIGH | **MED** | `min(aggression,5.6)` (`:431`); authored 15 (`maniac.json:9`). 9.4 excess does nothing; worse, air-aggression ignores the lever entirely (uses `bluff_freq`) |
| **M4** | One `aggression` scalar spans all buckets & streets | CONF MED | PARTIAL | **MED** | **Both corrected the ledger:** value & bluff are *not* welded (air uses `bluff_freq`, made hands use `aggression`, `:487`). Real flaw: one dial for *every* non-bluff bucket/street |
| **M6** | Maniac `spr_commit 4.0` stacks off OVERPAIR+/TPTK almost always | MED-HIGH | PARTIAL ("most pots" overstated — SPR≤4 mainly 3bet pots) | **MED** | binary cliff + shared 3× boost (`:504-517`); committed maniac overpair raises ~92% facing a bet |
| **N3** | Maniac **4bet/5bet range tighter-or-equal to LAG's** — archetype inversion; never light-jams | NEW MED | NEW HIGH | **MED** | maniac 5bet == LAG 5bet (QQ+/AK; `maniac.json:191`, `lag.json:168`); maniac 4bet TT+/AJs+/AQo pure |
| **N2** | Authored preflop mixes **silently shadowed** by first-match-wins | — | NEW HIGH | **MED** | TAG `ATs/KJs/KQo` in a later call-mix unreachable behind an earlier 3bet mix (`personas.py:81`; `tag.json:117`); overlaps in open/limp lists too |
| **M8** | `stickiness` double-duty (looseness + size-elasticity) | CONF LOW | CONF MED | **LOW** | `:484` + `:377`; same structural flaw as Part I (F1) |
| **N4/N5** | Maniac's **air aggression uses only `bluff_freq`** — caps signature relentless c-bet at ~55% (real ≈80-90%); the lever that *names* the maniac never touches its air | NEW LOW | (≈ N4 initiative) | **LOW** | bluff-raise/air-bet paths bypass `aggression` (`:487,495`); maniac 3bet sizing 5.5×4.5bb ≈ 24.75bb is also oversized (Claude N2) |

## Ranked fix list (aggressive; folds into Part-I sequence)
1. **Street-aware refactor (the big one).** Thread street (derivable from `len(board)`); on the river
   floor one-pair (MIDDLE/TOP) raise merit to ~0 and near-zero air calls, polarize raises to
   TWO_PAIR_PLUS+ / bluff-cell. **Repairs M2 + M7 + half of M5 for ALL six personas at once** — the
   single highest realism-per-effort change and the direct fix for the user-reported river bugs.
2. **Delete open-limp mixes** for maniac & LAG (pure content). Off-archetype passive tell.
3. **Position/size-aware preflop responses** (N1) + rebuild maniac 4bet/5bet + 3bet-sizing so it is
   actually looser/erratic than LAG (N3, N4-sizing). Add overlap validation to kill shadowed mixes (N2).
4. **Decay `bluff_mass` by street + give-up lines** (M5 remainder).
Deeper (shared with Part I): split `aggression` → value/bluff × bucket/street (M4); graded SPR
commit (M6); split `stickiness` (M8).

## Research anchors (aggressive)
- **Maniac** = VPIP ~55 / PFR ~37 / **AF ≈ 5**, "raises and re-raises almost every time," notoriously
  hard to range, long-term loser — **raise-or-fold, does NOT open-limp** —
  [ThePokerBank](https://www.thepokerbank.com/strategy/general/playing-styles/),
  [BlackRain79 maniacs](https://www.blackrain79.com/2015/11/what-to-do-when-fish-fight-back.html).
- **TAG ~15-20% / LAG ~25-40%** hands; LAG = **same-or-greater postflop aggression** than TAG on a
  *wider* preflop range; good LAGs play near-TAG from EP, widen BTN/CO; both AF ≥ 3 —
  [SplitSuit LAG](https://www.splitsuit.com/playing-lag-loose-aggressive-poker),
  [Upswing TAG](https://upswingpoker.com/tight-aggressive-tag-strategy-passive/),
  [BlackRain79 TAG→LAG](https://www.blackrain79.com/2016/06/transitioning-from-tag-to-lag-how-to.html).
- **Rivers are polarized** (value + bluffs, *omit medium-strength*); **bluff frequency declines
  flop→river**; larger bet → more bluffs but value stays the majority —
  [Upswing polarized/linear](https://upswingpoker.com/polarized-vs-linear-ranges/),
  [GTO Wizard river play](https://blog.gtowizard.com/principles-of-river-play/),
  [SplitSuit GTO bluffing](https://www.splitsuit.com/perfect-gto-bluffing).
