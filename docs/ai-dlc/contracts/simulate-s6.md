# Contract map — S6 turn graders + range_advantage rewrite + coverage gate (at HEAD 2026-07-10)

> Read-only scan by contract-mapper (post-wave-1b checkout). Slice S6 of
> `docs/ai-dlc/roadmap/simulate-table.md`. Builds on `contracts/simulate-s5.md` (verified
> accurate at HEAD): `_by_street` dict exists (`composite.py:44-49`), flop-only ValueError
> guards on all 3 graders (`postflop.py:332-333,532-533,708-709`), pinned-hash tests
> (`test_signature.py:202-207`) + turn/river fixtures (`:218-235`), append-rule docstring
> (`srs.py:113-117`).

## 1. `range_advantage()` — dead `node_context` param

`range_advantage(node_context, hero_pos, villain_pos, texture) -> str` returning exactly
`'hero' | 'villain' | 'neutral'` (`postflop.py:103-133`). Scoring: baseline 1.0 (pf aggressor);
+0.5 A-high / +1.0 other high, −1.0 low; +1.0 dry / −1.0 wet; −1.0 connected; −1.0 OOP;
`>= 2.0` hero, `<= -1.0` villain, else neutral. **`node_context` bound, never read.**

Callers (exhaustive, 2): `grade_cbet` `:336-337` (passes `spot.node_context[0] or CBET`);
`grade_vs_check_raise` `:712-716` (passes ctx; 3rd arg deliberately check-raiser's position —
refuter-caught comment `:713-715`). Separate `range_advantage_defender(aggressor, defender,
texture)` (`:449-474`) used only by `grade_vs_cbet` `:537`, returns `defender|aggressor|neutral`.

Return-string consumers (new label = KeyError or silent degrade):
1. Merit maps — `_merits` `{"hero":1.0,"neutral":0.0,"villain":-1.0}[adv]` (`:267`, **KeyError
   on new label**); `_merits_vs_cbet` (`:489`); `_merits_vs_check_raise` (`:646`).
2. `rationale_tags[1]` — 4-wide `[node, adv, cat, wetness]` shape (`:382,:424,:575,:756`).
3. Composer `_ADV` dict (`feedback.py:55-61`), unknown key `.get`-degrades to "range
   advantage unclear" (`:130`).

⚠️ Rewriting to consume `node_context` changes flop output unless flop-context branches
reproduce current arithmetic exactly — merits, freqs, EVs, correctness bands, explanations
all derive from it. Turn branches must return only the 3 canonical labels.

## 2. Flop grader anatomy (template for turn graders)

Signature (all 3): `grade_X(spot, hero_range, villain_range, decision) -> EvaluationResult`;
provider passes `spot.hero_range, spot.villain_range` (`providers/postflop.py:35`).

Consumes: `street` (guard), `board[:3]`, `node_context[0]`, `hero.position/hole_cards`,
`facing`/`players` (`_villain_pos` `:136-145`), `legal_actions` (`_bet_sizes` `:322-326`,
`_faced_call_and_pot` `:477-483`), `pot_bb`, `villain_range` (fold-equity MC, cbet only).

Output (`evaluation.py:61-78`): `EvaluationResult{per_action: [ActionEval{action, size_bb,
frequency, ev_bb}], best_action, chosen_eval, ev_loss_bb, correctness(optimal|acceptable|
mistake|blunder)|None, rationale_tags, explanation, provider=HEURISTIC, leak_category,
coverage(full|partial|not_found), solver_node_key, is_mixed, authored_rationale, tiers}`.
Never boolean.

Correctness bands (code constants): `POST_ACCEPTABLE_MAX=0.6, POST_MISTAKE_MAX=1.8,
POST_MIX=0.20` (`postflop.py:78-80`); ladder at `:396-405` (identical ×3).

**Content packs today:** `content/postflop/cbet.json` only — entries
`{node_context, position, facing, actions: [], rationale}`; **packs carry ONLY rationale
prose**, keyed `(node_context, position, facing)` via `_postflop_rationale_index()`
(`postflop.py:38-54`). All numeric strategy lives in code (`_CBET_FOLD_PCT_*` `:213-216`,
`_CAT_VALUE` `:205`, `_HAND_VALUE` `:446`, bands).
⚠️ "Thresholds in content packs" = NEW capability: `Entry` model (`content/models.py:44-52`)
has no threshold fields; `contentpack.schema.json` `$defs/NodeContext` enumerates exactly the
10 current values — new enum members require schema regen, and `Entry.node_context: NodeContext`
means pack loading crashes on unknown strings until the enum grows.

