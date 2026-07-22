# Adversarial Review — Poker-Coach Heuristic Bot Engine

**Reviewer role:** refuter (maker ≠ checker). Goal: break the reasoning, not bless it.
**Scope:** the 18 numbered claims/assumptions in `poker-math-brief.md`, verified against the
actual code, judged against credible poker theory with real numbers.

## 0. Brief-vs-code verification (did the brief lie?)

I read the code before trusting the brief. The brief is **accurate**. Specifically confirmed:

- `personas_postflop.py` merit tables (`_AGG_BASE`, `_CHECK_BASE`, `_FOLD_BASE`, `_CALL_BASE`,
  `_RAISE_BASE`, draw bonuses, `_BLUFF_RAISE_FACTOR=0.3`, `_COMMIT_AGG_BOOST=3.0`) match the
  brief verbatim (lines 180–235).
- `bluff_mass = pf.bluff_freq * noise * pf.multiway_bluff_damp ** max(opponents-1, 0)`
  (line 284) — matches brief §2.3 exactly. Bluff mass is a flat per-persona constant, decayed
  only by opponent count, **never by bet size or price**. Confirmed.
- SPR commit at line 313: `stack_bb / pot_bb <= pf.spr_commit and (bucket ≥ OVERPAIR_TPTK or
  draw STRONG)` → zero fold mass, ×3 bet/raise. Matches brief §2.4 step 4.
- Sizing is drawn independent of bucket (lines 339–347); `postflop_node_key` reads only
  board+legal, never hole cards (`sizing.py:66–93`). Anti-sizing-tell confirmed.
- `rng.choices` always — mixed, never argmax (line 332). Confirmed.
- Lever table in brief §3 matches the six JSON packs **exactly** (I diffed nit/passive_fish/
  calling_station/tag/lag/maniac). One note: the brief §3 table lists maniac `stickiness 0.55`;
  the JSON confirms `0.55` (brief header text elsewhere says stickiness generally — no error).
- Maniac worked examples in brief §3 reproduce from the code: top-pair-bet
  `0.55×15 / (0.55×15 + 0.45) = 0.948`; top-pair-raise-facing-bet
  `1.5 / (1.5 + 0.43 + 0.12) = 0.73`. Both correct.
- The test-file disclaimer (`test_personas_postflop.py:554–561`) is quoted accurately, and I
  found an *additional* candid admission at lines 520–552: WTSD misses PRD bands for 5/6
  personas and the team re-anchored those bands to engine output rather than theory. The brief
  under-sells how much the team already knows is off.

**No misrepresentation found.** The brief is an honest description of the engine.

---

## Theory reference numbers (pinned, cited)

- **MDF = pot / (pot + bet)**; Alpha = 1 − MDF. By size: 1/3 pot → MDF 75% / α 25%;
  1/2 pot → 67% / 33%; 2/3 pot → 60% / 40%; pot → 50% / 50%; 1.25× pot → ~44.5% / 55.5%.
  [GTO Wizard MDF & Alpha]
- **GTO bluff-to-value by size** (river, polar): 1/3 pot → 20% bluffs (1:4); 1/2 pot → 25%
  (1:3); pot → 33% (1:2); overbet → 38–40%. Bluff frequency **rises with bet size**.
  [SplitSuit, DeucesCracked, PokerStrategy]
- **Archetype population stats**: nit VPIP <15 / PFR <12, AF low; TAG VPIP 16–22 / PFR 13–20,
  AGG% 32–40; LAG (6-max) VPIP 24–30 / PFR 20–26; calling station VPIP >35 low PFR, very low
  AF; maniac VPIP >50, raises/re-raises constantly. [PokerVIP, pokerology, pokercoaching]
- **Multiway**: bluff/c-bet frequency drops ~50% from HU to 3-way (HU c-bet ~70% → ~35%
  three-way). [pokergtosolver, poker-alpha, GTO Wizard 3-way heuristics]
- **SPR commitment**: Miller/Flynn/Mehta *Professional NLHE* (2007) formalized SPR; modern
  reading is low SPR **lowers equity thresholds** (price-driven), it does NOT create an
  automatic "committed, never fold" state. [Red Chip, PokerTube, thepokerbank]
