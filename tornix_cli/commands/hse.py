"""`tornix hse` — Health & Safety («الأمن والسلامة») of a project, curated.

Everything runs as the signed-in user against `/api/v1/projects/:id/hse/...`: the platform decides who may
view (view_hse), manage (manage_hse) or act as the violation's assignee, so a refusal (403) is final.

Flow the app ships: inspection round → violation with a «before» photo → a «after» photo → closure request
(lands in «الطلبات» for the approver) → approval closes it → a manager may reopen it with a reason.
"""
from __future__ import annotations

import mimetypes
import os
import re
from datetime import datetime, timezone

import click

from ._helpers import client, show

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CATEGORIES = ["safety", "security", "environment", "personnel"]
STATUSES = ["OPEN", "CLOSURE_REQUESTED", "CLOSED"]
KINDS = ["near_miss", "incident", "lost_time"]
RESULTS = ["ok", "nc", "na"]
PHOTO_KINDS = ["before", "after"]
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _base(project_id: str) -> str:
    if not _UUID.match(project_id or ""):
        raise click.UsageError("PROJECT must be the project id (UUID); find it with `tornix projects list`.")
    return f"/api/v1/projects/{project_id}/hse"


def _violation_id(obj, project_id: str, ref: str) -> str:
    """A violation by id, or by its number («12»)."""
    if _UUID.match(ref):
        return ref
    if not ref.lstrip("#").isdigit():
        raise click.UsageError("VIOLATION is the violation id (UUID) or its number.")
    n = int(ref.lstrip("#"))
    res = client(obj).get(f"{_base(project_id)}/violations", params={"limit": 500}, envelope=True)
    for v in (res or {}).get("data", []):
        if v.get("number") == n:
            return v["id"]
    raise click.UsageError(f"no violation number {n} in this project.")


@click.group(name="hse", help="Health & Safety: inspections, violations (before/after photos), closure requests, incidents, plan, KPIs.")
def hse_group() -> None:
    pass


# ── reads ──────────────────────────────────────────────────────────────

