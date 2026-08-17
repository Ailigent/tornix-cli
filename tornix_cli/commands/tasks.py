from __future__ import annotations

import json

import click

from ._helpers import client, show


def _json(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.UsageError(f"invalid JSON for --data: {e}")


@click.group(name="tasks", help="Tasks (curated). Tasks are scoped to a project.")
def tasks_group() -> None:
    pass


@tasks_group.command("list", help="List tasks in a project.")
@click.option("--project", "project_id", required=True, help="Project id (tasks are nested).")
@click.option("--status", default=None)
@click.option("--limit", type=int, default=None, help="Maximum number of tasks to return.")
@click.pass_obj
def tasks_list(obj, project_id, status, limit):
    params = {}
    if status:
        params["status"] = status
    if limit is not None:
        params["limit"] = limit
    # The backend calls the task title `name`; `title` does not exist on a task.
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}/tasks", params=params or None),
         columns=["id", "name", "status", "assignee_id", "due_date"])


@tasks_group.command("get", help="Get a task by id.")
@click.argument("task_id")
@click.pass_obj
def tasks_get(obj, task_id):
    show(obj, client(obj).get(f"/api/v1/tasks/{task_id}"))


@tasks_group.command("create", help="Create a task in a project.")
@click.option("--project", "project_id", required=True)
@click.option("--title", required=True,
              help="Task title (leading/trailing whitespace is trimmed).")
@click.option("--assignee", "assignee_id", default=None)
@click.option("--sprint", "sprint_id", default=None,
              help="Sprint id to place the task in (agile projects).")
@click.option("--board-column", "board_column_id", default=None,
              help="Board column id (agile projects). If omitted with --sprint, "
                   "defaults to the first To Do column.")
@click.pass_obj
def tasks_create(obj, project_id, title, assignee_id, sprint_id, board_column_id):
    """Create a task. When --sprint is given without --board-column, the first
    To Do column is fetched automatically so the task appears on the Kanban
    board immediately (not stranded in the DB with board_column_id=NULL)."""
    # Guard against minting an untitled task from a blank/whitespace title.
    title = title.strip()
    if not title:
        raise click.UsageError("--title must not be blank.")
    # CreateTaskDto requires `name`; the flag stays --title for compatibility.
    body = {"name": title}
    if assignee_id:
        body["assignee_id"] = assignee_id
    if sprint_id:
        body["sprint_id"] = sprint_id
        if not board_column_id:
            # Auto-resolve the first To Do column so the task lands on the board.
            c = client(obj)
            try:
                board = c.get(f"/api/v1/agile/projects/{project_id}/board")
                cols = board.get("columns", []) if isinstance(board, dict) else []
                for col in cols:
                    if col.get("kind") != "done" and col.get("name", "").lower() in ("to do", "todo"):
                        board_column_id = col["id"]
                        break
                if not board_column_id and cols:
                    # Fallback: first non-done, non-proposed column.
                    for col in cols:
                        if col.get("kind") not in ("done", "proposed"):
                            board_column_id = col["id"]
                            break
            except Exception:
                pass  # Non-agile project or board not available — leave it unset.
        if board_column_id:
            body["board_column_id"] = board_column_id
    show(obj, client(obj).post(f"/api/v1/projects/{project_id}/tasks", json=body))


@tasks_group.command("update", help="Update a task (PUT) with a JSON body.")
@click.argument("task_id")
@click.option("--data", "raw", required=True, help="JSON body (PUT).")
@click.pass_obj
def tasks_update(obj, task_id, raw):
    show(obj, client(obj).put(f"/api/v1/tasks/{task_id}", json=_json(raw)))


@tasks_group.command("comment", help="Add a comment to a task.")
@click.argument("task_id")
@click.option("--text", required=True)
@click.pass_obj
def tasks_comment(obj, task_id, text):
    show(obj, client(obj).post(f"/api/v1/tasks/{task_id}/comments", json={"content": text}))
