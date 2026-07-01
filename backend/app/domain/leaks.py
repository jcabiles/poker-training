"""Leak-category taxonomy.

Reserved numeric namespaces so later phases never renumber and break historical
analytics rows:
  preflop  100-199
  postflop 200-299  (Phase 2)
  exploit  300-399
Bump TAXONOMY_VERSION on any change; never reuse a retired number.
"""

from __future__ import annotations

from enum import IntEnum

TAXONOMY_VERSION = 2


class LeakCategory(IntEnum):
    # --- Preflop (100-199) ---
    RFI_EP = 100
    RFI_MP = 101
    RFI_CO = 102
    RFI_BTN = 103
    RFI_SB = 104
    BLIND_DEFENSE = 110  # hero in SB/BB facing an open
    VS_RFI = (
        112  # hero in a non-blind seat facing an open (call/3bet/fold nuance via rationale_tags)
    )
    VS_3BET_IP = 120
    VS_3BET_OOP = 121
    FOURBET_RESPONSE = 130
    SQUEEZE = 140
    VS_LIMPERS = 150
    SIZING = 160

    # --- Postflop (200-299) ---
    FLOP_CBET = 200  # flop c-bet decision (HU SRP)
    VS_CBET = 201  # facing a flop c-bet — defense (HU SRP)
    VS_CHECK_RAISE = 202  # facing a flop check-raise as the original bettor (Phase 2e-1)
    BOARD_TEXTURE = 210  # board-texture classification drill
    EQUITY_EST = 211  # equity-estimation drill

    # --- Exploit (300-399), per villain archetype ---
    CALLING_STATION_EXPLOIT = 300
    NIT_EXPLOIT = 301
    LAG_EXPLOIT = 302
    PASSIVE_FISH_EXPLOIT = 303
