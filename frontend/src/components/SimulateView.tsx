import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  getSession,
  getVillainRange,
  leaveSession,
  postHeroAction,
  postNextHand,
  postSimulateSession,
} from "../api/client";
import type { ActionType, GradeView, SessionView, VillainRangeView } from "../api/types";
import SimActionBar from "./simulate/SimActionBar";
import SimEventLog from "./simulate/SimEventLog";
import SimLedger from "./simulate/SimLedger";
import SimRangeChart from "./simulate/SimRangeChart";
import SimRecap from "./simulate/SimRecap";
import SimShowdown from "./simulate/SimShowdown";
import SimSpeedPicker, { type SimSpeed } from "./simulate/SimSpeedPicker";
import SimWatchToggle from "./simulate/SimWatchToggle";
import SimStreetReport from "./simulate/SimStreetReport";
import SimTable from "./simulate/SimTable";
import SimVillainRange from "./simulate/SimVillainRange";

// Simulate S9 — the playable, persistent table. Hero acts via predetermined
// -sizing buttons; bots resolve instantly (server-side, within each request),
// so every rendered view sits at a hero-decision boundary or hand-over. Stacks
// carry over, a per-seat net-BB ledger tracks P&L, and a browser reload
// restores the exact live decision point via a persisted session_id.
//
// PokerTable stays the drill/quiz render primitive; the felt here is the
// simulate-scoped SimTable (same room, richer per-seat data S9 owns). No
// villain hole cards ever render except at showdown (structural on the wire —
// re-checked in SimTable/SimShowdown).

const STORAGE_KEY = "simulate.session_id";
const SPEED_KEY = "simulate.speed";
const WATCH_KEY = "simulate.watch";

// The client's json<T>() throws Error("<url> -> <status>") on non-2xx, so a
// lost/ended session surfaces as a message ending "-> 404".
function isSessionNotFound(err: unknown): boolean {
  return err instanceof Error && / -> 404$/.test(err.message);
}

// ── Client-side pacing (S11) ────────────────────────────────────────────────
// The server resolves every bot action synchronously and returns them in one
// `events` batch; there is no server pacing hook. Pacing is a pure client-side
// replay: a shared `stagedIndex` counts how many of the batch's events are
// "revealed" so far, and drives BOTH the log (which lines are visible) and the
// felt (which seats show their resolved fold/all-in/chips state). The index
// walks up on a timer whose per-step delay depends on the speed setting.

// Base bot delay window at "normal" (ms). Each step picks a uniform-random
// value in [MIN, MAX] so the table's rhythm reads human, never metronomic.
const NORMAL_MIN = 500;
const NORMAL_MAX = 1500;
// "fast" runs the same window proportionally quicker; "instant" = no delay.
const FAST_FACTOR = 0.4;

function readSpeed(): SimSpeed {
  try {
    const v = window.localStorage.getItem(SPEED_KEY);
    if (v === "normal" || v === "fast" || v === "instant") return v;
  } catch {
    /* private-mode storage — fall through to default */
  }
  return "normal";
}

// Watch-folded-hands setting (client-only, localStorage). ON (default) plays the
// villains out to showdown after a hero fold; OFF skips straight to the next
// hand. Absent/garbage storage ⇒ default ON.
function readWatch(): boolean {
  try {
    return window.localStorage.getItem(WATCH_KEY) !== "off";
  } catch {
    return true;
  }
}

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

// Delay before revealing the NEXT staged event, given the effective speed.
// reduced-motion collapses to instant regardless of the stored setting.
function stepDelayMs(speed: SimSpeed): number {
  if (speed === "instant" || prefersReducedMotion()) return 0;
  const span = NORMAL_MAX - NORMAL_MIN;
  const base = NORMAL_MIN + Math.random() * span;
  return speed === "fast" ? base * FAST_FACTOR : base;
}

