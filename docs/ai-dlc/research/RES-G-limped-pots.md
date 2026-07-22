# RES-G — Limped pots: engine reality, hero baselines, grading feasibility

**Spike, Epic 5 (multiway coverage). Output = decision doc + copy-ready content. NO app code.**
Created 2026-07-22. Becomes LAW: build slices copy the §3 JSON and §6 slices verbatim;
adversarial refuters verify implementations against this doc.

Tags on every quantitative claim:
- **[SOLVED]** — provable arithmetic / engine-measured fact (a sim number or a code-read).
- **[SOURCED]** — cited to live-poker literature (Upswing / GTO Wizard / 888 / PokerNews).
- **[DERIVED-ASSUMPTION]** — we computed/chose it (α-anchored + exploit-direction + house style).
  Use as a **design target, not a truth**; refuters may not flag it as "wrong."

Repo law that binds every recommendation here: multiway adjustments are **DIRECTION-only**
(never per-opponent MDF or n-th-root constants); EVs labeled **approximate**; **no solver tables**;
strategy lives in versioned `content/` data (not code); results are **frequency+EV, never boolean**;
`spot_signature()` is **frozen** (it hashes `limper_count` already — `srs.py:62` — so limped-pot
work must not add a new signature dim); every schema change ships an Alembic migration.

---

## 0. Headline (read this first)

Limped pots are **already partly built** and nobody noticed. The engine has a first-class `limp`
action (`personas.py:25`, `"limp" → CALL` on the wire), five of six personas limp, a `vs_limpers`
content pack exists (`content/preflop/vs_limpers.json`, 3 entries: CO×1, BTN×1, BTN×2), and a
working grader (`grade_map_preflop.py::_map_vs_limpers`) maps the **iso-raise / over-limp / fold**
decision to it. So the gap is **not** "zero limped-pot material" — it is:

1. **Hero preflop coverage is thin** — only CO/BTN face limpers in content; UTG–HJ, SB, and BB have
   NO `vs_limpers` entry, and the sim generates those decisions constantly (§1). Over-limp behind is
   folded into the same entries (the `call` action), and there is **no BB-check node** and **no
   hero-open-limp node** at all.
2. **Limped-pot POSTFLOP is a hard "no baseline yet"** — every postflop grader requires hero to be
   the single preflop raiser (`grade_map_postflop.py:64–65`); a pot with zero preflop raises can
   never map. This is ~42% of flops (§1) graded nowhere postflop.

---

## §1 Engine reality (MEASURED)

**Harness** [SOLVED]: seeded headless sim, default `LINEUP` (2 passive_fish, 2 tag, 1 calling_station,
1 nit, 1 lag, 1 maniac across the 8 non-hero seats — `play.py:35`), 100bb stacks, button rotates,
hero seat 0. Scripted hero with a limp-friendly policy (15% raise / 75% call / else check-or-fold)
so limped-pot roles are exercised. Instrumented at the moment the flop is first dealt: a **limped
pot** = ≥2 players saw the flop AND preflop had **zero RAISE** actions. Aggregated over
**3 seeds × 3000 hands = 9000 hands** (`scratchpad/measure_limped.py`, deleted after run).

### 1a. Frequency [SOLVED]

| Metric | seed 20260722 | seed 424242 | seed 77777 | **Aggregate** |
|---|---|---|---|---|
| Hands | 3000 | 3000 | 3000 | 9000 |
| Flops reached (≥2 live) | 1983 | 1953 | 1952 | 5888 |
| **Limped flops (0 raises)** | 802 | 813 | 849 | **2464** |
| Raised flops | 1181 | 1140 | 1103 | 3424 |
| Limped % **of flops seen** | 40.4% | 41.6% | 43.5% | **41.8%** |
| Limped % **of all hands** | 26.7% | 27.1% | 28.3% | **27.4%** |
| **Limped flops per 1000 hands** | 267 | 271 | 283 | **274 / 1000** |

**≈42% of all flops in the default lineup are limped pots** [SOLVED] — corroborating N5's census
"~45% of multiway volume." The share is stable across seeds (40–44%). Per 1000 hands dealt, ~274
reach a limped flop.

### 1b. Field sizes at the flop [SOLVED]

