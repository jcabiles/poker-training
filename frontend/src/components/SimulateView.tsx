import { useCallback, useEffect, useRef, useState } from "react";

import {
  getSession,
  leaveSession,
  postHeroAction,
  postNextHand,
  postSimulateSession,
} from "../api/client";
import type { ActionType, SessionView } from "../api/types";
import SimActionBar from "./simulate/SimActionBar";
import SimEventLog from "./simulate/SimEventLog";
import SimLedger from "./simulate/SimLedger";
import SimShowdown from "./simulate/SimShowdown";
import SimTable from "./simulate/SimTable";

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

// The client's json<T>() throws Error("<url> -> <status>") on non-2xx, so a
// lost/ended session surfaces as a message ending "-> 404".
function isSessionNotFound(err: unknown): boolean {
  return err instanceof Error && / -> 404$/.test(err.message);
}

export default function SimulateView() {
  const [view, setView] = useState<SessionView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); // any in-flight action/deal
  const busyRef = useRef(false); // sync guard against click bursts
  const sessionIdRef = useRef<string | null>(null);

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
    setView(res);
  }, []);

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
      void run((id) =>
        postHeroAction(id, sizeBb != null ? { action, size_bb: sizeBb } : { action }),
      );
    },
    [run],
  );

  const nextHand = useCallback(() => {
    void run((id) => postNextHand(id));
  }, [run]);

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

  return (
    <section className="simulate">
      <div className="sim-topbar">
        <h1 className="sim-heading">Simulate</h1>
        {view && (
          <button
            type="button"
            className="btn sim-leave-btn"
            onClick={leaveTable}
            disabled={busy}
          >
            Leave table
          </button>
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
            <SimTable hand={hand} />

            {hand.is_hero_turn && (
              <SimActionBar
                legalActions={hand.legal_actions}
                disabled={busy}
                onDecide={decide}
              />
            )}

            {hand.hand_over && (
              <SimShowdown
                showdown={hand.showdown}
                seats={hand.seats}
                onNextHand={nextHand}
                dealing={busy}
              />
            )}

            {!hand.is_hero_turn && !hand.hand_over && (
              <p className="sim-waiting" role="status">
                Waiting on the table…
              </p>
            )}
          </div>

          <aside className="sim-side">
            <SimEventLog events={hand.events} />
            <SimLedger seats={hand.seats} />
          </aside>
        </div>
      ) : (
        !error && (
          <div className="panel simulate-empty" role="status">
            Taking a seat…
          </div>
        )
      )}
    </section>
  );
}
