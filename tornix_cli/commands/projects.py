from __future__ import annotations

import json

import click

from ._helpers import client, show


@click.group(name="projects", help="Projects (curated).")
def projects_group() -> None:
    pass


# talon: caller-scoped projects list
_LIST_COLUMNS = ["project_id", "name", "status", "budget"]


def _caller_id(cl):
    """The signed-in user's id — who "mine" means."""
    me = cl.get("/api/v1/auth/me")
    for holder in (me, me.get("user") if isinstance(me, dict) else None):
        if isinstance(holder, dict):
            for k in ("id", "user_id", "userId"):
                if holder.get(k):
                    return str(holder[k])
    return None


def _is_mine(project, uid):
    """True when the caller is on this project — a member, or the one who made it."""
    if uid is None:
        return True
    if str(project.get("created_by") or "") == uid:
        return True
    for m in project.get("members") or []:
        if isinstance(m, dict) and str(m.get("user_id") or "") == uid:
            return True
    return False


def _all_pages(cl, params):
    """Every project, not page one. The endpoint defaults to limit=20 and says so in
    `meta`; the CLI used to hand that first page back as the whole answer."""
    rows, page = [], 1
    while True:
        q = dict(params)
        q["page"] = page
        body = cl.get("/api/v1/projects", params=q, envelope=True)
        if isinstance(body, list):
            return body
        if not isinstance(body, dict):
            return rows
        chunk = body.get("data")
        rows.extend(chunk if isinstance(chunk, list) else [])
        meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
        total_pages = meta.get("totalPages")
        if not isinstance(total_pages, int) or page >= total_pages or page >= 50:
            return rows
        page += 1


@projects_group.command(
    "list",
    help="List YOUR projects (the ones you are a member of). Add --all for every "
         "project in the organization.",
)
@click.option("--limit", type=int, default=None, help="Cap the rows returned.")
@click.option("--status", default=None)
@click.option("--all", "org_wide", is_flag=True, default=False,
              help="Every project in the organization, not just yours.")
@click.pass_obj
def projects_list(obj, limit, status, org_wide):
    cl = client(obj)
    params = {"limit": 100}
    if status:
        params["status"] = status
    rows = _all_pages(cl, params)
    if not org_wide:
        uid = _caller_id(cl)
        rows = [p for p in rows if _is_mine(p, uid)]
    if limit is not None:
        rows = rows[:limit]
    show(obj, rows, columns=_LIST_COLUMNS)


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
