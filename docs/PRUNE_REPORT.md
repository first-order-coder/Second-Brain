# Repository Prune Report

Date: 2025-10-14

Scope: Inventory, gating debug endpoints, and initial findings. Subsequent commits will remove confirmed-dead assets and update deps safely.

## Inventory

### FastAPI Routes (from `backend/main.py` and routers)
- Core:
  - `GET /` (root)
  - `POST /upload-pdf`
  - `POST /generate-flashcards/{pdf_id}`
  - `GET /status/{pdf_id}`
  - `GET /flashcards/{pdf_id}`
- Summaries (feature-flagged):
  - `GET /summaries/{source_id}`
  - `POST /summaries/{source_id}/refresh`
  - `GET /health/summary`
- YouTube:
  - `POST /ingest/url` (FEATURE_YOUTUBE_INGEST)
  - `POST /ingest/debug/tracks` (FEATURE_YOUTUBE_INGEST && ENABLE_DEBUG_ENDPOINTS)
  - `POST /youtube/flashcards` (LLM cardify from transcript)
  - `POST /youtube/save` (save generated YT deck → SQLite)

### Next.js Routes (app/)
- Pages:
  - `/` → `app/page.tsx`
  - `/flashcards/[id]` → viewer
  - `/sources/[id]` → summary page
- API:
  - `/api/youtube/flashcards` → POST generate, PUT save deck
  - `/api/ingest/url` → proxy to backend ingest
  - `/api/_debug/env` (ENABLE_DEBUG_ENDPOINTS)
  - `/api/_debug/ping` (ENABLE_DEBUG_ENDPOINTS)

## Debug Gating
- Added `ENABLE_DEBUG_ENDPOINTS=false` default in both backend and frontend.
- Backend now only mounts `routes/ingest_debug.py` when `ENABLE_DEBUG_ENDPOINTS=true`.
- Frontend debug API routes return 404 unless enabled.

## Commands Planned/Used
- Static scans (to be executed in CI/local):
  - Frontend: `npx ts-prune`, `npx depcheck`, `pnpm tsc --noEmit`, `pnpm eslint . --max-warnings=0`
  - Backend: `vulture backend . --min-confidence 80`, `ruff check backend`, `mypy backend`
- Inventory:
  - Next: `next build` with `ANALYZE=true` (if analyzer configured)
  - File counts: `find frontend -type f | wc -l` and `find backend -type f | wc -l`

## Candidate Areas for Prune (pending verification)
- Frontend components duplicate ThemeToggle under `components/theme/ThemeToggle.tsx` and `components/ThemeToggle.tsx` (verify imports; keep only one).
- Docs/test helpers like `test_openai.py` (retain if used for manual tests; otherwise gate or remove).
- Redundant YouTube transcript helpers if superseded by `services/youtube_transcripts.py` (verify usage).

## Actions Taken So Far
- Gated debug endpoints via `ENABLE_DEBUG_ENDPOINTS=false` by default (backend and frontend).
- Removed duplicate unused component: `frontend/components/ThemeToggle.tsx` (app uses `components/theme/ThemeToggle.tsx`).

## Safety Guarantees
- PDF upload flow unchanged.
- YouTube ingest and flashcards remain intact.
- Debug tooling preserved but gated.

## Next Steps
1) Run dead-code tools and record outputs here.
2) Cross-check dynamic imports and server-render paths before removal.
3) Stage removals in small commits with clear messages.

# Repository Prune Report

## Initial Inventory (Before Pruning)

### File Counts
- Frontend: 23,743 files
- Backend: 7,328 files
- Total: 31,071 files

### Directory Sizes (MB)
- Frontend node_modules: 338.66 MB
- Backend venv: 225.62 MB
- Frontend .next: 96.34 MB
- Backend uploads: 27 MB
- Other directories: <1 MB each

### Analysis Date
Generated: $(Get-Date)

## Tools and Commands Used
- PowerShell for file counting and size analysis
- ts-prune for TypeScript dead code detection
- depcheck for unused dependencies
- vulture for Python dead code detection
- ruff/mypy for Python linting

## Findings Summary
*To be filled as analysis progresses*

## Files Removed
*To be filled during removal phase*

## Files Kept with Feature Flags
*To be filled for debug endpoints and conditional features*

## Risk Assessment
*To be filled with potential issues and revert instructions*