| Field (players seeing flop) | Count | Share of limped flops |
|---|---|---|
| 2-way (HU) | 760 | 30.8% |
| **3-way** | 1164 | **47.2%** |
| 4-way | 475 | 19.3% |
| 5-way | 62 | 2.5% |
| 6-way | 3 | 0.1% |
| **Multiway (3+)** | 1704 | **69.2%** |

**Limped pots are predominantly multiway** [SOLVED]: 69% go 3+ ways, the modal field is **3-way**
(47%), and 4-way is common (19%). HU limped pots (a limp folded around to the BB, or SB-complete-vs-BB)
are the minority (31%). Note the HU share is partly inflated by the hero's own limp/call policy;
bot-only limped fields skew even more multiway.

### 1c. Who limps [SOLVED]

Bot-only limp mix (CALL actions in 0-raise pots, hero excluded, 2746 bot limps):

| Persona | Bot limps | Share of bot limps | Limps in pack? |
|---|---|---|---|
| **passive_fish** | 1335 | **48.6%** | yes (wide) |
| **calling_station** | 1142 | **41.6%** | yes (very wide) |
| maniac | 229 | 8.3% | yes (over-limp leg only) |
| nit | 20 | 0.7% | yes (small pairs, 30–40% freq) |
| lag | 20 | 0.7% | yes (rare over-limp leg) |
| **tag** | 0 | 0.0% | **NO limp mix** — always raise-or-fold |

**~90% of all limps come from passive_fish + calling_station** [SOLVED]. This is the profile you
want a $2/$3 student to punish: two recreational stations donate almost all the dead money. Tag
never limps (correct — a competent reg raise-or-folds); nit/lag limp only trivially. Maniac's limps
are the over-limp-behind leg of its `vs_limpers` node, not open-limps.

Limper seat distribution is roughly uniform across non-blind seats (UTG through BTN each ~12–13% of
limps), i.e. these personas open-limp from **any** position, not just late — a live-realistic (if
strategically loose) behavior.

### 1d. Hero decision-point roles in limped pots [SOLVED]

The most frequent hero decisions inside limped pots (across seeds), ranked:

- `hero faces 1 limper @ {CO, BTN, HJ, LJ, SB, UTG2, ...}` — the dominant shape.
- `hero faces 2 limpers @ {SB, BTN, CO, BB, HJ, LJ}` — common.
- `hero faces 3+ limpers @ {BB, CO, SB, BTN}` — the long tail.

**Content covers only CO×1, BTN×1, BTN×2** [SOLVED]. Every `@HJ`, `@LJ`, `@UTG2`, `@SB`, and `@BB`
row — and every `faces-3+` row — is a live, high-frequency hero decision that currently returns
`None` ("no baseline yet"). The **BB-facing-limpers** rows are special: the BB can **check** (free
flop) as well as iso/fold — a decision shape no other node has (§2, §3d).

---

## §2 Who-limps personas — levers for the 6 personas

The persona limp behavior is **already authored** and matches live reality; this section documents
what exists and the one direction-only tuning worth flagging. Limp behavior lives in each pack's
`preflop[]` list as a `"limp"` mix (translated to `CALL` on the wire, `personas.py:25`), under the
`facing: "unopened"` node (open-limp) and the `facing: "vs_limpers"` node (over-limp behind).

| Persona | Open-limps? | Over-limps behind? | Direction (current authored behavior) | Confidence |
|---|---|---|---|---|
| **passive_fish** | **Yes — wide** | Yes — wide | Limps a huge speculative range (pairs, most suited, many offsuit Broadways); raises only premiums. **The canonical live open-limper.** | [SOLVED] authored + [SOURCED] "recreational players open-limp" |
| **calling_station** | **Yes — very wide** | Yes — near-any-two | Limps ~any pair/suited/connected + wide offsuit; raises only AA/KK/AKs at 60%. **The widest limper**; the exploit target. | [SOLVED] authored |
| **maniac** | Rare (raise-heavy) | Yes — polar over-limp leg | Prefers to raise; over-limps a trap/speculative leg behind limpers. | [SOLVED] authored |
| **nit** | Small pairs only, 30–40% | Small pairs only, ~30% | Limps 22–77 at low freq (set-mining), else raise-or-fold. Live-realistic "limp small pairs" nit tell. | [SOLVED] authored |
| **lag** | Rare | Rare over-limp leg | Mostly raise-or-fold; occasional over-limp trap. | [SOLVED] authored |
| **tag** | **No** | **No** | Pure raise-or-fold — the "correct" reg baseline, deliberately non-exploitable here. | [SOLVED] authored |