**Tiered feedback composer:** `feedback.py::compose_tiers(spot, result, decision) ->
FeedbackTiers{verdict, reasoning, deep_dive}`, wrapped once via `TieredFeedbackProvider`
(`factory.py:32-37`). Purely post-hoc — turn grader gets tiers free IF it emits the 4-wide
tag shape. Dispatch `if tags[0] in _NODE and len(tags) >= 4` (`feedback.py:127`); `_NODE` keys
`cbet/vs_cbet/vs_check_raise` (`:50-54`). ⚠️ **Unknown turn tag names fall through to the
PREFLOP else-branch (`:137-151`) → chart-language nonsense** — `_NODE`/`_ADV` must gain turn
entries. NOT_FOUND short-circuits all tiers (`:92-93,:107-108,:156-157`).

## 3. `NodeContext` — every switch site

Definition `spot.py:63-79` — 10 members (StrEnum; values persist in SRS rows + hashes).
Switch sites (exhaustive):
- `drill.py:89` `_POSTFLOP_CTX = (CBET, VS_CBET, VS_CHECK_RAISE)` — gates `_next_review` (`:157`).
- `drill.py:92-148` `_rebuild_postflop` if/elif on `row.node_context`; unknown → None →
  **due row silently skipped** (`:158-160`).
- `providers/postflop.py:15` `_POSTFLOP_NODES` in `supports()`; `_grade` if/elif (`:29-34`).
- `grading.py:70-93` `leak_category_for()`; **unknown ctx falls to `VS_RFI` (112) — turn ctx
  without branch mislabels leaks as preflop**.
- `drill.py:176-182` `_FAMILY_CTX` + literal mode strings in `next_drill` (`:216-221`).
- Content: `Entry.node_context: NodeContext` + JSON-schema enum.
- Signature: `ctx = ",".join(sorted(...))` tuple index 3 (`srs.py:120,127`) — new values hash
  to new items automatically, no collision.
