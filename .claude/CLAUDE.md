# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

Local NLHE (No-Limit Hold'em) training web app. Monorepo:
- `backend/` — FastAPI + pure domain core (`app/domain/`, no web/DB imports, enforced by `tests/test_domain_purity.py`) + SQLite/Alembic.
- `frontend/` — React + Vite + strict TypeScript; API types generated from `openapi.json`.
- `content/` — strategy content packs (versioned JSON) + JSON schema. Strategy lives in data, not code.
- `docs/` — research, roadmap, specs, tickets.

See `README.md` for setup, architecture, and status.

## Commands
- Backend tests + boot probe: `./scripts/verify.sh`
- Backend lint: `cd backend && ruff check .`
- Frontend typecheck/build: `cd frontend && npm run typecheck && npm run build`

## Conventions
- Grading flows through one async `StrategyProvider` interface — keep it swappable (heuristic today, solver later).
- Results are always frequency + EV, never boolean.
- Don't put web/DB imports in `app/domain/`.

## Security

`.claude/settings.json` is a hardened sandbox config:
- OS sandbox enabled (`allowUnsandboxedCommands: false`) — Bash and subprocesses are confined.
- Network allowlist: `pypi.org`, `files.pythonhosted.org`. Widen `sandbox.network.allowedDomains` for new workflows — don't disable the sandbox.
- Writes restricted to project dir; deny list blocks `.env`, secrets, `~/.ssh`, `~/.aws`, keychains.

Restart Claude Code after editing `.claude/settings.json` to reload it.
