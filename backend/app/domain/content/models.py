"""ContentPack models — the strategy-as-data contract.

Entry format is locked for mixed strategies from day 1: each entry's `actions`
is a list of {action, combos, frequency}. The heuristic provider sets
frequency=1.0 on its dominant action; a solver provider later fills true mixed
frequencies with NO format change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.archetypes import VillainType
from app.domain.content.notation import parse_range
from app.domain.spot import ActionType, NodeContext, Position

# The 8 frontend drill Mode values (frontend/src/api/types.ts::Mode /
# frontend/src/lib/hashRoute.ts::MODE_IDS) that a card's "drill this" link can
# navigate to via hash routing (#/drill/<mode>). Kept in sync manually with
# the FE, same convention as the rest of the hand-maintained wire types.
DrillMode = Literal[
    "random",
    "review",
    "leak_focus",
    "exploit",
    "challenge",
    "postflop",
    "vs_cbet",
    "vs_check_raise",
]


class ActionRange(BaseModel):
    action: ActionType
    combos: str  # range-notation string (see notation.parse_range)
    frequency: float = Field(default=1.0, ge=0.0, le=1.0)


class Entry(BaseModel):
    node_context: NodeContext
    position: Position
    facing: Position | None = None  # opener / 3-bettor position when relevant
    limper_count: int | None = None  # for vs_limpers entries
    villain_type: VillainType | None = None  # set for exploit-overlay entries
    rationale: str | None = None  # one-line "why" for exploit entries
    actions: list[ActionRange]
    sizing_bb: float | None = None


class ContentPack(BaseModel):
    id: str
    version: int
    domain: str
    description: str = ""
    entries: list[Entry] = Field(default_factory=list)
    sizing_rules: dict = Field(default_factory=dict)
    exploit_overlays: dict = Field(default_factory=dict)  # freeform stub in Phase 0/1


# Persona packs (Simulate S3) — bot preflop strategy as data. Action-name
# vocabulary is per node facing; names are CONTENT-level (limp/3bet/...) and
# translated to wire ActionType by the engine (app/domain/personas.py).
PersonaFacing = Literal["unopened", "vs_limpers", "vs_rfi", "vs_3bet", "vs_4bet"]

_FACING_ACTIONS: dict[str, frozenset[str]] = {
    "unopened": frozenset({"fold", "limp", "raise"}),
    "vs_limpers": frozenset({"fold", "limp", "raise"}),  # limp = over-limp
    "vs_rfi": frozenset({"fold", "call", "3bet"}),
    "vs_3bet": frozenset({"fold", "call", "4bet"}),
    "vs_4bet": frozenset({"fold", "call", "5bet_shove"}),
}


class PersonaActionMix(BaseModel):
    combos: str  # range-notation string (see notation.parse_range)
    # action-name -> probability; sum <= 1.0; remainder is an implicit fold.
    weights: dict[str, float]

    @field_validator("combos")
    @classmethod
    def _combos_parse(cls, v: str) -> str:
        parse_range(v)  # raises ValueError on unsupported notation tokens
        return v

    @field_validator("weights")
    @classmethod
    def _weights_valid(cls, v: dict[str, float]) -> dict[str, float]:
        for name, w in v.items():
            if not 0.0 <= w <= 1.0:
                raise ValueError(f"weight for {name!r} out of [0, 1]: {w}")
        if sum(v.values()) > 1.0 + 1e-9:
            raise ValueError(f"weights sum to {sum(v.values())} > 1.0")
        return v


class PersonaNode(BaseModel):
    facing: PersonaFacing
    positions: list[Position] | None = None  # None = wildcard (any position)
    mixes: list[PersonaActionMix]  # FIRST MATCH WINS; unmatched hand-class => fold 1.0

    @model_validator(mode="after")
    def _action_vocabulary(self) -> PersonaNode:
        allowed = _FACING_ACTIONS[self.facing]
        for mix in self.mixes:
            bad = set(mix.weights) - allowed
            if bad:
                raise ValueError(f"actions {sorted(bad)} not allowed facing {self.facing!r}")
        return self


class PersonaSizing(BaseModel):
    """Authored in S3, consumed in S4 (the S3 engine ignores it)."""

    open_bb: float
    threebet_mult: float
    fourbet_mult: float


class PersonaPostflop(BaseModel):
    """Postflop lever block (S4) — every persona-differentiating number lives
    here; the shared mechanics live in app/domain/personas_postflop.py."""

    aggression: float = Field(gt=0.0)  # scales bet/raise merit (1.0 = neutral)
    stickiness: float = Field(gt=0.0)  # scales call merit / resistance to folding
    bluff_freq: float = Field(ge=0.0, le=1.0)  # baseline bet/raise rate with air
    sizing: dict[str, float]  # pot-fraction str -> weight; weights sum to ~1
    spr_commit: float = Field(gt=0.0)  # SPR at/below which strong+ hands commit
    multiway_bluff_damp: float = Field(ge=0.0, le=1.0)  # per extra opponent

    @field_validator("sizing")
    @classmethod
    def _sizing_valid(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("sizing must be non-empty")
        total = 0.0
        for key, weight in v.items():
            try:
                frac = float(key)
            except ValueError:
                raise ValueError(f"sizing key {key!r} is not a float pot fraction") from None
            if frac <= 0.0:
                raise ValueError(f"sizing fraction {key!r} must be > 0")
            if weight <= 0.0:
                raise ValueError(f"sizing weight for {key!r} must be > 0")
            total += weight
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"sizing weights sum to {total}, expected ~1.0")
        return v


class PersonaPack(BaseModel):
    id: str  # "persona_passive_fish" etc.
    version: str
    domain: Literal["persona"]
    persona: VillainType  # the acting identity
    display_name: str
    sizing: PersonaSizing
    preflop: list[PersonaNode]
    postflop: PersonaPostflop | None = None  # required in all 6 shipped packs

    @model_validator(mode="after")
    def _node_ordering(self) -> PersonaPack:
        """Per facing: explicit-position nodes BEFORE the (at most one) wildcard,
        and explicit-position nodes may not overlap positions (lookup is
        first-match-in-list-order; see personas.sample_preflop_action)."""
        seen_positions: dict[str, set[Position]] = {}
        wildcard_seen: set[str] = set()
        for node in self.preflop:
            if node.positions is None:
                if node.facing in wildcard_seen:
                    raise ValueError(f"more than one wildcard node facing {node.facing!r}")
                wildcard_seen.add(node.facing)
                continue
            if node.facing in wildcard_seen:
                raise ValueError(
                    f"explicit-position node after wildcard facing {node.facing!r}"
                )
            prior = seen_positions.setdefault(node.facing, set())
            overlap = prior & set(node.positions)
            if overlap:
                raise ValueError(
                    f"duplicate position coverage facing {node.facing!r}: {sorted(overlap)}"
                )
            prior.update(node.positions)
        return self


class ConceptCard(BaseModel):
    """Point-of-need teaching content (N8), versioned JSON under content/cards/.

    Matching (leak_category first, rationale_tags to disambiguate) lives in
    app/services/concept_cards.py, NOT here — this model is pure content-data,
    same as ContentPack/Entry above.
    """

    id: str
    version: int
    title: str
    summary: str  # 2-3 sentences, shown collapsed
    body: str  # a few short paragraphs, shown expanded
    leak_categories: list[int]  # LeakCategory ints this card can answer
    rationale_tags: list[str] = Field(default_factory=list)  # disambiguators; [] = leak-only match
    drill_mode: DrillMode  # where "drill this" navigates (#/drill/<mode>)
    source_doc: str  # docs/research/<source_doc>-*.md this card distills
