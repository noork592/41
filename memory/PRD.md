# Factory Order Management ERP — PRD

## Original Problem Statement
Full-stack Factory Order Management ERP (React + FastAPI + MongoDB): user roles, order tracking,
dispatch management, customer ledgers, reporting, and transport route optimisation with railway
level-crossing (phatak) avoidance. Restored from GitHub repo `anhad592/40`.

## Architecture
- Frontend: React (`/app/frontend`), Tailwind, shadcn/ui, react-router-dom, craco, leaflet maps, i18n.
- Backend: FastAPI (`/app/backend/server.py`), Motor/MongoDB, JWT auth, bcrypt.
- Env (LOCAL ONLY, repo has no .env): backend `.env` MONGO_URL, DB_NAME, JWT_SECRET, EMERGENT_LLM_KEY;
  frontend `.env` REACT_APP_BACKEND_URL. Login: admin / admin123 (seeded on fresh DB).

## Transport route avoidance (Daily Report → Transport tab, `TransportRoutes.jsx`)
- `POST /api/transport/optimize` returns multiple route options (Shortest / Nearest first / As selected)
  each annotated with a `crossings` count, plus an "Avoid railway crossing" option.
- Crossing detection: known OSM `level_crossing` nodes + user-marked phataks + **geometric intersection
  of the route polyline with the rail LINE geometry** (`_rail_line_hits`), with flyover forgiveness.
- Rail/bridge geometry sourced from Overpass (often DOWN) with OSM map-API small-tile fallback
  (`_rail_data_near`); full-bbox OSM 400s in dense cities so tiles are used.

## Feature Log
- 2026-09-27 (fix + feature): "Avoid railway crossing" was still crossing the rail.
  - Root cause 1: only discrete level_crossing NODES were detected → added rail-LINE intersection
    detection (`_seg_intersect`, `_rail_line_hits`, `_on_flyover`) merged into `_crossings_on`;
    `rail_ways` now returned by fetchers and threaded through `_build_avoidance_route`.
  - Root cause 2: in the user's area Overpass is down and OSM has no usable grade-separated flyover
    OSRM can route over, so automatic detour genuinely can't avoid the crossing.
  - SOLUTION (user-driven, deterministic): **"Mark flyover"** — new endpoints
    `GET/POST/DELETE /api/flyovers` (db.flyovers). Optimize forces the avoid route through user flyovers
    (distance-cap-exempt, top-priority via-points) and forgives the crossing there (80m tolerance).
    Frontend: green "Mark flyover" toggle (testid `tr-flyover-mode`) + ⤴ markers, click-to-delete.
  - Verified by testing agent: marking flyovers near the crossings dropped the Avoid route from 2 → 1
    crossing; CRUD works; no 500s.

## Next
- Optional: auto-suggest flyover placement; warn on route summary when crossings > 0.
