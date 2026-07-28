from __future__ import annotations

import json

import click

from ._helpers import client, show


@click.group(name="projects", help="Projects (curated).")
def projects_group() -> None:
    pass


@projects_group.command("list", help="List projects in the active organization.")
@click.option("--limit", type=int, default=None)
@click.option("--status", default=None)
@click.pass_obj
def projects_list(obj, limit, status):
    params = {}
    if limit is not None:
        params["limit"] = limit
    if status:
        params["status"] = status
    show(obj, client(obj).get("/api/v1/projects", params=params or None),
         columns=["project_id", "name", "status", "budget"])


@projects_group.command("get", help="Get a project by id.")
@click.argument("project_id")
@click.pass_obj
def projects_get(obj, project_id):
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}"))


@projects_group.command("health", help="Get a project's health summary.")
@click.argument("project_id")
@click.pass_obj
def projects_health(obj, project_id):
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}/health"))


@projects_group.command("members", help="List a project's members.")
@click.argument("project_id")
@click.pass_obj
def projects_members(obj, project_id):
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}/members"),
         columns=["id", "name", "role"])


@projects_group.command("create", help="Create a project.")
@click.option("--name", required=True,
              help="Project name (leading/trailing whitespace is trimmed).")
@click.option("--description", default=None)
@click.pass_obj
def projects_create(obj, name, description):
    # Guard against minting an untitled project from a blank/whitespace name.
    name = name.strip()
    if not name:
        raise click.UsageError("--name must not be blank.")
    body = {"name": name}
    if description:
        body["description"] = description
    show(obj, client(obj).post("/api/v1/projects", json=body))


@projects_group.command("update", help="Update a project (PUT) with a JSON body.")
@click.argument("project_id")
@click.option("--data", "raw", required=True, help="JSON body (PUT).")
@click.pass_obj
def projects_update(obj, project_id, raw):
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.UsageError(f"invalid JSON for --data: {e}")
    show(obj, client(obj).put(f"/api/v1/projects/{project_id}", json=payload))
