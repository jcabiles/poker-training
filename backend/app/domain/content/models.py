"""ContentPack models — the strategy-as-data contract.

Entry format is locked for mixed strategies from day 1: each entry's `actions`
is a list of {action, combos, frequency}. The heuristic provider sets
frequency=1.0 on its dominant action; a solver provider later fills true mixed
frequencies with NO format change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.archetypes import VillainType
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
