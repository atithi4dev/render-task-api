# Task API

A tiny FastAPI service with 7 endpoints, built as a backend to put an MCP server in front of.
Data is in-memory and resets on restart (Render free tier also sleeps after inactivity).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Health check (no auth) |
| GET | /tasks | List tasks (filters: status, priority, search, limit) |
| POST | /tasks | Create a task |
| GET | /tasks/{id} | Get one task |
| PATCH | /tasks/{id} | Update fields / mark done |
| DELETE | /tasks/{id} | Delete a task |
| GET | /stats | Counts, open-by-priority, overdue IDs |

Interactive docs: `/docs`. OpenAPI JSON: `/openapi.json`.

## Auth
Send `X-API-Key: <key>`. Set the `API_KEY` env var to enable it. If unset, auth is off (local dev only).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# http://localhost:8000/docs
```

## Deploy on Render
1. Push this folder to a GitHub repo.
2. Render dashboard: New > Blueprint (uses render.yaml), or New > Web Service with:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Set env var `API_KEY` (the blueprint auto-generates one; copy it from the dashboard).
4. Your URL will look like `https://task-api-xxxx.onrender.com`.

## Try it
```bash
BASE=https://task-api-xxxx.onrender.com
KEY=your-api-key

curl $BASE/health
curl -H "X-API-Key: $KEY" "$BASE/tasks?status=open"
curl -X POST $BASE/tasks -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"title":"Call bank","due":"2026-10-03","priority":"high"}'
curl -X PATCH $BASE/tasks/<id> -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"status":"done"}'
curl -H "X-API-Key: $KEY" $BASE/stats
```

## Suggested MCP tool mapping (for later)
**MCP server 1: task management**
- `list_tasks` -> GET /tasks
- `create_task` -> POST /tasks
- `update_task` (incl. complete) -> PATCH /tasks/{id}
- `delete_task` -> DELETE /tasks/{id}

**MCP server 2: insights**
- `get_task` -> GET /tasks/{id}
- `get_task_stats` -> GET /stats
- `search_tasks` -> GET /tasks?search=...