@hse_group.command("access", help="What the caller may do in this project's HSE (view / manage / assignee).")
@click.argument("project_id")
@click.pass_obj
def hse_access(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/access"))


@hse_group.command("kpis", help="HSE KPI cards: days without lost time, near misses, open / awaiting-closure violations.")
@click.argument("project_id")
@click.pass_obj
def hse_kpis(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/kpis"))


@hse_group.command("summary", help="KPIs plus violation counts per status for one project.")
@click.argument("project_id")
@click.pass_obj
def hse_summary(obj, project_id):
    c, b = client(obj), _base(project_id)
    res = c.get(f"{b}/violations", params={"limit": 1}, envelope=True) or {}
    show(obj, {"access": c.get(f"{b}/access"), "kpis": c.get(f"{b}/kpis"),
               "violations_total": res.get("total"), "violations_by_status": res.get("counts")})


@hse_group.command("violations", help="List violations (newest first) with counts for the whole filter.")
@click.argument("project_id")
@click.option("--status", type=click.Choice(STATUSES), multiple=True)
@click.option("--severity", type=click.Choice(SEVERITIES), multiple=True)
@click.option("--category", type=click.Choice(CATEGORIES), multiple=True)
@click.option("--overdue", is_flag=True, help="Past the due date and not closed.")
@click.option("--mine", is_flag=True, help="Assigned to me or created by me.")
@click.option("--company", default=None, help="Responsible company contains…")
@click.option("--search", default=None)
@click.option("--limit", type=click.IntRange(1, 500), default=50)
@click.option("--offset", type=click.IntRange(0), default=0)
@click.pass_obj
def hse_violations(obj, project_id, status, severity, category, overdue, mine, company, search, limit, offset):
    params = {"status": ",".join(status) or None, "severity": ",".join(severity) or None,
              "category": ",".join(category) or None, "overdue": "true" if overdue else None,
              "mine": "true" if mine else None, "company": company, "search": search,
              "limit": limit, "offset": offset or None}
    res = client(obj).get(f"{_base(project_id)}/violations", params=params, envelope=True) or {}
    show(obj, {"total": res.get("total"), "counts": res.get("counts"), "violations": res.get("data", [])})


@hse_group.command("violation", help="One violation with its photos.")
@click.argument("project_id")
@click.argument("violation")
@click.option("--photo-urls", is_flag=True, help="Also fetch a signed link per photo.")
@click.pass_obj
def hse_violation(obj, project_id, violation, photo_urls):
    c, b = client(obj), _base(project_id)
    vid = _violation_id(obj, project_id, violation)
    v = c.get(f"{b}/violations/{vid}")
    if photo_urls and isinstance(v, dict):
        for p in v.get("photos", []):
            p["url"] = (c.get(f"{b}/violations/{vid}/photos/{p['id']}/url") or {}).get("url")
    show(obj, v)


@hse_group.command("inspections", help="Inspection rounds of the project.")
@click.argument("project_id")
@click.pass_obj
def hse_inspections(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/inspections"))


@hse_group.command("checklist", help="The default inspection checklist (keys + Arabic labels).")
@click.argument("project_id")
@click.pass_obj
def hse_checklist(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/inspections/default-checklist"))


@hse_group.command("incidents", help="Near misses / incidents / lost-time incidents.")
@click.argument("project_id")
@click.pass_obj
def hse_incidents(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/incidents"))


@hse_group.command("plan", help="The four-part HSE plan (safety, security, environment, personnel).")
@click.argument("project_id")
@click.pass_obj
def hse_plan(obj, project_id):
    show(obj, client(obj).get(f"{_base(project_id)}/plan"))


# ── writes ─────────────────────────────────────────────────────────────

@hse_group.command("violation-add", help="Record a violation (needs manage_hse).")
@click.argument("project_id")
@click.option("--title", required=True)
@click.option("--description", default=None)
@click.option("--location", default=None)
@click.option("--category", type=click.Choice(CATEGORIES), default=None)
@click.option("--severity", type=click.Choice(SEVERITIES), default=None)
@click.option("--assignee-id", default=None, help="A member of the project.")
@click.option("--company", default=None, help="Responsible company.")
@click.option("--due-date", default=None, help="YYYY-MM-DD")
@click.pass_obj
def hse_violation_add(obj, project_id, title, description, location, category, severity, assignee_id, company, due_date):
    body = {"title": title, "description": description, "location": location, "category": category,
            "severity": severity, "assignee_id": assignee_id, "responsible_company": company, "due_date": due_date}
    show(obj, client(obj).post(f"{_base(project_id)}/violations", json={k: v for k, v in body.items() if v is not None}))


@hse_group.command("violation-update", help="Change a violation (needs manage_hse; not on a closed one).")
@click.argument("project_id")
@click.argument("violation")
@click.option("--title", default=None)
@click.option("--description", default=None)
@click.option("--location", default=None)
@click.option("--category", type=click.Choice(CATEGORIES), default=None)
@click.option("--severity", type=click.Choice(SEVERITIES), default=None)
@click.option("--assignee-id", default=None)
@click.option("--company", default=None)
@click.option("--due-date", default=None)
@click.pass_obj
def hse_violation_update(obj, project_id, violation, title, description, location, category, severity, assignee_id, company, due_date):
    body = {"title": title, "description": description, "location": location, "category": category,
            "severity": severity, "assignee_id": assignee_id, "responsible_company": company, "due_date": due_date}
    body = {k: v for k, v in body.items() if v is not None}
    if not body:
        raise click.UsageError("give at least one field to change.")
    vid = _violation_id(obj, project_id, violation)
    show(obj, client(obj).patch(f"{_base(project_id)}/violations/{vid}", json=body))


@hse_group.command("photo-add", help="Upload a local image and register it as the violation's «before» or «after» photo.")
@click.argument("project_id")
@click.argument("violation")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--kind", type=click.Choice(PHOTO_KINDS), required=True)
@click.pass_obj
def hse_photo_add(obj, project_id, violation, path, kind):
    """Bytes go to `/storage/upload-direct` (bucket files, under the violation's prefix), then the photo is registered."""
    mime = mimetypes.guess_type(path)[0] or ""
    if not mime.startswith("image/"):
        raise click.UsageError("PATH must be an image.")
    c, b = client(obj), _base(project_id)
    vid = _violation_id(obj, project_id, violation)
    name = os.path.basename(path)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    storage_path = f"hse/{project_id}/violations/{vid}/{kind}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{safe}"
    with open(path, "rb") as fh:
        data = fh.read()
    resp = c._http.post("/api/v1/storage/upload-direct", params={"bucket": "files", "path": storage_path, "contentType": mime},
                        content=data, headers=c._headers({"Content-Type": mime}), timeout=120)
    if resp.status_code >= 400:
        raise c._to_error(resp)
    show(obj, c.post(f"{b}/violations/{vid}/photos", json={"kind": kind, "storage_path": storage_path, "file_name": name,
                                                           "mime_type": mime, "size_bytes": len(data), "source": "web"}))


@hse_group.command("request-closure", help="Ask to close a violation (assignee or manager). Needs ≥1 «after» photo id; the request lands in «الطلبات».")
@click.argument("project_id")
@click.argument("violation")
@click.option("--photo-id", "photo_ids", multiple=True, required=True, help="Id of an «after» photo (repeat).")
@click.option("--note", default=None)
@click.pass_obj
def hse_request_closure(obj, project_id, violation, photo_ids, note):
    vid = _violation_id(obj, project_id, violation)
    show(obj, client(obj).post(f"{_base(project_id)}/violations/{vid}/request-closure",
                               json={"photo_ids": list(photo_ids), **({"note": note} if note else {})}))


@hse_group.command("close", help="Close a violation directly (manage_hse). The normal path is request-closure + approval.")
@click.argument("project_id")
@click.argument("violation")
@click.pass_obj
def hse_close(obj, project_id, violation):
    vid = _violation_id(obj, project_id, violation)
    show(obj, client(obj).post(f"{_base(project_id)}/violations/{vid}/close", json={}))


@hse_group.command("reopen", help="Reopen a closed violation (manage_hse); a reason is required.")
@click.argument("project_id")
@click.argument("violation")
@click.option("--reason", required=True)
@click.pass_obj
def hse_reopen(obj, project_id, violation, reason):
    vid = _violation_id(obj, project_id, violation)
    show(obj, client(obj).post(f"{_base(project_id)}/violations/{vid}/reopen", json={"reason": reason}))


@hse_group.command("incident-add", help="Report a near miss / incident / lost-time incident.")
@click.argument("project_id")
@click.option("--kind", type=click.Choice(KINDS), required=True)
@click.option("--description", required=True)
@click.option("--occurred-at", default=None, help="ISO date-time (default: now).")
@click.pass_obj
def hse_incident_add(obj, project_id, kind, description, occurred_at):
    body = {"kind": kind, "description": description, **({"occurred_at": occurred_at} if occurred_at else {})}
    show(obj, client(obj).post(f"{_base(project_id)}/incidents", json=body))


@hse_group.command("inspection-add",
                   help="Record an inspection round. --item KEY=ok|nc|na[:note] overrides the default checklist; nc items open violations.")
@click.argument("project_id")
@click.option("--title", required=True)
@click.option("--location", default=None)
@click.option("--item", "items", multiple=True, help="Default-checklist key = result[:note] (repeat).")
@click.option("--notes", default=None)
@click.option("--severity", type=click.Choice(SEVERITIES), default=None, help="For the violations nc items open.")
@click.option("--assignee-id", default=None)
@click.option("--company", default=None)
@click.option("--due-date", default=None)
@click.option("--no-violations", is_flag=True, help="Do not open a violation per nc item.")
@click.pass_obj
def hse_inspection_add(obj, project_id, title, location, items, notes, severity, assignee_id, company, due_date, no_violations):
    c, b = client(obj), _base(project_id)
    body: dict = {"title": title}
    if items:
        checklist = {i["key"]: dict(i) for i in c.get(f"{b}/inspections/default-checklist") or []}
        for raw in items:
            key, _, rest = raw.partition("=")
            result, _, note = rest.partition(":")
            if key not in checklist or result not in RESULTS:
                raise click.UsageError(f"--item {raw!r}: KEY is one of {sorted(checklist)} and result one of {RESULTS}.")
            checklist[key]["result"] = result
            if note:
                checklist[key]["note"] = note
        body["checklist"] = list(checklist.values())
    for k, v in (("location", location), ("notes", notes), ("severity", severity), ("assignee_id", assignee_id),
                 ("responsible_company", company), ("due_date", due_date)):
        if v:
            body[k] = v
    if no_violations:
        body["create_violations"] = False
    show(obj, c.post(f"{b}/inspections", json=body))
