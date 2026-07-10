"""Villain archetypes for exploit drills (pure domain)."""

from __future__ import annotations

from enum import StrEnum


class VillainType(StrEnum):
    CALLING_STATION = "calling_station"  # calls too much, won't fold, rarely raises
    NIT = "nit"  # folds too much, only premiums
    LAG = "lag"  # opens/3-bets too wide, aggressive
    PASSIVE_FISH = "passive_fish"  # limps/calls, passive
    TAG = "tag"  # tight-aggressive regular (Simulate persona)
    MANIAC = "maniac"  # hyper-aggressive, raises everything (Simulate persona)


# The exploit-drill roster — the original 4 archetypes with exploit-overlay
# content. Simulate personas (TAG/MANIAC) act at the table but have no
# exploit pack; keep exploit-drill consumers keyed to this subset.
EXPLOIT_ARCHETYPES: frozenset[VillainType] = frozenset(
    {VillainType.CALLING_STATION, VillainType.NIT, VillainType.LAG, VillainType.PASSIVE_FISH}
)
