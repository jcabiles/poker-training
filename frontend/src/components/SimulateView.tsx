import { useCallback, useEffect, useRef, useState } from "react";

import { postSimulateHand, postSimulateSession } from "../api/client";
import type { SimulateHandView, Spot } from "../api/types";
import PokerTable from "./PokerTable";

// Simulate S1 — walking skeleton. A dealt 9-max hand renders on the existing
// felt table (hero cards face-up, villains face-down, one dealer chip). No
// betting, chips, or persistence. Session is created lazily on first visit and
// held in component state; a reload starts a fresh session (fine in S1).

// Synthetic-Spot adapter (refuter finding): PokerTable's sole prop is a full
// Spot and it dereferences spot.game.stakes.sb / spot.board / spot.pot_bb etc.
// unguarded — a bare players/hero payload neither typechecks nor runs. So we
// build a complete Spot from the hand view with the pinned neutral values. The
// adapter lives ENTIRELY here; PokerTable.tsx is untouched. Optional Spot
// fields (spr, facing, villain_type, hero_range, villain_range, srs_signature)
// are omitted — only required fields get a neutral literal that typechecks.
function toSpot(hand: SimulateHandView): Spot {
  return {
    game: { stakes: { sb: 0.5, bb: 1 }, table_size: 9 },
    street: "preflop",
    board: [],
    pot_bb: 0,
    hero: hand.hero,
    players: hand.players,
    effective_stack_bb: 100,
    to_act: hand.hero.position,
    legal_actions: [],
    // Non-empty so PokerTable's "{ctx} · {stakes}" header has no orphan separator.
    node_context: ["cash"],
    limper_count: 0,
    action_history: [],
  };
}

// The client's json<T>() throws Error("<url> -> <status>") on non-2xx, so a
// lost session (e.g. backend restart) surfaces as a message ending "-> 404".
function isSessionNotFound(err: unknown): boolean {
  return err instanceof Error && / -> 404$/.test(err.message);
}

export default function SimulateView() {
  const [hand, setHand] = useState<SimulateHandView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dealing, setDealing] = useState(false);
  const dealingRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);

  // Create a fresh session and adopt its first hand.
  const startSession = useCallback(async () => {
    const res = await postSimulateSession();
    sessionIdRef.current = res.session_id;
    setHand(res.hand);
  }, []);

  // Lazy session create on mount. StrictMode double-invokes effects in dev;
  // the cancelled flag keeps the later resolve from clobbering state.
  useEffect(() => {
    let cancelled = false;
    setError(null);
    startSession().catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    });
    return () => {
      cancelled = true;
    };
  }, [startSession]);

  // "Next hand": deal on the current session; if the session was lost (404),
  // transparently create a fresh one so the tab keeps working after a restart.
  const nextHand = useCallback(async () => {
    // Ref guard: state updates are async, so a same-tick click burst would slip
    // past a state-only check and deal several hands per user intent.
    if (dealingRef.current) return;
    dealingRef.current = true;
    setDealing(true);
    setError(null);
    try {
      const id = sessionIdRef.current;
      if (!id) {
        await startSession();
        return;
      }
      try {
        setHand(await postSimulateHand(id));
      } catch (e) {
        if (isSessionNotFound(e)) {
          await startSession();
        } else {
          throw e;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      dealingRef.current = false;
      setDealing(false);
    }
  }, [startSession]);

  return (
    <section className="simulate">
      <div className="simulate-bar">
        <span className="simulate-count">
          Hand <span className="simulate-count-no">{hand ? hand.hand_no : "—"}</span>
        </span>
        <button
          type="button"
          className="btn btn-primary"
          onClick={nextHand}
          disabled={dealing}
        >
          Next hand
        </button>
      </div>

      {error && (
        <div className="panel bad-bg">
          Error: {error}. Is the backend running on :8008?
        </div>
      )}

      {hand ? (
        <PokerTable spot={toSpot(hand)} />
      ) : (
        !error && <div className="panel simulate-empty">Dealing the first hand…</div>
      )}
    </section>
  );
}
