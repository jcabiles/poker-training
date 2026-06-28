"""ContentPack models — the strategy-as-data contract.

Entry format is locked for mixed strategies from day 1: each entry's `actions`
is a list of {action, combos, frequency}. The heuristic provider sets
frequency=1.0 on its dominant action; a solver provider later fills true mixed
frequencies with NO format change.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.archetypes import VillainType
from app.domain.spot import ActionType, NodeContext, Position


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
