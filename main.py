"""Tiny Task API: a simple application layer to put an MCP server in front of.

Storage is in-memory (resets on restart), which is fine for testing.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

API_KEY = os.environ.get("API_KEY")  # if unset, auth is disabled (local dev)

app = FastAPI(title="Task API", version="1.0.0")


def require_key(x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


Status = Literal["open", "done"]
Priority = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = ""
    due: Optional[str] = Field(default=None, description="ISO date, e.g. 2026-10-05")
    priority: Priority = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    notes: Optional[str] = None
    due: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make(title, notes="", due=None, priority="medium", status="open"):
    tid = uuid.uuid4().hex[:8]
    return tid, {
        "id": tid, "title": title, "notes": notes, "due": due,
        "priority": priority, "status": status, "created_at": now(),
    }


TASKS: dict = {}
for t in [
    ("Send invoice to Ravi", "", "2026-10-05", "high", "open"),
    ("Book train tickets", "Lucknow to Delhi", "2026-10-10", "medium", "open"),
    ("Review pull request", "", None, "low", "done"),
]:
    k, v = make(*t)
    TASKS[k] = v


@app.get("/health")
def health():
    """Public health check (used by Render)."""
    return {"status": "ok", "time": now()}


@app.get("/tasks", dependencies=[Depends(require_key)])
def list_tasks(
    status: Optional[Status] = None,
    priority: Optional[Priority] = None,
    search: Optional[str] = Query(default=None, description="Substring match on title/notes"),
    limit: int = Query(default=20, ge=1, le=100),
):
    items = list(TASKS.values())
    if status:
        items = [t for t in items if t["status"] == status]
    if priority:
        items = [t for t in items if t["priority"] == priority]
    if search:
        s = search.lower()
        items = [t for t in items if s in t["title"].lower() or s in t["notes"].lower()]
    items.sort(key=lambda t: t["created_at"], reverse=True)
    return {"count": len(items[:limit]), "tasks": items[:limit]}


@app.post("/tasks", status_code=201, dependencies=[Depends(require_key)])
def create_task(body: TaskCreate):
    tid, task = make(body.title, body.notes, body.due, body.priority)
    TASKS[tid] = task
    return task


@app.get("/tasks/{task_id}", dependencies=[Depends(require_key)])
def get_task(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, "Task not found. Call GET /tasks to list valid IDs.")
    return TASKS[task_id]


@app.patch("/tasks/{task_id}", dependencies=[Depends(require_key)])
def update_task(task_id: str, body: TaskUpdate):
    if task_id not in TASKS:
        raise HTTPException(404, "Task not found. Call GET /tasks to list valid IDs.")
    TASKS[task_id].update(body.model_dump(exclude_unset=True))
    return TASKS[task_id]


@app.delete("/tasks/{task_id}", dependencies=[Depends(require_key)])
def delete_task(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, "Task not found. Call GET /tasks to list valid IDs.")
    return {"deleted": TASKS.pop(task_id)["id"]}


@app.get("/stats", dependencies=[Depends(require_key)])
def stats():
    total = len(TASKS)
    done = sum(1 for t in TASKS.values() if t["status"] == "done")
    by_priority = {p: 0 for p in ("low", "medium", "high")}
    for t in TASKS.values():
        if t["status"] == "open":
            by_priority[t["priority"]] += 1
    today = datetime.now(timezone.utc).date().isoformat()
    overdue = [t["id"] for t in TASKS.values()
               if t["status"] == "open" and t["due"] and t["due"] < today]
    return {"total": total, "open": total - done, "done": done,
            "open_by_priority": by_priority, "overdue_ids": overdue}