- **FE `types.ts:30` `node_context: string[]` — NOT a union; no FE change for new contexts.**
  But drill `Mode` union (types.ts ~:115-125), backend `DrillMode` Literal
  (`content/models.py:22-31`), `hashRoute.ts::MODE_IDS`, `Home.tsx PATH_NODES` (`:31-39`) all
  enumerate modes — only touched if S6 adds turn drill MODES (roadmap no-go: it doesn't).

## 4. CompositeProvider — plugging a TURN provider

Constructor `__init__(self, preflop, postflop)` (`composite.py:38`); `_by_street` `:44-49`
with comment "S6/S7 swap the TURN/RIVER entries here." Duck-typed async
`supports/optimal/evaluate`. `_not_found`: Coverage.NOT_FOUND, "No content for this spot.",
freq 0.0 / ev 0.0, leak None.

`PostflopHeuristicProvider.supports()` gates on street==FLOP **and** node∈`_POSTFLOP_NODES`
**and** `len(board) >= 3` (`providers/postflop.py:21-26`).

Plugging in: widen `__init__` (new param) + swap `Street.TURN` entry; new provider `supports()`
gates street==TURN + turn contexts + `len(board) >= 4`. Wire in `factory.py:32-37`.
⚠️ NOT_FOUND trio (`test_provider.py:146-186`) pins turn spot w/ CBET ctx and ctx-less turn
spot both NOT_FOUND — turn provider must NOT accept flop-node contexts, else
`test_postflop_provider_rejects_turn_street` needs deliberate rewrite.
`test_feedback_tiers.py:159-167` uses ctx-less TURN spot — safe.

## 5. `grade_drill` coverage gap (assigned fix)

Flow at HEAD (`drill.py:233-257`): evaluate → `sig = req.spot.srs_signature or
spot_signature(req.spot)` (`:242`) → **unconditional** `session.add(DrillAttempt)` + commit
(`:244-255`) → **unconditional** `record_attempt(...)` (`:256`) → return. Confirmed live:
client-POSTed turn/river spot gets NOT_FOUND yet persists DrillAttempt (leak None) + SRSItemRow
with flop-truncated `texture_class` (`srs.py:122`, `review.py:30`); row enters due queue.

Response is `EvaluationResult` — **no SRS fields in response; gating writes changes zero
response bytes.** Gate skips both writes on `result.coverage == Coverage.NOT_FOUND`.
**No test pins NOT_FOUND-persists behavior** — gate breaks nothing; add tripwire test for
skipped-persist. Tests depending on FULL-grade persists: `test_api.py:71,114,207,146,174,247`;
`test_review.py:19-119`.

## 6. `_rebuild_postflop` + `_next_review` — TURN branch needs

SRS row fields (`db/models.py:40-65`): signature(PK), node_context, position, facing,
limper_count, villain_type, leak_category, **street (column exists, migration 0004)**,
texture_class, spr_bucket, faced_bet_bucket, ease/interval/reps/due_date/last_grade.
Turn row records `street="turn"` but `texture_class` = flop-3-card classify.

Existing branch pattern (`drill.py:92-148`): dispatch on node_context string → closure over
builders (`build_cbet_spot`/`build_vs_cbet_spot`/`build_check_raise_spot`, signatures
`scenarios.py:363,429,509`) → 150 rejection-sampled candidates matched vs
`target = (texture_class, spr_bucket, faced_bet_bucket)` with 3-tier fallback →
`chosen.srs_signature = row.signature`.

TURN branch needs: (a) turn builders in `scenarios.py` — street=TURN, board len 4,
action_history covering preflop+flop+turn bet (needed by `faced_bet_bucket` street filter,
`srs.py:96-102`), correct pot/spr, CALL min_bb; (b) branch keyed on turn context strings;
(c) `_key` compares flop texture (must — row stores flop-truncated). `_POSTFLOP_CTX` must
grow turn members or turn rows never route to rebuild.

**Alembic: NO migration needed** unless new columns (street/node_context/leak_category
columns already hold strings/ints).

## 7. Leak buckets

`leaks.py`: TAXONOMY_VERSION=3; postflop 200-299 has FLOP_CBET=200, VS_CBET=201,
VS_CHECK_RAISE=202, BOARD_TEXTURE=210, EQUITY_EST=211; exploit thru 305. Never renumber;
**bump TAXONOMY_VERSION → 4**. Turn slots naturally 203/204.

⚠️ Grader→leak mapping duplicated: (1) hardcoded per grader (`postflop.py:361,561,742`);
(2) `grading.py::leak_category_for()` (`:87-92`) used by `_entry_category` (`drill.py:63-66`)
for leak_focus pools. **Add BOTH** or leak_focus can't target new buckets.

FE consumption: leak ints hardcoded `Home.tsx:31-39` (`PATH_NODES[].leakCategories`);
`/stats/leaks` names via `LeakCategory(cat).name`, unknown ints degrade to number string;
concept cards `content/cards/postflop.json` keyed on leak ints, no match → `card: null`
(graceful). New turn IDs → optional Home tile + concept cards (S6 scope decision).

## 8. Spot model — validation reality

Fields `spot.py:130-154`. Validation cards-only — **NO cross-field board-length-vs-street
constraint**; `street=TURN, board=[3]` is valid Pydantic. Board length enforced only by
provider `supports()`. Turn spot production today: **ZERO** builders/samplers emit
Street.TURN; only test-side `model_copy` overrides exist.

## 9. Pinned hashes (tripwire contract)

`test_signature.py:202-207`: flop cbet `"6832a54693ba5f6c"`, preflop RFI `"0cdf437e044b0bc5"`.
Comment `:192-199`: do NOT update literal without explicit migration decision. Append rule
(`srs.py:113-117`): new dims append AFTER `faced_bet_bucket`, constant for existing flop spots.
Street already at tuple index 2 — turn/flop hash differently. **S6 needn't touch the tuple**
unless adding turn-card texture to the SRS key (then append-with-flop-constant, e.g. `"-"`).

## Cross-cutting hazards

- **Turn-texture blindness in SRS key:** `_postflop_signature` classifies `board[:3]`
  (`srs.py:122`) — turn card (flush/straight-completing) invisible to the key; two
  strategically different turns collapse to one SRS item unless a turn dim is appended.
  Same for `SRSItemRow.texture_class` (`review.py:30`).
- Domain purity: graders/builders in domain; coverage gate lives in `api/v1/drill.py` (correct layer).
- Thresholds-in-content tension: postflop invariant only partially true today (packs = prose,
  numbers = code). Moving turn thresholds to packs = `Entry`/`ContentPack` extension +
  schema regen.
- One provider seam: turn provider slots into `_by_street[Street.TURN]`; nothing upstream changes.
- Executable-spec tests: `test_provider.py:146-186` (NOT_FOUND trio),
  `test_signature.py:202-235`, `test_api.py:114/207`, `test_feedback_tiers.py`, `test_review.py`.

## Integration points

`factory.py:32-37` · `composite.py:44-49` · `providers/postflop.py:15,21-26` ·
`postflop.py:103-133` + 3 merit maps + `feedback.py:50-74` · `grading.py:70-93` + grader-local
`leak =` lines · `drill.py:89,92-148,151-171,233-257` · `srs.py:107-135` · `review.py:25-31` ·
`content/postflop/*.json` + `contentpack.schema.json` + `content/models.py:44-52` ·
`Home.tsx:31-39` + `content/cards/postflop.json`.