- **Limping**: GTO limps exist but are narrow — SB complete ~4.2% vs a correctly-raising BB;
  BTN open-limp is a **short-stack (≤~14bb) tournament** phenomenon, essentially absent at
  100bb cash. [GTO Wizard: open-limping buttons; PokerNews SB limp-reraise]

---

## Per-claim verdicts

### Claim 1 — Position+facing lookup, first-match-wins mixes as preflop abstraction
**Verdict: SOUND (as an abstraction).** Range-chart lookup keyed on (position, facing node) is
exactly how every commercial preflop trainer and solver output is consumed — GTO preflop
solutions *are* position×node range charts with weighted actions. First-match-wins with a
fold-default is a clean way to encode a weighted range. The only theoretical loss is that it
can't express the same hand taking different actions vs *different raiser positions/sizes*
within one node, but for a beginner trainer that's immaterial.
*Cite:* GTO preflop charts are position×action tables (bbzpoker "How to Read Range Charts";
888poker GTO open-raising). Divergence justified by beginner goal.

### Claim 2 — Static mixes, no board/stack/ICM/opponent-modeling, fixed 100bb
**Verdict: DEFENSIBLE-SIMPLIFICATION.** 100bb cash with no ICM is the single most-studied,
most-canonical NLHE context; freezing there is the *right* simplification for a beginner. The
real cost is no stack-depth awareness (3-bet pot SPRs, short-stack shove/fold) — but those are
explicitly out of scope. No dynamic opponent-modeling is *appropriate* here: the whole
pedagogy is that each bot is a fixed archetype to be read. Justified.
*Cite:* pokercoaching "start with GTO fundamentals then exploit"; scope is beginner cash.

### Claim 3 — Maniac 3-bets value at 100% but merged tier at 45% — directionally plausible?
**Verdict: DEFENSIBLE-SIMPLIFICATION, with one real quibble.** Directionally correct: a real
maniac 3-bets a very wide, bluff-heavy range, and pure-value-at-100% + a big bluffy tier is the
right *shape*. But a true population maniac (VPIP >50, "re-raises almost every time") would
3-bet *more* than 45% of the merged tier and would not have a disciplined `TT+/AJs+/AQo+`
value core — the JSON maniac is closer to a competent LAG's 3-bet build than to a genuine
spew-monkey. That's arguably *good* for a trainer (a truly random maniac teaches nothing), but
it means "maniac" is mislabeled relative to the population read the app claims to teach.
*Cite:* maniac VPIP >50 / constant re-raising (pokerology, beastsofpoker). Minor mismatch;
justified by not wanting an unlearnable bot.

### Claim 4 — Sizing as flat multiplier of last-raise-to (not pot-relative/geometric)
**Verdict: DEFENSIBLE-SIMPLIFICATION.** `3bet = mult × last_raise_to` is precisely the live-poker
rule of thumb (3× IP / 4× OOP the raise). It is not GTO-geometric and it ignores that correct
3-bet sizing is pot-and-position dependent, but the flat-multiplier convention is what every
book/coach *teaches beginners*. Iso = open + 1bb/limper is textbook live. Justified.
*Cite:* 888poker GTO open-raising (raise-size heuristics); standard live iso rule.

### Claim 5 — Limp-heavy ranges for loose personas; is limping ever GTO/defensible?
**Verdict: QUESTIONABLE (theory), DEFENSIBLE (pedagogy).** At 100bb cash, GTO essentially never
open-limps — SB completes only ~4.2% vs a correct BB, and BTN open-limping is a ≤14bb
tournament artifact, gone by 17bb. The maniac's *large* UTG/BTN limp ranges are **not GTO and
not even good exploitative play** at 100bb. HOWEVER, limping IS a hallmark of the real-world
"passive fish / loose-limpy" population the app wants to depict, and giving a beginner live
reps against limpers (iso-raising them, punishing limp-behind) is pedagogically valuable. So:
theoretically indefensible as "optimal," but *correct as a caricature of a real leak*. The
label to watch: this is limping-as-a-fish-tell, not limping-as-strategy.
*Cite:* GTO Wizard "Curious Case of Open-Limping Buttons" (short-stack only); PokerNews SB
limp ~4.2%. Divergence justified ONLY as fish-modeling, not as strategy to imitate.

