"""Decision — the player's chosen action at a Spot."""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from app.domain.spot import ActionType


class Decision(BaseModel):
    action: ActionType
    size_bb: float | None = None
    size_fraction: float | None = None  # fraction of pot (postflop convenience)

    @model_validator(mode="after")
    def _require_size_for_aggressive(self):
        if self.action in (ActionType.BET, ActionType.RAISE):
            if self.size_bb is None and self.size_fraction is None:
                raise ValueError(f"{self.action.value} requires size_bb or size_fraction")
        return self