**Persona-lever recommendation** [DERIVED-ASSUMPTION]: **leave the persona limp levers as-is.** They
already reproduce the live pattern (recreationals donate, regs don't) and the §1 sim confirms the
mix produces the right volume and target profile. There is **no persona-lever bug** to fix in this
epic — the gap is entirely hero coverage. If a future slice wants more limp volume it can widen
`calling_station`/`passive_fish` `unopened` limp mixes, but that is optional tuning, not law.

**One honest caveat** [SOURCED]: live literature (Upswing "Why Limping Is Usually Bad") treats
open-limping as a leak, so a student should learn to *punish* limps, not imitate them — which is
exactly what §3 hero baselines teach (iso-raise the dead money, over-limp only speculative hands).

---

## §3 Hero preflop baselines (copy-ready `content/preflop/vs_limpers.json` entries)

**Schema** (`content/schema/contentpack.schema.json`, `Entry`): each entry is
`{node_context, position, limper_count?, actions[], sizing_bb?, rationale?}`; each action is
`{action, combos, frequency}`. `_map_vs_limpers` keys on **(hero position, limper_count)** and
`build_spot` seats the limpers canonically at `_LIMP_SEATS[:count]` — so WHICH seats limped is
canonicalized away (only the count matters). The grader offers **raise / call / fold**; the
`call` action IS the over-limp-behind option (no separate node needed).

**Iso-raise sizing law** [SOURCED, Upswing *vs Multiple Limpers*]: **4bb + 1bb per limper**, live.
So 1 limper → 5bb, 2 limpers → 6bb, 3 limpers → 7bb. The existing 3 entries already use this
(CO×1 = 5.0, BTN×1 = 5.0, BTN×2 = 6.0). **Sizing note** [SOLVED]: `sizing_bb` is a single number;
the preflop grader only produces a size verdict when an entry offers **≥2 raise evals**
(`grading.py:242`), so iso-*sizing* is **action-only graded today** — the raise size is displayed
(as the suggested size) but not graded good/bad. That is acceptable for v1 (the action choice
iso-vs-limp-vs-fold is the teaching point); a two-size iso grade is a possible later extension, out
of scope here.

**Range-direction law** [SOURCED, Upswing; PokerNews *Destroy Limpers*]: iso-raise a **value-skewed
range that dominates a weak limping range**; **tighten as limper_count rises** (fold equity drops
vs multiple limpers); **widen from later position** (position lets you realize equity). Speculative
hands (small pairs, suited connectors, suited gappers) **over-limp instead** — cheap multiway flops
where set/straight/flush **implied odds** beat thin isolation. Live iso is **wider and more
value-heavy** than an RFI range (you are attacking dead money and a capped, weak caller).

### 3a. Fill the missing seats, 1 limper (copy-ready)

The pattern: EP seats iso tightest (many players still behind), late seats iso widest. Ranges below
are **[DERIVED-ASSUMPTION]** — anchored to the existing CO/BTN entries (value-skew + implied-odds
over-limp), positionally interpolated off the RFI ladder in `content/preflop/rfi.json`, and
consistent with the Upswing/PokerNews direction. Treat as design targets.

> **M2 correction** (post-implementation refuter finding): §1d measures the EP faces-1-limper shape
> as **UTG2**, not UTG — UTG acts first preflop and has no seats before it, so a UTG×1 entry breaks
> `scenarios.build_spot`'s VS_LIMPERS branch (`_before(UTG) == []`, the limper-seating loop never
> runs, producing an incoherent Spot). The entry below is authored as EP-tight per this section's
> intent; **M2 corrected its `position` to `UTG2`** so it is both organically reachable via
> `map_preflop` and coherent in `build_spot` (Practice mode). The range itself is unchanged.

