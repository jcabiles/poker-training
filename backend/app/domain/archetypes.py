"""Villain archetypes for exploit drills (pure domain)."""

from __future__ import annotations

from enum import Enum


class VillainType(str, Enum):
    CALLING_STATION = "calling_station"  # calls too much, won't fold, rarely raises
    NIT = "nit"  # folds too much, only premiums
    LAG = "lag"  # opens/3-bets too wide, aggressive
    PASSIVE_FISH = "passive_fish"  # limps/calls, passive