### Claim 6 — 7-rung analytic ladder adequately represents postflop strength
**Verdict: QUESTIONABLE.** Absolute made-hand rungs are a real, load-bearing simplification.
Postflop EV is **equity vs the opponent's range**, not absolute strength: top pair on A72r is a
near-nut bluff-catcher; the *same* top pair on JT9ss is a marginal hand that folds to
aggression. The ladder can't tell them apart because texture only enters via sizing, never
value. The MONSTER bucket lumping non-nut and nut flushes together is the sharpest error — nut
vs 3rd-nut flush play very differently and the engine treats them identically. For a *beginner*
trainer this is a tolerable coarse-grain, but it's the second-biggest theoretical gap (behind
price-blindness) because it means bot value/aggression decisions are texture-agnostic.
*Cite:* GTO Wizard flop heuristics (value is board-texture-dependent — weak vs strong top pair
size differently); Janda *Applications of NLHE* (equity-vs-range is the unit of postflop
decisions). Partly justified by beginner goal; the nut/non-nut MONSTER collapse is a genuine
modeling weakness.

### Claim 7 — Multiplicative "shared merit × persona lever" produces coherent archetypes?
**Verdict: QUESTIONABLE — the maniac proves the model breaks at the extreme.** For moderate
levers (0.5–3.2) the multiplicative shaping is fine and produces sensible monotone ordering.
But because `aggression` multiplies value/raise merit while `check`/`fold` merit stays fixed,
the transform **saturates**: at aggression 15 a top pair bets 95% and raises a made hand facing
a bet at 73% — value-frequency spew, mathematically a near-argmax despite the "always mixed"
design. The team admits this (`test:554`). It is not a bug in the *arithmetic*; it's a
structural flaw in using an unbounded multiplier on one side of an un-normalized ratio. A
logistic/softmax shaping or a bounded lever would not saturate. So the mechanism is *sound in
its coherent regime and unsound at the top of its own range* — and the top of its range is
occupied by a shipped persona.
*Cite:* the engine's own `test_personas_postflop.py:554–561`. This is an internal-coherence
failure, not merely a GTO divergence.

### Claim 8 — Sizing fully independent of hand strength (not range-balanced)
**Verdict: SOUND as anti-tell / DEFENSIBLE-SIMPLIFICATION overall.** Decoupling size from
strength is *exactly right* for not leaking value-vs-bluff — that is a genuine GTO property
(balanced ranges at each size). The gap vs GTO is that GTO *also* balances the range **at each
size** (small-bet range and big-bet range each have correct value:bluff), whereas here one size
distribution is applied over all buckets, so the size-conditioned ranges are not
theory-balanced. For a beginner opponent this is invisible and harmless — a human can't exploit
"this bot's 33%-bet range has slightly wrong composition." Justified.
*Cite:* Red Chip "Multiple Bet Sizes in GTO Poker" (balance is *per size*, which the engine
doesn't do but doesn't need to for beginners).

### Claim 9 — Bluff cell + flat `bluff_freq`, NOT tied to bet size / MDF
**Verdict: WRONG (as poker theory) — the single biggest theoretical gap, tied with §12.** GTO
bluff frequency is a **function of bet size**: 1/3 pot → ~20% bluffs, 1/2 pot → 25%, pot →
33%, overbet → 38–40%. The engine's `bluff_freq` is a flat per-persona constant *completely
decoupled* from the size it then samples. Concretely: TAG bluffs at 0.22 whether it fires 33%
pot (theory wants ~0.20 → coincidentally close) or pot-size (theory wants ~0.33 → materially
under-bluffed). Because the size is drawn *independently and afterward*, the bot can bet 1.5×
pot with a 0.22 flat bluff rate — an overbet that theory says should be ~40% bluffs. The
value:bluff ratio is therefore **uncorrelated with the price the bot lays**, which is the exact
quantity a student is supposed to learn to read. This is not a harmless simplification: it can
actively mis-train bluff-catching (see §17). Verdict WRONG on theory; only *partly* excused
because the app doesn't claim these bots are balanced.
*Cite:* SplitSuit "Perfect GTO Bluffing"; DeucesCracked 2026 bluff-frequency; PokerStrategy
"Bet sizing and bluffing." The bet-size↔bluff-frequency link is first-order theory the engine
omits.

