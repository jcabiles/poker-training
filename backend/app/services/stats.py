"""Leak tracking + summary aggregation over DrillAttempt rows."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.db.models import DrillAttempt, SRSItemRow
from app.domain.leaks import LeakCategory

_GOOD = {"optimal", "acceptable"}

# Challenge-mode personal difficulty multiplier (Phase: Challenge mode T3).
# Named per the shared ticket contract — keep these in sync with
# docs/ai-dlc/tickets/challenge-preflop-rfi.md.
MIN_N = 5  # minimum RFI attempts on a hand class before it gets a personal signal
M_MIN = 0.5  # floor multiplier — hand classes the user plays cleanly
M_MAX = 2.0  # ceiling multiplier — hand classes the user misplays most

_RFI_CATEGORIES = {
    int(LeakCategory.RFI_EP),
    int(LeakCategory.RFI_MP),
    int(LeakCategory.RFI_CO),
    int(LeakCategory.RFI_BTN),
    int(LeakCategory.RFI_SB),
}


def _name(cat: int) -> str:
    try:
        return LeakCategory(cat).name
    except ValueError:
        return str(cat)


def leak_stats(session: Session) -> list[dict]:
    rows = list(session.exec(select(DrillAttempt)))
    by: dict[int, list[DrillAttempt]] = defaultdict(list)
    for r in rows:
        if r.leak_category is not None:
            by[r.leak_category].append(r)

    out = []
    for cat, items in by.items():
        n = len(items)
        good = sum(1 for i in items if i.correctness in _GOOD)
        out.append(
            {
                "category": cat,
                "name": _name(cat),
                "attempts": n,
                "accuracy": round(good / n, 3) if n else 0.0,
                "avg_ev_loss": round(sum(i.ev_loss_bb for i in items) / n, 3) if n else 0.0,
            }
        )
    out.sort(key=lambda x: (x["accuracy"], -x["attempts"]))  # worst first
    return out


def _accuracy(items: list[DrillAttempt]) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if i.correctness in _GOOD) / len(items)


def summary(session: Session, today: date | None = None) -> dict:
    # DrillAttempt.created_at is stamped in UTC; compare the streak in UTC too so
    # "today" matches the stored dates (avoids a UTC-vs-local date-boundary gap).
    today = today or datetime.now(UTC).date()
    rows = list(session.exec(select(DrillAttempt)))
    ordered = sorted(rows, key=lambda r: r.created_at)

    days = {r.created_at.date() for r in rows}
    streak, d = 0, today
    while d in days:
        streak += 1
        d -= timedelta(days=1)

    due = len(list(session.exec(select(SRSItemRow).where(SRSItemRow.due_date <= today))))
    trend = round(_accuracy(ordered[-20:]) - _accuracy(ordered[-40:-20]), 3)

    return {
        "total_attempts": len(rows),
        "accuracy": round(_accuracy(rows), 3),
        "due_count": due,
        "streak_days": streak,
        "trend": trend,
    }


def hand_error_weights(session: Session) -> dict[str, float]:
    """Per-hand-class personal difficulty multiplier for Challenge-mode sampling.

    Aggregates RFI `DrillAttempt` rows (`leak_category` in {100..104}, i.e.
    RFI_EP..RFI_SB) by `hand_class` and maps mean `ev_loss_bb` to a multiplier in
    `[M_MIN, M_MAX]`, normalized so the mean multiplier across the returned classes
    is ~1.0. Hand classes with fewer than MIN_N attempts are omitted entirely — the
    caller (the challenge sampler) defaults omitted classes to a neutral 1.0.

    Degenerate inputs resolve to neutral rather than raising:
      - no qualifying rows at all -> {}
      - every qualifying class shares (near enough) the same mean EV-loss, so
        there's no signal to rank on -> every qualifying class gets 1.0.
    """
    rows = list(
        session.exec(select(DrillAttempt).where(DrillAttempt.leak_category.in_(_RFI_CATEGORIES)))
    )

    losses_by_class: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r.hand_class is not None:
            losses_by_class[r.hand_class].append(r.ev_loss_bb)

    means = {
        hc: sum(losses) / len(losses)
        for hc, losses in losses_by_class.items()
        if len(losses) >= MIN_N
    }
    if not means:
        return {}

    overall_mean = sum(means.values()) / len(means)
    deviations = {hc: m - overall_mean for hc, m in means.items()}
    spread = max(abs(d) for d in deviations.values())
    if spread < 1e-9:
        # All qualifying classes have (effectively) the same mean EV-loss —
        # nothing to rank on, so stay neutral instead of a 0/0 blowup.
        return dict.fromkeys(means, 1.0)

    # Raw (pre-rescale) multiplier: worse hands (dev >= 0, higher mean
    # ev_loss_bb) scale toward M_MAX, better hands scale toward M_MIN. Scaling
    # each side by its own half-range keeps the class at spread's extreme
    # exactly at M_MAX/M_MIN, but — since qualifying classes rarely split
    # symmetrically above/below the mean, especially with only 2-3 classes —
    # the mean of these raw multipliers can drift well away from 1.0.
    raw: dict[str, float] = {}
    for hc, dev in deviations.items():
        half_range = (M_MAX - 1.0) if dev >= 0 else (1.0 - M_MIN)
        raw[hc] = 1.0 + (dev / spread) * half_range

    # True mean-preserving rescale: divide by the raw mean BEFORE clamping, so
    # the returned weights' mean is ~1.0 regardless of how lopsided the
    # deviations are. Clamping is the last step and only trims the tails.
    raw_mean = sum(raw.values()) / len(raw)
    weights = {hc: round(min(M_MAX, max(M_MIN, w / raw_mean)), 3) for hc, w in raw.items()}
    return weights
