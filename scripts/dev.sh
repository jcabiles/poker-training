#!/usr/bin/env bash
# Single-command dev: boots backend (:8008) in background, waits for health,
# then runs frontend (:5173) in foreground. Backend is killed on exit.
set -euo pipefail
cd "$(dirname "$0")/.."

cd backend
.venv/bin/uvicorn app.main:app --reload --port 8008 &
BACKEND_PID=$!
cd ..

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "== waiting for backend on :8008 =="
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8008/api/v1/health >/dev/null 2>&1; then
    echo "== backend up =="
    break
  fi
  sleep 0.5
done

cd frontend
npm run dev
