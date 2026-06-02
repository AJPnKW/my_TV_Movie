# deployment/api/api_contract_draft.md

Base: /api/v1

Endpoints:
- GET /health
- GET /media
- GET /media/{id}
- POST /media/import-json
- GET /watch-state
- PUT /watch-state/{media_item_id}
- GET /sync/queue
- POST /sync/trakt/pull
- POST /sync/trakt/push
- POST /sync/reconcile
- GET /media-library/inventory
- POST /media-library/scan
- POST /media-library/qa
- POST /media-library/remux
- GET /runtime/config
- PUT /runtime/profile

Rules:
- Server mode handles writes.
- Static JSON mode remains read-only fallback.
- All writes create audit/sync history.
- No silent loss of watch actions.
