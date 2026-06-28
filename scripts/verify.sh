#!/usr/bin/env bash
# Backend verify: tests + real boot (lifespan migrations) + route probes.
# Frontend is verified separately (vite build + Playwright on the running app).
set -euo pipefail
cd "$(dirname "$0")/../backend"

echo "== pytest =="
.venv/bin/python -m pytest -q

echo "== boot + probe routes =="
.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as c:  # triggers lifespan -> alembic upgrade head (incl srs_item)
    assert c.get("/api/v1/health").status_code == 200, "health"
    for mode in ("random", "review", "leak_focus"):
        r = c.get(f"/api/v1/drill/next?mode={mode}")
        assert r.status_code == 200, f"next {mode}"
        body = r.json()
        assert body["spot"]["street"] == "preflop", f"spot {mode}"
        assert body["grid"], f"grid {mode}"  # per-hand coloring present

    spot = c.get("/api/v1/drill/next").json()["spot"]
    g = c.post("/api/v1/drill/grade", json={"spot": spot, "action": {"action": "fold"}})
    assert g.status_code == 200 and "is_mixed" in g.json(), "grade"

    assert c.get("/api/v1/stats/summary").status_code == 200, "summary"
    assert c.get("/api/v1/stats/leaks").status_code == 200, "leaks"

    paths = c.get("/openapi.json").json()["paths"]
    for p in ("/api/v1/drill/next", "/api/v1/drill/grade", "/api/v1/stats/leaks", "/api/v1/stats/summary"):
        assert p in paths, f"openapi missing {p}"

    # facing-aggression nodes are sampled + gradeable
    seen = set()
    for _ in range(80):
        seen.update(c.get("/api/v1/drill/next?mode=random").json()["spot"]["node_context"])
    assert {"vs_3bet", "vs_4bet"} <= seen, f"missing facing-aggression nodes: {sorted(seen)}"

    # exploit mode serves archetype spots; random/baseline pools never leak them
    ex = c.get("/api/v1/drill/next?mode=exploit").json()["spot"]
    assert ex["villain_type"] in {"calling_station", "nit", "lag", "passive_fish"}, "exploit villain missing"
    for _ in range(40):
        assert c.get("/api/v1/drill/next?mode=random").json()["spot"]["villain_type"] is None, "random leaked an exploit spot"

    # --- Phase 2a: postflop c-bet + foundational quizzes ---
    pf = c.get("/api/v1/drill/next?mode=postflop").json()
    assert pf["spot"]["street"] == "flop" and len(pf["spot"]["board"]) == 3, "postflop spot not a flop"
    assert pf["grid"] == {}, "grid should be empty postflop"
    pg = c.post("/api/v1/drill/grade", json={"spot": pf["spot"], "action": {"action": "check"}})
    assert pg.status_code == 200 and pg.json()["leak_category"] == 200, "postflop grade (FLOP_CBET)"

    tq = c.get("/api/v1/drill/quiz/next?kind=texture").json()
    assert tq["kind"] == "texture" and len(tq["board"]) == 3, "texture quiz item"
    tr = c.post("/api/v1/drill/quiz/grade", json={"kind": "texture", "board": tq["board"], "choice": "wet"})
    assert tr.status_code == 200 and tr.json()["expected"] in ("dry", "medium", "wet"), "texture quiz grade"

    eq = c.get("/api/v1/drill/quiz/next?kind=equity").json()
    assert eq["kind"] == "equity" and eq["hero_cards"] and eq["villain_range"], "equity quiz item"
    er = c.post("/api/v1/drill/quiz/grade", json={
        "kind": "equity", "board": eq["board"], "hero_cards": eq["hero_cards"],
        "villain_range": eq["villain_range"], "estimate_pct": 50.0,
    })
    assert er.status_code == 200 and er.json()["expected"].endswith("%"), "equity quiz grade"

    for p in ("/api/v1/drill/quiz/next", "/api/v1/drill/quiz/grade"):
        assert p in paths, f"openapi missing {p}"
print("BACKEND VERIFY OK")
PY
