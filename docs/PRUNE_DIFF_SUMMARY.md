# Prune Diff Summary (Human-readable)

Date: 2025-10-14

## Added
- Backend: ENABLE_DEBUG_ENDPOINTS flag; gates ingest debug routes.
- Frontend: ENABLE_DEBUG_ENDPOINTS flag; gates /api/_debug/* routes.
- Docs: docs/PRUNE_REPORT.md (inventory + plan), this file.

## Changed
- backend/main.py: mount ingest_debug only when ENABLE_DEBUG_ENDPOINTS=true; added /youtube/save endpoint.
- frontend/app/api/youtube/flashcards/route.ts: added PUT to save deck via backend.
- frontend/components/YTToCards.tsx: Save-to-deck wired to new API.
- backend/env.example: documented ENABLE_DEBUG_ENDPOINTS.
- frontend/env.local: documented ENABLE_DEBUG_ENDPOINTS.

## Removed
- frontend/components/ThemeToggle.tsx (duplicate; unused — replaced by components/theme/ThemeToggle.tsx)

## Notes
- No changes to PDF upload/generation/study flows.
- YouTube ingest hardening preserved; debug endpoints now off by default.