### Claim 10 — SPR-commit rule (fold→0, agg×3 at SPR ≤ threshold with overpair+)
**Verdict: QUESTIONABLE, trending WRONG at high thresholds.** Modern SPR theory explicitly
rejects the "low SPR ⇒ automatically committed, never fold" framing the rule encodes. Miller/
Flynn/Mehta's SPR is about **equity thresholds dropping**, not fold-mass vanishing — a low SPR
means you need *less* equity to continue, not that you continue with everything down to an
overpair regardless of range/board/opponents. The rule ignores equity-vs-range, texture, and
opponent count entirely, which is precisely the "pot-committed fallacy" the sources warn
against. Worse, maniac `spr_commit 4.0` fires in nearly every single-bet pot (SPR ≤4 is the
norm after one flop bet at 100bb), so its overpairs *never* fold — that's not commitment, it's
a stuck-off calling machine. A threshold near the theory-sensible 1–2 zone (nit 1.2,
calling_station 1.5) is defensible; 3.0–4.0 (LAG/maniac) is theoretically wrong.
*Cite:* Red Chip "SPR"; PokerTube "Pot Committed… Fallacy"; Miller/Flynn/Mehta *Professional
NLHE Vol I* (2007). Low thresholds defensible; high thresholds a genuine error.

### Claim 11 — `multiway_bluff_damp^(opponents−1)` exponential bluff decay
**Verdict: DEFENSIBLE functional form, MIS-CALIBRATED constants.** Exponential/multiplicative
decay per additional opponent is a *reasonable* shape — the probability that all N opponents
whiff is roughly multiplicative, so each extra caller multiplies bluff EV down. The problem is
the constants. Theory says bluff/c-bet frequency drops **~50% from HU to 3-way**. The engine's
per-opponent multiplier means 3-way retention = damp². Check the personas: nit damp 0.30 →
3-way retention 0.09 (drops 91% — far too much); maniac damp 0.85 → 3-way retention 0.72
(drops only 28%, vs theory ~50%). So the *form* is fine but the calibration is all over the
map: tight personas over-fold multiway into near-zero, the maniac barely slows down (it still
air-bets 47% into two players — theory says a c-bet range should roughly halve). The maniac
number is the worst offender.
*Cite:* pokergtosolver / poker-alpha "bluff frequency drops ~50%+ HU→multiway"; GTO Wizard
"Monkey in the Middle" 3-way heuristics. Form defensible; maniac/nit constants wrong.

### Claim 12 — Fold/call/raise merits static per bucket, NOT derived from pot odds or MDF
**Verdict: WRONG (as poker theory) — co-biggest gap with §9.** A bot facing a bet does **not
look at the price**. Static `_FOLD_BASE`/`_CALL_BASE` per bucket means the bot folds top pair
to a 1/4-pot bet at the *same rate* it folds to a 2×-pot overbet. Real defense is governed by
pot odds (call if equity ≥ price) and, vs a balanced bettor, by MDF (defend ≥ pot/(pot+bet):
75% vs 1/3, 50% vs pot). The engine collapses an entire axis of the game — **defense as a
function of price** — to a constant. This is the axis a beginner most needs to internalize
("am I getting the right price to call?"). It is not excused by the archetype framing: you can
have exploitable *frequencies* while still making them *respond to price*; the engine does
neither. Genuine modeling error, only softened by "these bots are deliberately exploitable."
*Cite:* GTO Wizard "MDF & Alpha"; splitsuit "MDF 101"; pot-odds fundamentals. This is the
single most important theoretical omission in the engine.