export default function SimulateView() {
  const [view, setView] = useState<SessionView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); // any in-flight action/deal
  const busyRef = useRef(false); // sync guard against click bursts
  const sessionIdRef = useRef<string | null>(null);

  // Speed setting (client-only, localStorage). Drives the pacing delays. Held
  // in a ref too so the running playback timer reads the LIVE speed on each step
  // — a mid-batch change takes effect on the next reveal without rewinding.
  const [speed, setSpeed] = useState<SimSpeed>(readSpeed);
  const speedRef = useRef<SimSpeed>(speed);
  const changeSpeed = useCallback((next: SimSpeed) => {
    speedRef.current = next;
    setSpeed(next);
    try {
      window.localStorage.setItem(SPEED_KEY, next);
    } catch {
      /* private-mode storage — setting still applies this session */
    }
  }, []);

  // Watch-folded-hands toggle. Held in a ref too because `decide` reads it at
  // fold-CLICK time (a mid-playout flip must not retroactively change the hand
  // in flight — it takes effect on the NEXT fold).
  const [watch, setWatch] = useState<boolean>(readWatch);
  const watchRef = useRef<boolean>(watch);
  const changeWatch = useCallback((next: boolean) => {
    watchRef.current = next;
    setWatch(next);
    try {
      window.localStorage.setItem(WATCH_KEY, next ? "on" : "off");
    } catch {
      /* private-mode storage — setting still applies this session */
    }
  }, []);

  // Pacing state: how many of the current batch's events are revealed. The felt
  // (SimTable) and the log (SimEventLog) both read this so a seat never shows
  // its resolved state before the log narrates that seat's action. Held in a
  // ref too so the recursive step timer reads the live value without re-arming.
  const [stagedIndex, setStagedIndex] = useState(0);
  const stagedRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  const setStaged = useCallback((n: number) => {
    stagedRef.current = n;
    setStagedIndex(n);
  }, []);

  // ── S10 grading state ─────────────────────────────────────────────────────
  // The just-taken decision's verdict, shown as a seal on the hero pod. The hero
  // acts by their own click (not part of the bot playback), so the badge may
  // appear immediately — but it's cleared the moment the next action starts and
  // whenever a fresh hand deals, so it never bleeds onto a later decision.
  const [heroBadge, setHeroBadge] = useState<GradeView | null>(null);

  // Tier accumulation (refuter reality): persisted recap rows carry NO
  // verdict/reasoning text — only the live `last_grade` on each action response
  // does. So we stash each hand's live grades by ordinal here and merge them
  // back into the hand-over recap, so mistakes/blunders show their "why" on the
  // live path. Reset per hand (a new hand_no). A ref (not state): it's read at
  // render time from the current view and never needs to trigger its own render.
  const tiersByOrdinal = useRef<Map<number, GradeView>>(new Map());
  // "session_id#hand_no" keys — session-scoped so a 404-recovery into a fresh
  // session (which restarts at hand 1) can't reuse the previous hand's state.
  const gradedHandNo = useRef<string | null>(null);
  // The hand we've already refetched the report for, so a restore/re-render
  // of an already-finished hand doesn't refetch on every adopt.
  const reportedHandNo = useRef<string | null>(null);

  // Bumped whenever a hand completes so the all-time per-street report refetches
  // its aggregate. Also nudged on mount by the report's own effect.
  const [reportKey, setReportKey] = useState(0);

  // ── Villain-range (V2) ──────────────────────────────────────────────────────
  // Cumulative narrated-action bookkeeping for the range endpoint's lockstep
  // `through_action` param (the WHOLE-hand count of non-POST actions narrated so
  // far — hero's own + every villain's). The endpoint maps it to the domain's
  // POST-inclusive index (`domain_index = 2 + through_action`), so an off-by-one
  // here shows up as a chart one action ahead of / behind the log.
  //
  // `narratedBase` = the count of narrated actions BEFORE the current batch's
  // staged events; `narratedCount = narratedBase + stagedIndex`. Within one hand
  // every re-adopt is a hero action (next-hand/initial deal start a new
  // hand_no), and the hero's own action is itself exactly one narrated row that
  // precedes this batch's events — so the recurrence is: new hand ⇒ base 0;
  // same-hand hero action ⇒ base = prevBase + prevEventCount + 1. Held in a ref
  // (read at fetch time) plus mirrored context for reset detection.
  const narratedBaseRef = useRef(0);
  const narratedHandRef = useRef<string | null>(null);
  const prevEventCountRef = useRef(0);

  // Which villain seat's estimated-range panel is open (one at a time), plus the
  // resolved estimate + its fetch status. openRangeSeat drives the SimTable
  // button pressed-state and the panel mount; the rest is the panel's data.
  const [openRangeSeat, setOpenRangeSeat] = useState<number | null>(null);
  const [villainRange, setVillainRange] = useState<VillainRangeView | null>(null);
  const [rangeLoading, setRangeLoading] = useState(false);
  const [rangeErrored, setRangeErrored] = useState(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const events = view?.hand?.events ?? null;
  const eventCount = events?.length ?? 0;

  // Playback engine: whenever a new batch arrives, replay it one event at a time
  // on the speed-scaled timer. A fresh batch (new view) restarts from 0; the
  // timer walks stagedIndex up to eventCount, then stops. instant/reduced-motion
  // yields a 0ms first step so the whole batch reveals in one frame. Any new
  // batch or unmount clears the pending timer (no interval leaks).
  useEffect(() => {
    clearTimer();
    if (eventCount === 0) {
      setStaged(0);
      return;
    }

    // Instant / reduced-motion: reveal the whole batch in one commit — no
    // per-step timer, and no one-frame flash of the pre-reveal (all-live) felt.
    if (stepDelayMs(speedRef.current) === 0) {
      setStaged(eventCount);
      return;
    }

    setStaged(0);
    const step = () => {
      const next = stagedRef.current + 1;
      setStaged(next);
      if (next < eventCount) {
        timerRef.current = window.setTimeout(step, stepDelayMs(speedRef.current));
      } else {
        timerRef.current = null;
      }
    };
    timerRef.current = window.setTimeout(step, stepDelayMs(speedRef.current));

    return clearTimer;
    // Restart the batch only when a NEW events array arrives (fresh object
    // identity per view). Speed is read live from speedRef inside `step`, so a
    // mid-batch speed change takes effect on the next step WITHOUT rewinding —
    // that's why `speed` is deliberately not a dependency of this effect.
  }, [events, eventCount, clearTimer, setStaged]);

  const playing = eventCount > 0 && stagedIndex < eventCount;

  // Lockstep map for the felt: position → the 1-based staged-index threshold at
  // or above which that seat's LAST action in this batch has been narrated. A
  // seat reveals its resolved status (fold-dim / all-in / chips-in-front) only
  // once stagedIndex reaches its threshold — so the felt never shows a seat's
  // final state before the log line that explains it. Positions absent from the
  // batch (hero, seats settled before it) get no entry → revealed immediately.
  const revealAt = useMemo(() => {
    const m = new Map<string, number>();
    if (events) events.forEach((e, i) => m.set(e.position, i + 1));
    return m;
  }, [events]);

  // Adopt a session view: hold its id (both in a ref for callbacks and in
  // localStorage for reload restore) and render its hand.
  const adopt = useCallback((res: SessionView) => {
    sessionIdRef.current = res.session_id;
    try {
      window.localStorage.setItem(STORAGE_KEY, res.session_id);
    } catch {
      // Private-mode / disabled storage: play still works this session, only
      // reload-restore is lost. Non-fatal.
    }

    // S10 grade bookkeeping. A new (session, hand_no) pair resets the per-hand
    // tier accumulator — hand_no ALONE is not a safe key: every session starts
    // at hand 1, so a mid-hand-1 404 recovery into a fresh session would
    // otherwise bleed session A's "why" text into session B's recap (final-gate
    // refuter med-1). Then stash this response's live grade (if any) by ordinal
    // so the hand-over recap can merge in the tiers the persisted rows lack,
    // and surface it as the hero-pod badge.
    const hand = res.hand;
    const gradeKey = `${res.session_id}#${hand.hand_no}`;
    if (gradedHandNo.current !== gradeKey) {
      tiersByOrdinal.current = new Map();
      gradedHandNo.current = gradeKey;
    }
    const grade = hand.last_grade ?? null;
    if (grade) tiersByOrdinal.current.set(grade.ordinal, grade);
    setHeroBadge(grade);

    // A finished hand's decisions have persisted — refetch the all-time report
    // (once per hand, so a reload of an already-over hand doesn't re-fetch).
    if (hand.hand_over && reportedHandNo.current !== gradeKey) {
      reportedHandNo.current = gradeKey;
      setReportKey((k) => k + 1);
    }

    // Villain-range narrated-count bookkeeping (see the refs' comment). A fresh
    // hand resets the base to 0; a same-hand re-adopt is always a hero action,
    // whose single narrated row precedes this batch's events — so the new base
    // is the previous batch's fully-revealed total (prevBase + prevEventCount)
    // plus that one hero row. The count is only ever CONSUMED while playback is
    // active (see `rangeThrough`); on a settled/restored turn the full history
    // is requested instead, so a mid-hand reload (events=[], no hero action)
    // never needs an accurate base.
    const newBatch = res.hand.events?.length ?? 0;
    if (narratedHandRef.current !== gradeKey) {
      narratedHandRef.current = gradeKey;
      narratedBaseRef.current = 0;
      // Any hand transition closes an open villain-range panel — including
      // hand endings whose hand_over view was never adopted (the hero-fold
      // shortcut jumps straight to the next deal; without this a panel open on
      // a NON-folding villain silently carried across the hand boundary —
      // villain-range refuter med-1).
      setOpenRangeSeat(null);
    } else {
      narratedBaseRef.current = narratedBaseRef.current + prevEventCountRef.current + 1;
    }
    prevEventCountRef.current = newBatch;
    // Reset the staged index ATOMICALLY with the base bump: the playback
    // effect also resets it, but that runs a flush later — in between,
    // rangeThrough would read newBase + the OLD batch's terminal stagedIndex
    // and fire one inflated lockstep request (refuter low-1).
    setStaged(0);

    setView(res);
  }, [setStaged]);

  const clearStored = useCallback(() => {
    sessionIdRef.current = null;
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* non-fatal */
    }
  }, []);

  // Create a fresh session and adopt its first hand.
  const startSession = useCallback(async () => {
    adopt(await postSimulateSession());
  }, [adopt]);

  // Mount: try to restore a stored session; on 404 (missing/ended) clear it and
  // deal a fresh one. StrictMode double-invokes effects in dev; the cancelled
  // flag keeps the later resolve from clobbering state.
  useEffect(() => {
    let cancelled = false;
    setError(null);
    const stored = (() => {
      try {
        return window.localStorage.getItem(STORAGE_KEY);
      } catch {
        return null;
      }
    })();

    const boot = async () => {
      if (stored) {
        try {
          const res = await getSession(stored);
          if (!cancelled) adopt(res);
          return;
        } catch (e) {
          if (!isSessionNotFound(e)) throw e;
          // Stale/ended session — fall through to a fresh one.
          clearStored();
        }
      }
      if (!cancelled) await startSession();
    };

    boot().catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    });
    return () => {
      cancelled = true;
    };
  }, [adopt, clearStored, startSession]);

  // Shared runner for hero actions / deals: a sync ref guard (state is async —
  // a same-tick burst would slip past a state-only check), 404 recovery, and
  // error surfacing. `op` returns the new view (or starts fresh on a lost
  // session).
  const run = useCallback(
    async (op: (id: string) => Promise<SessionView>) => {
      if (busyRef.current) return;
      const id = sessionIdRef.current;
      if (!id) {
        // No live session (first-visit race) — create one instead.
        busyRef.current = true;
        setBusy(true);
        setError(null);
        try {
          await startSession();
        } catch (e) {
          setError(e instanceof Error ? e.message : String(e));
        } finally {
          busyRef.current = false;
          setBusy(false);
        }
        return;
      }
      busyRef.current = true;
      setBusy(true);
      setError(null);
      try {
        try {
          adopt(await op(id));
        } catch (e) {
          if (isSessionNotFound(e)) {
            clearStored();
            await startSession();
          } else {
            throw e;
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [adopt, clearStored, startSession],
  );

  const decide = useCallback(
    (action: ActionType, sizeBb?: number | null) => {
      // Hero-fold skip (Watch OFF only): the hero has no more decisions this
      // hand, so with watching disabled there is nothing to pace — skip the bot
      // playback entirely and deal the next hand in the same turn. Cancel any
      // residual timer first so a fold mid-playback of a prior batch can't leave
      // a stray reveal running. Read from the ref so a mid-playout toggle only
      // affects the NEXT fold. With Watch ON we fall through to the normal path
      // below, which adopts the fold response so the villains narrate to
      // showdown (+ recap) exactly like a hand played out.
      if (action === "fold" && !watchRef.current) {
        clearTimer();
        void run(async (id) => {
          // The fold response ends the hand but is never adopted (we jump
          // straight to the next deal) — without the bump here the per-street
          // report went stale after every fold-ended hand (final-gate refuter
          // high-1: adopt() only sees the NEXT hand, whose hand_over is false).
          const folded = await postHeroAction(id, { action });
          const foldedKey = `${folded.session_id}#${folded.hand.hand_no}`;
          if (folded.hand.hand_over && reportedHandNo.current !== foldedKey) {
            reportedHandNo.current = foldedKey;
            setReportKey((k) => k + 1);
          }
          return postNextHand(id);
        });
        return;
      }
      void run((id) =>
        postHeroAction(id, sizeBb != null ? { action, size_bb: sizeBb } : { action }),
      );
    },
    [run, clearTimer],
  );

  const nextHand = useCallback(() => {
    // Dealing a fresh hand after hand_over must cancel any residual playback
    // timer from the just-finished hand's final batch before the new view lands.
    clearTimer();
    void run((id) => postNextHand(id));
  }, [run, clearTimer]);

  // Leave the table: end it server-side, clear storage, deal a fresh session so
  // the tab keeps working. A lost session (already 404) is treated as success.
  const leaveTable = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    const id = sessionIdRef.current;
    try {
      if (id) {
        try {
          await leaveSession(id);
        } catch (e) {
          if (!isSessionNotFound(e)) throw e;
        }
      }
      clearStored();
      await startSession();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }, [clearStored, startSession]);

  const hand = view?.hand ?? null;

  // Merge the finished hand's persisted recap with the live tiers we accumulated
  // this hand (persisted rows lack verdict/reasoning text; the live grades carry
  // it). Match by ordinal; the live entry wins where present so misses show
  // their "why" on the live path. On a mid-session reload the accumulator is
  // empty, so this degrades to the numbers-only persisted rows — accepted v1.
  const mergedRecap = useMemo<GradeView[]>(() => {
    const rows = hand?.recap ?? [];
    return rows.map((r) => tiersByOrdinal.current.get(r.ordinal) ?? r);
    // hand?.recap identity changes per view; the accumulator is a ref read live.
  }, [hand?.recap]);

  // Pacing gate (S11 lockstep philosophy — nothing on screen may lead the log):
  // during staged bot playback the hand may already be hand_over server-side,
  // but the recap and the felt's final grades must stay hidden until playback
  // completes. The hero's OWN badge is exempt — the hero acted by their own
  // click, not the bot playback, so it may show immediately.
  const revealHandEnd = !playing;

  // ── Villain-range panel: open/close + lockstep fetch (V2) ───────────────────
  // The narrated count that gates the estimate. While playback runs, it's the
  // per-hand cumulative count of narrated actions the log has revealed so far
  // (base + stagedIndex) — passed as `through_action` so the chart conditions on
  // exactly the visible prefix and NEVER leads the log. When NOT playing the log
  // is fully caught up (or this is a restored/settled turn), so we request the
  // full history (undefined) — which also sidesteps a mid-hand reload's
  // untracked base.
  const narratedCount = narratedBaseRef.current + stagedIndex;
  const rangeThrough = playing ? narratedCount : undefined;

  // The open seat's live SeatView (server truth) and its STAGED reveal state —
  // the same staged-fold computation SimTable's button uses, so the panel closes
  // in lockstep with the fold narration, not the instant server-truth flips.
  const openSeat =
    openRangeSeat != null ? hand?.seats.find((s) => s.seat_index === openRangeSeat) : undefined;
  const openSeatStagedFolded =
    openSeat != null &&
    (() => {
      const threshold = revealAt.get(openSeat.position);
      const revealed = threshold == null || stagedIndex >= threshold;
      return revealed && openSeat.status === "folded";
    })();

  const toggleRange = useCallback((seatIndex: number) => {
    setOpenRangeSeat((prev) => (prev === seatIndex ? null : seatIndex));
  }, []);
  const closeRange = useCallback(() => setOpenRangeSeat(null), []);

  // Auto-close: the open villain's staged fold narrates, or the hand ends
  // (hand_over reveals real cards — an estimate beside the truth is noise). Both
  // are lockstep-aware: hand_over's felt reveal is itself gated behind playback,
  // and the fold uses the staged computation above.
  useEffect(() => {
    if (openRangeSeat == null) return;
    if (hand?.hand_over || openSeat == null || openSeatStagedFolded) {
      setOpenRangeSeat(null);
    }
  }, [openRangeSeat, hand?.hand_over, openSeat, openSeatStagedFolded]);

  // Fetch on open + REFETCH as the narrated count advances while open (lockstep
  // narrowing). Stale-response guard mirrors SimRangeChart: each request is
  // stamped with the (seat, through) live at fire time; a late response for a
  // superseded stamp is discarded. Fire-and-forget — never blocks the table.
  const rangeStampRef = useRef<string>("");
  useEffect(() => {
    if (openRangeSeat == null || view == null) return;
    const stamp = `${view.session_id}#${openRangeSeat}#${rangeThrough ?? "full"}`;
    rangeStampRef.current = stamp;
    let cancelled = false;
    setRangeLoading(true);
    setRangeErrored(false);
    getVillainRange(view.session_id, openRangeSeat, rangeThrough)
      .then((res) => {
        if (cancelled || rangeStampRef.current !== stamp) return;
        setVillainRange(res);
        setRangeLoading(false);
      })
      .catch(() => {
        if (cancelled || rangeStampRef.current !== stamp) return;
        setVillainRange(null);
        setRangeErrored(true);
        setRangeLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Refetch on: open seat change, count advance (lockstep narrowing), or a
    // 404-recovery into a fresh session (session_id).
  }, [openRangeSeat, rangeThrough, view]);

  // Drop stale panel data the instant the open seat changes / closes, so the
  // next open never flashes the previous villain's grid before its fetch lands.
  useEffect(() => {
    setVillainRange(null);
    setRangeErrored(false);
  }, [openRangeSeat]);

  return (
    <section className="simulate">
      <div className="sim-topbar">
        <h1 className="sim-heading">Simulate</h1>
        {view && (
          <div className="sim-topbar-controls">
            <SimWatchToggle watch={watch} onChange={changeWatch} />
            <SimSpeedPicker speed={speed} onChange={changeSpeed} />
            <button
              type="button"
              className="btn sim-leave-btn"
              onClick={leaveTable}
              disabled={busy}
            >
              Leave table
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="panel bad-bg">
          Error: {error}. Is the backend running on :8008?
        </div>
      )}

      {hand ? (
        <div className="sim-layout">
          <div className="sim-main">
            <SimTable
              hand={hand}
              stagedIndex={stagedIndex}
              revealAt={revealAt}
              lastGrade={heroBadge}
              openRangeSeat={openRangeSeat}
              onToggleRange={toggleRange}
            />

            {/* Villain-range panel (V2) — one open villain at a time, keyed by
                the open seat so a seat switch remounts a fresh grid. Sits under
                the felt so it doesn't crowd the seat pods. Auto-closes on the
                villain's staged fold / hand_over (effects above). */}
            {openSeat && !openSeatStagedFolded && !hand.hand_over && (
              <SimVillainRange
                key={openSeat.seat_index}
                position={openSeat.position}
                range={villainRange}
                loading={rangeLoading}
                errored={rangeErrored}
                onClose={closeRange}
              />
            )}

            {hand.is_hero_turn && (
              <SimActionBar
                legalActions={hand.legal_actions}
                disabled={busy || playing}
                onDecide={decide}
              />
            )}

            {/* Point-of-need baseline range chart (C2). Preflop hero turns only,
                and never during bot playback (pacing). The identity key must
                change PER DECISION POINT, not per hand: two hero preflop turns
                in one hand (open → villain 3-bets → hero faces it) would
                otherwise share a key and keep the FIRST decision's chart on
                screen for the second (chart refuter high-1). pot_bb strictly
                grows between consecutive preflop hero decisions, so it is the
                per-decision discriminator; is_hero_turn added nothing (always
                true when mounted). */}
            {hand.is_hero_turn && hand.street === "preflop" && !playing && view && (
              <SimRangeChart
                sessionId={view.session_id}
                identityKey={`${view.session_id}#${hand.hand_no}#${hand.pot_bb}`}
                heroCards={hand.hero.hole_cards}
              />
            )}

            {/* Hand-over surfaces gate on playback: the recap and settlement
                slip appear only once the bot playback finishes (revealHandEnd),
                so nothing leads the log. */}
            {hand.hand_over && revealHandEnd && (
              <>
                <SimShowdown
                  showdown={hand.showdown}
                  seats={hand.seats}
                  onNextHand={nextHand}
                  dealing={busy}
                />
                <SimRecap recap={mergedRecap} />
              </>
            )}

            {!hand.is_hero_turn && !hand.hand_over && (
              <p className="sim-waiting" role="status">
                Waiting on the table…
              </p>
            )}
          </div>

          <aside className="sim-side">
            <SimEventLog events={hand.events} stagedIndex={stagedIndex} />
            <SimStreetReport refreshKey={reportKey} />
            <SimLedger seats={hand.seats} />
          </aside>
        </div>
      ) : (
        !error && (
          <div className="sim-empty-shell">
            <div className="panel simulate-empty" role="status">
              Taking a seat…
            </div>
            {/* The all-time report is session-independent — show it even before
                the first hand adopts (spec: visible with or without a live
                session). */}
            <aside className="sim-side sim-side-empty">
              <SimStreetReport refreshKey={reportKey} />
            </aside>
          </div>
        )
      )}
    </section>
  );
}