```json
{
  "node_context": "vs_limpers", "position": "UTG", "limper_count": 1,
  "actions": [
    { "action": "raise", "combos": "99+, AJs+, KQs, AQo+", "frequency": 1.0 },
    { "action": "call",  "combos": "22-88, ATs, KJs, QJs, JTs, T9s, 98s", "frequency": 1.0 }
  ],
  "sizing_bb": 5.0,
  "rationale": "First to act with the whole table behind, isolate only hands that dominate a weak limper AND fare well if a player behind wakes up (99+, AJs+, AQo+); the medium pairs and suited Broadways/connectors over-limp to see a cheap multiway flop where implied odds beat thin isolation from out of position (Upswing vs-limpers; doc 01 §9)."
},
{
  "node_context": "vs_limpers", "position": "LJ", "limper_count": 1,
  "actions": [
    { "action": "raise", "combos": "88+, ATs+, KJs+, QJs, AJo+, KQo", "frequency": 1.0 },
    { "action": "call",  "combos": "22-77, A5s, KTs, QTs, JTs, T9s, 98s, 87s", "frequency": 1.0 }
  ],
  "sizing_bb": 5.0,
  "rationale": "One off EP: widen the iso slightly (88+, suited Broadways, AJo/KQo) as fewer players remain behind, while small pairs and suited connectors over-limp for set/straight equity in a likely multiway pot (Upswing vs-limpers; doc 01 §9)."
},
{
  "node_context": "vs_limpers", "position": "HJ", "limper_count": 1,
  "actions": [
    { "action": "raise", "combos": "77+, A9s+, KTs+, QTs+, JTs, ATo+, KJo+, A5s", "frequency": 1.0 },
    { "action": "call",  "combos": "22-66, 54s, 65s, 76s, 87s, 98s, K9s, Q9s", "frequency": 1.0 }
  ],
  "sizing_bb": 5.0,
  "rationale": "Mirror the CO iso one seat earlier and marginally tighter: value-skewed isolation (77+, suited aces/Broadways, ATo+/KJo+) to play a heads-up pot in position against a capped limper, with the small pairs and suited connectors over-limping for cheap multiway equity (Upswing vs-limpers; doc 01 §9)."
},
{
  "node_context": "vs_limpers", "position": "SB", "limper_count": 1,
  "actions": [
    { "action": "raise", "combos": "66+, A9s+, KTs+, QTs+, JTs, ATo+, KJo+, A5s", "frequency": 1.0 },
    { "action": "call",  "combos": "22-55, 54s, 65s, 76s, 87s, 98s, K9s, Q9s, J9s", "frequency": 1.0 }
  ],
  "sizing_bb": 5.0,
  "rationale": "From the small blind you close only to the big blind but play every street out of position, so isolate a value-heavy range that wants a heads-up pot (66+, suited aces/Broadways, ATo+); complete (over-limp) with speculative hands rather than fold, since the discounted 0.5bb price prices in set/straight draws even out of position (Upswing vs-limpers; doc 01 §9)."
}
```

> **`CO`×1 and `BTN`×1 already exist** in `vs_limpers.json` (do not duplicate). UTG1/UTG2 may reuse
> the UTG entry or interpolate one notch wider — a slice may collapse UTG/UTG1/UTG2 to a single EP
> entry if authoring volume is a concern (position is the only differentiator and EP seats play
> near-identically vs a single limper).

### 3b. 2-limper entries for the missing seats (copy-ready, tighter + 6bb)

```json
{
  "node_context": "vs_limpers", "position": "CO", "limper_count": 2,
  "actions": [
    { "action": "raise", "combos": "88+, ATs+, KTs+, QJs, AJo+", "frequency": 1.0 },
    { "action": "call",  "combos": "22-77, 54s, 65s, 76s, 87s, 98s", "frequency": 1.0 }
  ],
  "sizing_bb": 6.0,
  "rationale": "Two limpers means the pot likely stays multiway even after a raise, so tighten to hands that hold up against several callers (88+, suited aces/Broadways) and size to 4bb+2 (6bb); speculative pairs and connectors over-limp, since 3-way-plus pots reward set-mining and drawing over thin isolation (Upswing vs-limpers; doc 01 §9, §11)."
},
{
  "node_context": "vs_limpers", "position": "SB", "limper_count": 2,
  "actions": [
    { "action": "raise", "combos": "88+, ATs+, KTs+, QJs, AJo+", "frequency": 1.0 },
    { "action": "call",  "combos": "22-77, 54s, 65s, 76s, 87s, 98s, A2s, A3s, A4s, A5s", "frequency": 1.0 }
  ],
  "sizing_bb": 6.0,
  "rationale": "Out of position against two limpers, isolate only a tight value core (88+, suited Broadways, AJo+) and complete the rest, leaning on the cheap SB price to set-mine and draw in a guaranteed-multiway pot rather than bloating it out of position with marginal iso hands (Upswing vs-limpers; doc 01 §9, §11)."
}
```