### Claim 13 — Do the 6 archetypes + lever values map to real population reads?
**Verdict: DEFENSIBLE, directionally correct, magnitude fuzzy.** The *ordering* is right and
matches population data: nit (tight-passive, low agg), calling_station (max stickiness 1.8, low
agg 0.5 — correct: high VPIP-call, near-zero AF), passive_fish (sticky+passive), TAG (agg 2.4),
LAG (agg 3.2), maniac (highest). Direction of every lever matches the real VPIP/PFR/AF profiles
cited. Two magnitude problems: (a) maniac aggression 15 is a saturation artifact, not a
population multiple (team admits this); (b) the team's own tests show WTSD misses real
population bands for 5/6 personas and they re-anchored the bands to engine output
(`test:520–552`) — so the personas are internally consistent but *not* population-faithful on
showdown frequency. Ordering: sound. Absolute fidelity: not achieved and partly acknowledged.
*Cite:* PokerVIP / pokerology / pokercoaching archetype VPIP-PFR-AF tables; engine
`test_personas_postflop.py:520–561`. Directionally justified; magnitudes are calibration
artifacts.

### Claim 14 — Is a single scalar `aggression` a defensible model of "style"?
**Verdict: QUESTIONABLE — the maniac is the proof it isn't sufficient alone.** Style is
multi-dimensional (frequency of aggression ≠ sizing ≠ street-consistency ≠ bluff selection).
Compressing "aggression" to one scalar that multiplies a fixed merit table means the *only* way
to make a bot more aggressive is to distort the frequency mix toward saturation — which is
exactly what breaks the maniac. The engine partially rescues this with *separate* stickiness,
bluff_freq, spr_commit, damp levers (so style isn't literally one scalar), but the aggression
lever specifically, being unbounded and multiplicative, is the fragile one. A bounded or
logit-space aggression parameter would model "style" far more robustly. So: single scalar is a
*defensible starting basis* but demonstrably insufficient at the extreme.
*Cite:* internal evidence (maniac saturation, `test:554`); general point that AF, bluff
frequency, and sizing are independent stat axes (PokerVIP profiling stats). Partly justified.

### Claim 15 — Are 5 scalar levers a sufficient basis for the player-type space?
**Verdict: QUESTIONABLE — important axes missing.** Missing dimensions that materially define
real player types: (a) **position awareness** — real players' ranges/aggression swing hugely by
position; these bots' postflop levers are position-blind. (b) **board-texture sensitivity** —
value decisions ignore texture (see §6); only sizing sees it. (c) **bet-size reading** — bots
don't defend differently vs different bet sizes (see §12), so they can't model "folds too much
to big bets" vs "calls any size." (d) **street/barrel consistency** — no multi-street plan, so
no "gives up turn" vs "triple-barrels" axis. These are not exotic; fold-to-cbet-by-size and
positional aggression are core HUD reads. Five scalars span a coarse 1-D aggression×stickiness
plane well; they cannot span the real 2-D+ read space. Justified for a *first* trainer, but a
real limitation for the "teach real reads" claim.
*Cite:* PokerVIP "four stats" (VPIP/PFR/3bet/AF) plus positional and by-street stats are what
profiling actually uses. Partly justified by beginner scope.

### Claim 16 — Is "exploit archetypes first, GTO later" pedagogically sound?
**Verdict: SOUND / DEFENSIBLE.** This matches expert consensus. Beginners benefit most from
"exploit the obvious — value bet strong hands, fold marginal ones vs strength, don't bluff
players who never fold"; recommended study split is ~50–70% exploitative for developing
players, with GTO as the framework. Learning to *read and exploit* fixed leaks is a legitimate,
even primary, early-stage skill. The risk (below) is specific mis-training from *particular*
unrealistic bot behaviors, not the pedagogy itself.
*Cite:* pokercoaching "Exploitative or GTO"; PokerStrategy "GTO vs Exploit — you need both";
casino.org GTO strategy. Pedagogy justified.

### Claim 17 — Which trade-offs are harmless vs actively misleading?
**Verdict (mixed):**
- **Harmless:** coarse buckets, size-independent-of-strength (anti-tell), static 100bb, no ICM,
  approximate EV labels, no multi-street plan. A beginner won't be mis-trained by these.
- **Potentially MISLEADING:** (1) **price-blind defense (§12)** — training against opponents
  whose folding never responds to your bet size can teach a student that sizing doesn't matter
  for fold equity, the opposite of a core lesson. (2) **bluff frequency decoupled from size
  (§9)** — a student "reading" a bot's bluffs learns a size↔bluff relationship that doesn't
  exist, and may carry a mis-calibrated bluff-catching instinct to real games. (3) **maniac
  over-commit/over-bluff (§10/§7)** — a caricature so extreme it teaches "punish maniacs by
  never folding value," which over-generalizes against merely-aggressive real players.
The first two are the ones to fix; they sit exactly on the skills the app claims to teach.
*Cite:* GTO Wizard MDF (defense IS price-driven); SplitSuit GTO bluffing (bluff freq IS
size-driven). These two divergences are genuine mis-training risks, not benign simplifications.

### Claim 18 — Are the real numeric heuristics (⅓≈4:1, pot≈2:1, MDF, ⅓-½-⅔ by street) anywhere
in the engine — and should they be?
**Verdict: They are ABSENT, and at least the defense/bluff ones SHOULD be present.** I searched
the engine: `bluff_freq` is a flat constant, defense merits are static per bucket, sizing is a
per-node pot-fraction distribution — **none of MDF, pot-odds, or the size↔bluff-ratio law
appears anywhere in the decision math**. `HERO_NODE_SIZE`/`POSTFLOP_BET_FRACS` encode ⅓/½/¾/pot
*sizes* (good — the ⅓-½-⅔-by-street idea is present in the *hero grading* sizes), but the
*bots* never connect those sizes to a bluff ratio or a defense frequency. For a trainer that
"claims to teach real poker," the two first-order laws — (a) defend ≈ MDF / by pot odds, (b)
bluff frequency scales with bet size — are the highest-value things to inject, because they're
cheap (both are one-line functions of the size the engine *already samples*) and they're
exactly what the app wants the human to learn. Their absence is the clearest case of
"beginner-friendly" being stretched to cover a genuine, fixable gap.
*Cite:* GTO Wizard MDF & Alpha; SplitSuit Perfect GTO Bluffing; DeucesCracked bluff-frequency.
Should be added.

---

## The 3–5 most serious problems, ranked

1. **Price-blind defense (Claim 12).** Bots fold/call at a static per-bucket rate that never
   looks at the bet size / pot odds / MDF. This deletes the single most important axis a
   beginner must learn ("am I priced in?") and can *mis-train* the student that sizing doesn't
   affect fold equity. Cheap to fix: scale `_FOLD_BASE` by a price term derived from the faced
   size the engine already knows.

2. **Bluff frequency decoupled from bet size (Claims 9 & 18).** `bluff_freq` is a flat constant;
   the size is sampled independently afterward. Real bluff-to-value is a function of size
   (⅓→20%, pot→33%, overbet→40%). The bot can overbet with a 22% bluff rate that theory says
   should be ~40%. Undermines exactly the read the app teaches, and is a one-line fix (make
   effective bluff mass a function of the sampled fraction).

3. **Aggression-lever saturation / maniac (Claims 7, 10, 11, 14).** An unbounded multiplicative
   `aggression` on one side of an un-normalized ratio saturates into near-argmax; maniac=15
   value-bets/raises marginal hands at spew frequency, `spr_commit 4.0` makes its overpairs
   never fold, and `multiway_damp 0.85` barely slows its multiway bluffing (47% into two).
   Internal-coherence failure (the team admits it), not just a GTO divergence. Fix: bounded/
   logit-space aggression, lower maniac spr_commit toward 1.5–2, lower damp toward ~0.6.

4. **Absolute made-hand ladder ignores equity-vs-range and texture (Claim 6).** Value decisions
   are texture-blind; MONSTER collapses nut and non-nut flushes. Second-tier because a beginner
   tolerates coarse strength, but the nut/non-nut collapse is a real weakness.

5. **Multiway decay mis-calibration (Claim 11).** Right functional form, wrong constants across
   the board (nit drops 91% by 3-way, maniac only 28%, vs theory ~50%).

## The single biggest thing the engine gets RIGHT

**Sizing decoupled from hand strength (Claim 8) — a genuine GTO property, correctly
implemented as anti-sizing-tell.** `postflop_node_key` reads only board+legal, never hole
cards, so a bot's bet size never leaks value-vs-bluff. This is the *hardest* balance property
for humans to maintain and the engine gets it for free and exactly right. Runner-up: the
**correct directional ordering of all six archetypes' levers** against real population VPIP/PFR/
AF profiles — the taxonomy itself is sound; it's only the extreme magnitudes and the missing
price/size linkages that fail.

---

## Sources

- GTO Wizard — MDF & Alpha: https://blog.gtowizard.com/mdf-alpha/
- GTO Wizard — Mathematical Misconceptions in Poker: https://blog.gtowizard.com/mathematical-misconceptions-in-poker/
- GTO Wizard — Monkey in the Middle (3-Way Pot Heuristics): https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/
- GTO Wizard — Flop Heuristics: IP C-Betting in Cash Games: https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/
- GTO Wizard — The Curious Case of Open-Limping Buttons: https://blog.gtowizard.com/curious-case-of-open-limping-buttons/
- GTO Wizard — The Math of Multi-Street Bluffs: https://blog.gtowizard.com/the-math-of-multistreet-bluffs/
- SplitSuit — MDF 101 + Free Calculator: https://www.splitsuit.com/mdf-101-and-free-calculator
- SplitSuit — Perfect GTO Bluffing: https://www.splitsuit.com/perfect-gto-bluffing
- Red Chip Poker — Multiple Bet Sizes in GTO Poker: https://redchippoker.com/multiple-bet-sizes-in-gto-poker/
- Red Chip Poker — SPR (Stack-to-Pot Ratio): https://redchippoker.com/spr-stack-to-pot-ratio-podcast/
- PokerStrategy — Bet sizing and bluffing: https://www.pokerstrategy.com/news/content/Bet-sizing-and-bluffing_114118/
- PokerStrategy — GTO vs Exploit? You need both: https://www.pokerstrategy.com/news/content/GTO-vs-Exploit-You-need-both_125147/
- DeucesCracked — GTO Bluff Frequency 2026: https://www.deucescracked.com/blog/gto-bluff-frequency-2026-modern-solver-balanced-river-bets
- PokerGTOSolver — Multiway Pot GTO Strategy: https://pokergtosolver.com/en/blog/multiway-pot-gto-strategy
- Poker-Alpha — Why Multi-Way Pots Break Solver Habits: https://poker-alpha.com/en/insights/multiway-pots/
- PokerVIP — Player Profiling: Three Major Poker Player Types: https://www.pokervip.com/strategy-articles/texas-hold-em-no-limit-advanced/player-profiling-three-major-poker-player-types
- Pokerology — Types of Poker Players (TAG/LAG/NIT/Station): https://www.pokerology.com/poker/strategy/playing-styles/
- PokerCoaching — Types of Poker Players: https://pokercoaching.com/blog/different-poker-players/
- PokerCoaching — Exploitative or GTO: https://pokercoaching.com/blog/exploitative-or-gto-which-is-the-better-poker-strategy/
- PokerCoaching — MDF Poker: https://pokercoaching.com/blog/mdf-poker/
- PokerTube — Pot Committed: Meaning, Fallacy & Common Misreads: https://www.pokertube.com/article/pot-committed
- The Poker Bank — Stack To Pot Ratio (SPR): https://www.thepokerbank.com/strategy/concepts/spr/
- PokerNews — Limp-Reraising From the Small Blind Against a GTO Opponent: https://www.pokernews.com/strategy/limp-reraising-from-the-small-blind-against-a-gto-opponent-31107.htm
- 888poker — GTO Open Raising Strategies: https://www.888poker.com/magazine/strategy/gto-opening-raising-strategy
- bbzpoker — GTO Preflop Charts Explained: https://bbzpoker.com/how-to-use-gto-charts/
- Book: Ed Miller, Sunny Mehta, Matt Flynn — *Professional No-Limit Hold'em: Volume I* (2007), SPR & commitment chapters.
- Book: Matthew Janda — *Applications of No-Limit Hold'em* (equity-vs-range, bluff-to-value construction).
