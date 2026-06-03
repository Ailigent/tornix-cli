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
@click.pass_obj
def tasks_list(obj, project_id, status):
    params = {}
    if status:
        params["status"] = status
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}/tasks", params=params or None),
         columns=["id", "title", "status", "assignee_id", "due_date"])


@tasks_group.command("get", help="Get a task by id.")
@click.argument("task_id")
@click.pass_obj
def tasks_get(obj, task_id):
    show(obj, client(obj).get(f"/api/v1/tasks/{task_id}"))


@tasks_group.command("create", help="Create a task in a project.")
@click.option("--project", "project_id", required=True)
@click.option("--title", required=True)
@click.option("--assignee", "assignee_id", default=None)
@click.pass_obj
def tasks_create(obj, project_id, title, assignee_id):
    body = {"title": title}
    if assignee_id:
        body["assignee_id"] = assignee_id
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