> **`BTN`×2 already exists** (77+, ATs+, KTs+, QJs, AJo+, A5s @ 6.0). HJ/LJ/UTG×2 may reuse the CO×2
> entry (they play near-identically vs 2 limpers) or a slice may cap 2-limper coverage at CO/BTN/SB
> if the tail volume (§1d) does not justify authoring — the sim shows `faces-2 @ HJ/LJ` is real but
> lower frequency than `@ CO/BTN/SB`.

### 3c. Over-limp is the `call` leg (no new node) [SOLVED]

The engine already routes a hero `CALL` in a 0-raise pot to `_map_vs_limpers` and grades it against
the entry's `call` action band. So **"over-limp range by position"** IS the `call` combos above — no
separate `over_limp` node_context is needed or should be added. A hero who over-limps a hand in the
`call` band grades OPTIMAL; over-limping a hand that should iso grades a size/action mismatch;
over-limping trash (outside both bands) grades a fold-equity leak. This is the cleanest possible
outcome and needs zero new grader machinery.

### 3d. BB-check option — NEEDS A NEW NODE (design, not copy-ready)

The BB facing only limpers can **check** (free flop) as well as iso-raise or fold — a decision shape
**no existing node models** (`_map_vs_limpers` builds a spot with FOLD/CALL/RAISE legal actions and
has no BB entry; the BB's "call" is a zero-cost check of its option). Two problems block a copy-ready
BB entry today:

1. `_LIMP_SEATS` is non-blind only and the SB-complete case explicitly returns `None`
   (`grade_map_preflop.py:235–236`) — the current builder cannot seat the hero as BB behind limpers.
2. The BB's check is **free** (already posted 1bb), so the "call" leg has `to_call = 0` — the grader
   would need to treat CHECK as the passive baseline, not CALL.

**Design** [DERIVED-ASSUMPTION]: a BB `vs_limpers` entry with actions `{raise (iso), check}` (no
fold — checking is free and strictly dominates folding), sizing 4bb+1/limper, iso range **wider than
other seats** (you are last to act, close the action, and get a free flop otherwise). Direction:
iso a value+equity range that wants to punish the limpers and thin the field; **check everything
else** (never fold the BB for free). This requires a small `scenarios.build_spot` extension (BB
limped node with a CHECK legal action) — see §5 and §6-Slice-C. **Live source** [SOURCED, GTO Wizard
*Disciplining BB in Limped Pots*]: the BB "arrives at the flop with a weaker range and so should
mostly check" — so the BB's default is check, iso only the top.

---

## §4 Limped-pot postflop directions

### 4a. What actually happens in code today [SOLVED]

**Every postflop grader returns `None` for a limped pot.** Confirmed by code-read:

- `grade_map_postflop.py::map_flop_cbet` line 64–65: `if len(raises) != 1 or raises[0].position is
  not hero.position: return None` — hero **must be the single preflop raiser**. A 0-raise pot fails
  immediately.
- The HU-SRP path (`_hu_srp_preflop`) requires an opener + a BB caller (line 183–184) — also a raise.
- `map_flop_cbet` also gates `len(live) != 2` (line 50–51) — **HU only**, so even a *raised* multiway
  flop is unmapped; a limped multiway flop is doubly out of scope.

So limped-pot postflop is **"no baseline yet" everywhere**, and `sample_postflop_decision` (the BOT
engine) still produces actions in these pots — bots bet/check/call fine, they are just **ungraded**
for the hero. There is no hidden partial support to reconcile.

**`personas_postflop.py::sample_postflop_decision` behavior when nobody was the preflop aggressor**
[SOLVED]: `is_aggressor = last_aggressor_position(...) == seat.position` (`play.py:191`). In a limped
pot there was no preflop raise, so on the flop the first bettor's `is_aggressor` is computed from the
**postflop** action history's last aggressor — i.e. no seat carries a preflop-aggressor flag into the
flop. The bot's sizing-by-node path (`personas_postflop.py:366` `if pf.sizing_by_node and
is_aggressor`) simply does not fire for a checking-first limped flop; bots fall to the generic
merit/bluff logic. Nothing crashes, but there is **no "limped-pot" awareness** in the bot — it treats
a limped flop like any other no-aggressor spot. Grading-wise, `range_advantage_defender`
(`postflop.py:752`) already encodes "the defender gets NO preflop-aggressor baseline" (`score = 0.0`
comment line 763) — which is the exact right *direction* for a limped pot (nobody has the PFR range
edge), but it is only reachable through the raised-pot vs-cbet path, never a limped pot.

### 4b. Strategic directions (what a limped-pot postflop grader should encode) [SOURCED + DERIVED]

If/when a slice builds limped-pot postflop grading, the directions are (all **direction-only**, per
repo law — no MDF, no n-th-root):

1. **No preflop aggressor → no range-advantage baseline** [SOURCED, GTO Wizard]. Neither player has
   the PFR's condensed strong range. Start from `score = 0` (exactly what
   `range_advantage_defender` already does) and let **board texture** decide the edge, not preflop
   role. [DERIVED-ASSUMPTION]: reuse the texture terms already in `postflop.py`.
2. **Ranges are capped and weaker on both sides** [SOURCED, Upswing/GTO Wizard]. Limpers rarely have
   the top of the range (they'd have raised), so **big bets and stacks-in lines are over-repped by
   value** — a limped-pot bettor sizing huge is polarized to real strength. Direction: **reward small
   probe/stab bets, penalize large bloating with medium strength**.
3. **In a limped pot the "aggressor" is whoever bets first, and should bet SMALL + polar** [SOURCED,
   GTO Wizard: "bet small, just as a c-bet in an SRP"; polarized value+bluff]. Direction for a hero
   who leads a limped flop: **small size preferred**; value-heavy on boards that smash the limping
   range, thin on dry high boards.
4. **The BB (or the passive limper) should MOSTLY CHECK** [SOURCED, GTO Wizard: "weaker range → mostly
   check," avoid betting vulnerable pairs]. Direction: reward check with medium made hands OOP,
   penalize thin value-bets into an uncapped field.
5. **Multiway dampening applies harder** [SOLVED, existing `_MW_THIN_VALUE_DAMPEN=0.7` from N5]. 69%
   of limped pots are 3+ way (§1b) — thin value and bluffs are worth less; the existing DIRECTION-only
   multiway dampener is the right lever, just currently unreachable in limped pots.

**Confidence** [DERIVED-ASSUMPTION]: these directions are well-sourced qualitatively but the
**heuristic will be coarse** — no solver tables, EVs stay labeled approximate. A limped-pot postflop
grader is honestly a "simplified-but-directionally-right" teacher, and multiway (3+) limped postflop
is the coarsest of all (the app has *no* multiway postflop grader for any node yet).

---

## §5 Grading feasibility map (per hero role)

| Hero role | Frequency (§1) | Verdict | Detail |
|---|---|---|---|
| **Iso-raise vs limpers** (CO/BTN, 1–2 limpers) | High | **GRADABLE NOW** ✅ | `_map_vs_limpers` + 3 existing entries already grade it (raise/call/fold, freq+EV). Working today. |
| **Iso-raise vs limpers** (UTG–HJ, SB; 3+ limpers) | High | **GRADABLE NOW w/ content** ✅ | Same grader, **zero code** — just add the §3a/§3b entries. The grader keys on (position, count); any authored (position,count) maps instantly. This is a pure **content fill**. |
| **Over-limp behind** (the `call` leg) | High | **GRADABLE NOW** ✅ | Already the `call` action band inside each `vs_limpers` entry (§3c). No new node. Covered exactly when the iso entry for that (position,count) exists. |
| **BB-check option** (BB facing limpers) | Medium (§1d: `faces-N @ BB` is common) | **NEEDS-NEW-GRADER** 🔶 | Small: a BB `vs_limpers` entry with a **CHECK** legal action + a `scenarios.build_spot` branch that seats hero=BB behind limpers and offers `{raise, check}` (no fold). `_map_vs_limpers` must stop returning `None` for the BB (lift the SB/blind gate for the BB-check case only). ~1 small slice. Direction per §3d. |
| **Limped-pot POSTFLOP** (flop/turn/river, any field) | ~42% of flops (§1a); 69% multiway | **NEEDS-NEW-GRADER (large) / partly NEVER** 🔴 | No postflop grader accepts a 0-raise pot AND no grader accepts a multiway flop at all. **HU limped postflop** (31% of limped flops) is a buildable new node family (new `map_limped_flop*` mappers + content thresholds, directions per §4b). **Multiway (3+) limped postflop** (69%) needs the app's first multiway postflop grader — a genuinely large, separate effort; until then it stays honest "no baseline yet." Heuristic-only, EVs approximate. |

**Summary**: two of the five roles are **gradable now or with pure content** (iso-raise, over-limp);
one is a **small new grader** (BB-check); one is a **large new family split into a buildable HU half
and a deferred multiway half** (limped postflop). Nothing is *permanently* never — but multiway
limped postflop is the deepest lift in the whole app and should be sequenced last / possibly deferred
to the solver-baseline LATER bet.

---

## §6 Recommended slice cut (with pass/fail per slice)

Ordered by value-per-effort. Each slice is a candidate `/ai-dlc` vertical slice; **Slice A is the
clear first cut** (highest frequency, zero code risk).

### Slice A — Limper iso/over-limp preflop coverage fill (content-only) — DO FIRST
**Scope**: add the missing `vs_limpers` entries from §3a/§3b (UTG/LJ/HJ/SB ×1; CO/SB ×2; optionally
UTG1/UTG2 reuse). No code — the grader (`_map_vs_limpers`) and builder already exist and key on
(position, count). Bump `vs_limpers.json` `version` 1→2.
**Pass/fail**:
- (a) A bot-driven belt test (fixed seed) shows `map_preflop` now grades hero `faces-1 @ {UTG,LJ,HJ,SB}`
  and `faces-2 @ {CO,SB}` limped decisions that returned `None` before (assert each named
  (position,count) maps).
- (b) `test_coverage_baseline.py` graded count goes **UP**, total **unchanged** (harness invariant —
  content-only change cannot move the hand stream).
- (c) Every added entry validates against `contentpack.schema.json`; nesting/order tests green.
- (d) `spot_signature()` byte-unchanged (no code touched); `TAXONOMY_VERSION` unchanged;
  `verify.sh` + FE build green.
**Appetite**: ~1 small slice (content authoring + tests). **No-gos**: no new node_context; no iso
*size* grade (stays action-only); off-pack (position,count) still returns `None`.

### Slice B — BB-check node vs limpers (small new grader)
**Scope**: new BB `vs_limpers` entries with `{raise (iso), check}` actions (no fold); a
`scenarios.build_spot` branch seating hero=BB behind `_LIMP_SEATS[:count]` with a CHECK legal action;
`_map_vs_limpers` lifts the blind-seat `None` gate for the BB-check case only. Direction per §3d.
**Pass/fail**:
- (a) Hero-as-BB facing 1–3 limpers now maps and grades `iso` vs `check` (freq+EV, never boolean);
  checking a range-appropriate hand grades OPTIMAL, iso'ing junk grades a leak.
- (b) A BB with a fold action is **never** offered (checking is free — folding the BB dominated).
- (c) SB-complete-vs-BB and all non-BB limped shapes are **byte-unchanged** (existing `_map_vs_limpers`
  tests stay green; the new path is a strict superset).
- (d) `spot_signature()` unchanged (`limper_count` already hashed); migration only if a new
  `sim_decision` dim is truly needed (prefer none); `verify.sh` + build green; design-review.
**Appetite**: ~1 small–medium slice. **No-gos**: no postflop yet; no fold leg for the BB; don't fabricate
a BB range where none is authored.

### Slice C — HU limped-pot flop grader (new node family)
**Scope**: the FIRST limped-pot postflop grader, **HU only** (31% of limped flops — the tractable
half). New `map_limped_flop_lead` / `map_limped_flop_vs_lead` mappers accepting a 0-raise HU pot,
content thresholds encoding §4b directions (small polar lead; mostly-check OOP; texture decides the
edge from `score=0`). Reuse `range_advantage_defender`'s no-baseline start and the existing
multiway/thin-value dampeners.
**Pass/fail**:
- (a) A bot-driven belt test fires the new mappers on a HU limped flop (hero leads / hero faces a lead);
  a 0-raise HU flop that returned `None` now grades freq+EV.
- (b) Any multiway (3+) limped flop still returns `None` ("no baseline yet") — the grader must
  **never silently HU-grade a multiway pot** (explicit `len(live) != 2 → None`).
- (c) Raised-pot postflop graders are **byte-unchanged** (existing postflop pins hold;
  `TAXONOMY_VERSION` bump only if the grader taxonomy genuinely changes).
- (d) EVs labeled approximate; `spot_signature()` unchanged; `verify.sh` + build green; refuter +
  design-review.
**Appetite**: ~1 large slice. **No-gos**: HU only; no multiway; heuristic-only (no solver); no
limped-pot turn/river in v1 (flop first, extend later like S6/S7 did for raised pots).

### Slice D (DEFER / LATER) — Multiway limped-pot postflop
**Scope**: the app's first **multiway** postflop grader (3+ way limped flops, 69% of limped pots).
**Recommendation**: **defer.** This is the single deepest lift in the app — no multiway postflop
grader exists for *any* node, the heuristic gets very coarse with 3+ uncapped ranges, and it is the
natural trigger to revisit the solver-baseline no-go. Keep it honest "no baseline yet" until
Slices A–C land and real usage justifies it. If built, it is direction-only (multiway dampeners),
EVs strongly approximate, and probably its own epic.

**Sequencing**: **A → B → C → (defer D)**. A is a near-free coverage win on the single
highest-frequency limped decision; B closes the BB-check gap cheaply; C opens postflop for the
tractable HU third; D is a separate future epic.

---

## Appendix — key code references (for refuters)

- Limp is a first-class action, wired to CALL: `backend/app/domain/personas.py:25–33`.
- Default lineup (who's at the table): `backend/app/domain/table/play.py:35–44`.
- Existing iso grader (works today): `backend/app/domain/table/grade_map_preflop.py:210–240`.
- Existing content (CO×1, BTN×1, BTN×2 only): `content/preflop/vs_limpers.json`.
- Preflop dispatch routes 0-raise limped pots here: `grade_map_preflop.py:91–97`.
- `build_spot` seats limpers / sets legal actions: `backend/app/domain/scenarios.py:207–224`.
- Postflop hard block (hero must be sole PFR): `grade_map_postflop.py:64–65`; HU-only gate `:50–51`.
- No-baseline defender direction (right for limped): `backend/app/domain/postflop.py:752–777`.
- `spot_signature()` already hashes `limper_count`: `backend/app/domain/srs.py:62`.
- Iso-size verdict needs ≥2 raise evals (why iso-size is action-only): `grading.py:242`.

## Sources

- [Upswing — How to Maximize Your Winnings Versus Multiple Limpers](https://upswingpoker.com/vs-multiple-limpers/) — 4bb + 1bb/limper iso sizing; tighten vs more limpers.
- [Upswing — 8 Live Poker Tips](https://upswingpoker.com/live-poker-tips-strategy/) · [Upswing — Why Limping Is Usually Bad](https://upswingpoker.com/why-limping-in-poker-is-bad/).
- [GTO Wizard — Disciplining Big Blind in Limped Pots](https://blog.gtowizard.com/disciplining-big-blind-in-limped-pots/) — BB weaker range → mostly check; limper bets small + polar.
- [GTO Wizard — The Curious Case of Open-Limping Buttons](https://blog.gtowizard.com/curious-case-of-open-limping-buttons/).
- [PokerNews — 10 Tips That Will Help You Destroy Limpers](https://www.pokernews.com/strategy/10-tips-that-will-help-you-destroy-limpers-32206.htm).
- [888 — Iso-Raising in Poker](https://www.888poker.com/magazine/strategy/iso-raising-poker-all-you-need-know).
- Internal: `docs/research/01-preflop-strategy.md` §9 (iso/over-limp), §11 (multiway); RES-D §1 (multiway direction-only law); N5 done-note (`docs/ai-dlc/roadmap/simulate-table.md`).
