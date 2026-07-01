# Spec — Phase 2b: Facing a Flop C-Bet (Defense)

> Delta spec for **Phase 2b** only. Builds on 2a (no rebuild, no new migration). The other side of the 2a spot: hero CALLED preflop (BB), checked, and now FACES a flop c-bet — decides **fold / call / raise (check-raise)**. Strategy source: `docs/research/02-postflop-strategy.md` (§4.1–4.4, §8.3 MDF table). STOP at the plan gate — no code until approved.

## Goal
Add the **vs-c-bet defense decision** (HU single-raised pots, hero = BB defender OOP) graded by **texture + range-advantage (defender's view) + pot-odds/MDF + hand category**, with a `vs_cbet` drill mode and frontend. Same heuristic family as 2a — **NOT equity-backed** (range-vs-range equity stays deferred; the equity engine remains quiz-only).

## Key decisions (incl. refuter fixes)
- **Dedicated defender-perspective range advantage — do NOT reuse `range_advantage()` via a position trick.** (Refuter blocker 1: the aggressor baseline `+1` plus `high_board +1` makes a defender-favored *high & wet* board, e.g. K♥Q♥J♥, score `"neutral"` — the defender's edge there is unreachable.) Add `range_advantage_defender(aggressor_pos, defender_pos, texture) -> "defender"|"aggressor"|"neutral"`: NO preflop-aggressor baseline for the defender; defender gains edge on low / connected / wet boards, loses it on high / dry boards; OOP penalty applies to the **defender**. `range_advantage()` (2a) is untouched.
- **Aggressor position comes from `spot.facing`, not `_villain_pos(spot)`.** (Refuter blocker 2: `_villain_pos` depends on player-list order — fragile.) The builder sets `facing = opener`; the grader reads `spot.facing`.
- **New grader path** `grade_vs_cbet()` — does NOT reuse `grade_cbet()`. Action space is fold/call/raise (no two-bet-size ambiguity), so action matching is by `ActionType` alone. **Raise decisions must carry a size** (`Decision` validation requires it) — the builder sets a concrete raise `min_bb`, and tests submit a sized raise. (Refuter blocker 5.)
- **No new migration.** vs_cbet attempts persist as `DrillAttempt` (provider `"heuristic"`) exactly like 2a postflop. Postflop SRS review remains deferred.
- **Faced bet size drives defense width** (MDF): a small (33%) c-bet → defend wider (call more, fold less); a big (75%) c-bet → fold more. The grader reads the faced size + the current pot from the spot.
- **Pot includes the c-bet at the decision point.** (Refuter blocker 3.) The builder sets `pot_bb = flop_pot + cbet_size` so the grader's pot-odds (`faced_bet / (pot)`) are correct.
- **Faced-bet size is in the postflop signature.** (Refuter blocker 4: small vs big c-bet on the same texture must NOT collapse to one SRS bucket — the correct defense differs by size.) Add a `faced_bet_bucket` to `_postflop_signature` (`"none"` for the 2a c-bet node where hero is the bettor; `"small"`/`"big"` for vs_cbet). This changes **postflop** hashes only — safe, because no postflop SRS rows are persisted yet (postflop review is deferred); **preflop hashes stay byte-identical** (separate branch).

## In scope
1. **Contracts (additive + one signature change):** `NodeContext.VS_CBET`; `LeakCategory.VS_CBET = 201`; `leak_category_for` gains a `VS_CBET → VS_CBET` case. **`_postflop_signature` gains a `faced_bet_bucket`** term (`"none"` / `"small"` / `"big"`), derived from the faced c-bet size (the largest opponent `bet` in `action_history` relative to pot, `"none"` if hero is the bettor). Preflop path unchanged.
2. **Grader** `domain/postflop.py::grade_vs_cbet(spot, hero_range, villain_range, decision) -> EvaluationResult`:
   - Inputs: board, hero hole cards, the faced c-bet size + current pot (from `spot`), `hero_range` (defender's preflop call range), `villain_range` (the c-bettor's range).
   - Compute `texture`, `defender_adv = range_advantage_defender(spot.facing, hero.position, texture)`, hero `_hand_category` (reuse 2a: strong / weak_made / draw / air), and the **pot odds** of calling (`faced_bet / pot`, pot already includes the c-bet).
   - Recommend **fold / call / raise** with per-action frequency + a documented PROXY EV + correctness, output as the existing `EvaluationResult` (per_action over FOLD/CALL/RAISE, freq+EV, leak `VS_CBET`, rationale + "why"). Heuristic shape:
     - **strong** (two-pair+/set/strong top pair) → raise (value) / call mix; never fold.
     - **draw** (FD/OESD) → call; **raise (semibluff)** when defender has range advantage on a wet board.
     - **weak_made** (middle/weak pair) → call vs small bets / good price; fold to big bets on aggressor-favored boards.
     - **air** → fold; small check-raise-bluff frequency only on low-connected boards where the defender's range advantage supports it.
     - Bet-size term: small faced bet shifts EV toward call (defend wider); big faced bet shifts EV toward fold.
3. **Provider routing** `domain/providers/postflop.py`: `PostflopHeuristicProvider.supports()` accepts CBET **or** VS_CBET; `evaluate()/optimal()` dispatch CBET→`grade_cbet`, VS_CBET→`grade_vs_cbet`. CompositeProvider unchanged (still routes by street).
4. **Spot builder** `domain/scenarios.py::build_vs_cbet_spot()` — reuse the 2a HU SRP pairing, but: hero = **BB defender (OOP)**, villain = **opener (IP) who has c-bet**. `players = [BB(is_hero=True), opener]`. Deal hero a hand from the BB **call** range; deal a 3-card flop; sample a c-bet size (33% or 75% of the flop pot); append the villain's `bet` to `action_history`. **`pot_bb = flop_pot + cbet_size`** (so pot odds are correct); `spr` recomputed on the remaining effective stack vs this pot. `node_context=[VS_CBET]`, `to_act=hero`, legal = **fold / call(min_bb = faced bet) / raise(min_bb = check-raise ≈ 3× the c-bet, max_bb = remaining stack)**; set `hero_range` = BB call range, `villain_range` = opener RFI range; `facing` = opener. A `sample_vs_cbet_spot()`.
5. **Drill wiring** `api/v1/drill.py`: `/drill/next?mode=vs_cbet` → `sample_vs_cbet_spot` (grid `{}`, like all postflop). `/drill/grade` already routes through the composite provider — no change. (`_next_review` postflop fallback already covers it.)
6. **Frontend:** add a **"Facing c-bet"** drill mode; the betting-line summary must render the villain's **`bet`** action (today `bettingLine()` shows raise/call/limp but not `bet`) so the player sees "BB checks · CO bets X". Decision bar already handles fold/call/raise. Board already renders (2a).

## Contract changes
- `NodeContext.VS_CBET = "vs_cbet"` (additive).
- `LeakCategory.VS_CBET = 201` (additive; postflop 200–299 namespace).
- `leak_category_for`: `VS_CBET → LeakCategory.VS_CBET` (additive).
- `_postflop_signature`: **add `faced_bet_bucket`** → **changes postflop hashes** (both CBET and VS_CBET). Safe: no postflop SRS rows persist yet. **Preflop hashes unchanged** (separate branch — guarded by an existing test).
- No DB schema change / migration. 2a `grade_cbet` logic untouched (only the provider's dispatch + `supports()` widen).

## Out of scope (deferred)
- Turn / river / multi-street barreling · check-raising as the aggressor's response · 3-bet-pot postflop · **equity-backed** range advantage · postflop SRS review (texture/SPR columns + migration) · facing a check-raise · multiway · solver · mastery-gating · squeeze.

## Constraints
Live/simplified · grading behind `StrategyProvider` via the composite · domain pure (postflop grader has no web/DB imports) · content reused from existing preflop packs (no new content files needed; ranges derived as in 2a) · **no new migration** · **no equity calls in the grader** (positional+texture+pot-odds only) · CSS tokens + AA contrast (any new UI) · any new deps → `RUN-THESE-COMMANDS.md` (target: none).

## Verify-by
1. `pytest` green incl:
   - **`range_advantage_defender` reachability** — a low/connected/wet board (e.g. 8♥7♥6♣) → `"defender"`; a high/dry board (A♠K♦2♣) → `"aggressor"`; AND a defender-favored **high & wet** board (e.g. K♥Q♥J♥, which the 2a reuse-trick could not reach) → `"defender"` or at least not `"aggressor"`.
   - **grader anchors** — (a) strong hand (set/two-pair) vs a c-bet → raise or call, never fold; (b) pure air on a high/dry aggressor-favored board vs a big c-bet → fold is best; (c) a strong draw on a wet defender-favored board → call, with raise (semibluff) a defensible mix; (d) **bet-size monotonicity**: for a fixed marginal hand + board, a small (33%) faced bet gives **higher call freq and lower fold freq** than a big (75%) bet; (e) leak = `VS_CBET (201)`.
   - **pot-odds correctness** — `pot_bb` at the decision point equals flop pot + c-bet (a 33%-pot c-bet yields ~25% pot odds, not ~33%).
   - **raise carries a size** — the grader accepts `Decision(action=RAISE, size_bb=…)` (no `ValueError`); the builder's raise `LegalAction` has a concrete `min_bb`.
   - **Builder:** valid flop spot, hero OOP = BB (`is_hero`), villain `bet` in `action_history`, `spot.facing` = opener, legal = fold/call/raise, ranges set, cards disjoint.
   - **Signature:** same texture + **different faced-bet size → different** signature (no SRS conflation); same texture + same size → same signature; **preflop signatures byte-identical** to before.
   - **Provider:** vs_cbet spots grade via the postflop provider; 2a c-bet spots still grade (now with a `"none"` faced-bet bucket); preflop unaffected.
2. Backend boots; `/drill/next?mode=vs_cbet` returns a flop defense spot that grades + persists; 2a postflop + preflop modes + quizzes unaffected.
3. Frontend builds + typechecks; live (Playwright): the Facing-c-bet mode shows board + "CO bets X" line + Fold/Call/Raise bar + grades with a sane "why".
4. CSS contrast/token check passes (no raw hex in new CSS).
