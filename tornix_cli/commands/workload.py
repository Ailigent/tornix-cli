"""Team workload — the ONE Workload figure the Tornix UI shows on «توازن الأحمال».

WHY THIS MODULE EXISTS
----------------------
Tornix computes a person's workload in exactly one place on the server
(`WorkloadService`, NestJS `src/modules/work-pulse/workload.*`):

    Workload % = (hours logged in the period
                  + remaining hours of open tasks due in the period)
                 ÷ working hours in the period (their schedule − holidays − approved leave)

with the organization's own bands (default: < 60 available, ≤ 90 balanced,
≤ 110 high, above — or more than 3 overdue tasks — over capacity). A task with
no estimate is never counted as zero: the figure is then a LOWER BOUND ("≥").

An agent that re-derived any of that from `project_tasks` rows would publish a
second, different number for the same person. So every command here reads the
server's figure as is, and adds nothing to it but labels.

READ-ONLY, ON PURPOSE
---------------------
There is no `transfer` / `reassign` command. Moving work between people is a
manager's decision taken in the app, behind a confirmation that shows both
people's load before → after and every warning; the server also refuses those
routes outright for an agent token. `preview` is the strongest thing an agent
may do: it asks the server what a move WOULD do and writes nothing.
"""
from __future__ import annotations

import click

from ._helpers import client, show

BASE = "/api/v1/team-insights"

#: The app's route for the load-balance tab (where a manager actually moves work).
TAB_ROUTE = "/dashboard/team?tab=workload"


def _figure(w: dict | None) -> dict:
    """Server snapshot → the flat row an agent reads. Labels only, no maths
    beyond the capacity left, which is shown exactly as the app shows it."""
    if not w:
        return {"workload_pct": None, "figure": "no data", "band": None}
    pct = w.get("pct")
    status = w.get("status")
    if pct is None:
        label = "no working hours in this period"
    elif status == "lower_bound":
        label = f"≥ {round(pct)}% (some tasks have no estimate — at least this much)"
    elif status == "approximate":
        label = f"≈ {round(pct)}% (some remaining hours are the person's average)"
    else:
        label = f"{round(pct)}%"
    cap = w.get("capacity_hours") or 0
    used = (w.get("logged_hours") or 0) + (w.get("remaining_hours") or 0)
    return {
        "workload_pct": pct,
        "figure": label,
        "exact": status == "measured",
        "status": status,
        "band": w.get("band"),
        "capacity_hours": cap,
        "logged_hours": w.get("logged_hours"),
        "remaining_hours": w.get("remaining_hours"),
        "free_hours": round(max(cap - used, 0), 1),
        "open_tasks": w.get("open_tasks"),
        "overdue_tasks": w.get("overdue_tasks"),
        "unestimated_tasks": w.get("unestimated_tasks"),
        "approximate_tasks": w.get("approximate_tasks"),
        "period": f"{w.get('period_start')} → {w.get('period_end')}",
        "weeks": w.get("weeks"),
    }


def _period(month: str | None) -> dict:
    if month is None:
        return {}
    m = month.strip()
    if len(m) != 7 or m[4] != "-" or not (m[:4] + m[5:]).isdigit() or not 1 <= int(m[5:]) <= 12:
        raise click.UsageError("--month must be YYYY-MM.")
    return {"month": m}


@click.group(name="workload",
             help="Team workload — the app's single Workload figure (read-only, curated).")
def workload_group() -> None:
    pass


@workload_group.command("team", help="Every person's Workload the caller may see (admin: org; PM: their projects).")
@click.option("--project-id", default=None, help="One project's team only.")
@click.option("--month", default=None, help="YYYY-MM (default: the current month).")
@click.option("--band", type=click.Choice(["available", "balanced", "high", "over"]), default=None,
              help="Only people in this band.")
@click.pass_obj
def workload_team(obj, project_id, month, band):
    """`GET /team-insights/workload`. An employee gets `viewer: none` and an
    empty list — say so, never guess the numbers some other way."""
    data = client(obj).get(f"{BASE}/workload", params={"project_id": project_id, **_period(month)})
    rows = []
    for m in (data or {}).get("members", []):
        row = {"user_id": m.get("user_id"), "name": m.get("name"), "job_title": m.get("job_title"),
               **_figure(m.get("workload"))}
        if band and row.get("band") != band:
            continue
        rows.append(row)
    show(obj, {
        "viewer": (data or {}).get("viewer"),
        "scope": (data or {}).get("scope"),
        "thresholds": (data or {}).get("thresholds"),
        "projects": (data or {}).get("projects"),
        "where_to_act": TAB_ROUTE,
        "members": rows,
    })


@workload_group.command("person", help="One person's Workload and open tasks with their remaining hours.")
@click.argument("user_id")
@click.option("--project-id", default=None, help="Only tasks of this project.")
@click.option("--month", default=None, help="YYYY-MM (default: the current month).")
@click.pass_obj
def workload_person(obj, user_id, project_id, month):
    data = client(obj).get(f"{BASE}/workload/{user_id}/tasks",
                           params={"project_id": project_id, **_period(month)})
    show(obj, {
        "user_id": (data or {}).get("user_id"),
        "workload": _figure((data or {}).get("workload")),
        "tasks": (data or {}).get("tasks", []),
    })


@workload_group.command("suggestions",
                        help="The engine's own rebalancing suggestions (Team insights) — who, which task, to whom, why.")
@click.option("--project-id", default=None, help="One project's team only.")
@click.pass_obj
def workload_suggestions(obj, project_id):
    """The SAME plans the manager sees in the Team insights strip. Relay them;
    never build your own — the engine already excludes started / blocked /
    critical-path / unestimated tasks, checks skills, leave and the receiver
    ceiling, and ranks the candidates."""
    data = client(obj).get(BASE, params={"project_id": project_id})
    out = []
    for i in (data or {}).get("insights", []):
        plan = i.get("plan") or {}
        out.append({
            "kind": i.get("kind"),
            "person": (i.get("subject") or {}).get("name"),
            "person_id": (i.get("subject") or {}).get("user_id"),
            "workload": _figure(i.get("workload")),
            "moves": [{
                "task": (l.get("task") or {}).get("name"),
                "task_id": (l.get("task") or {}).get("id"),
                "project": (l.get("task") or {}).get("project_name"),
                "remaining_hours": (l.get("task") or {}).get("remaining_hours"),
                "to": ((l.get("candidate") or {}).get("person") or {}).get("name"),
                "to_id": ((l.get("candidate") or {}).get("person") or {}).get("user_id"),
                "owner_before_after": [l.get("owner_before_pct"), l.get("owner_after_pct")],
                "receiver_before_after": [(l.get("candidate") or {}).get("workload_pct"),
                                          (l.get("candidate") or {}).get("after_pct")],
                "skills": ((l.get("candidate") or {}).get("skill") or {}).get("status"),
                "why": [r.get("key") for r in l.get("reasons", [])],
            } for l in plan.get("tasks", [])],
            "not_suggested": plan.get("excluded"),
        })
    show(obj, {"viewer": (data or {}).get("viewer"), "where_to_act": TAB_ROUTE, "insights": out})


@workload_group.command("preview",
                        help="What moving tasks WOULD do (before → after, warnings). Writes nothing.")
@click.option("--from", "from_user", required=True, help="Current owner's user id.")
@click.option("--to", "to_user", required=True, help="Receiver's user id.")
@click.option("--task", "task_ids", multiple=True, required=True, help="Task id (repeat, at most 20).")
@click.option("--month", default=None, help="YYYY-MM (default: the current month).")
@click.pass_obj
def workload_preview(obj, from_user, to_user, task_ids, month):
    """`POST /team-insights/transfer/preview` — the server's numbers for a
    hypothetical move. The manager makes the move in the app (`where_to_act`);
    an agent cannot (the move routes refuse agent tokens)."""
    if len(task_ids) > 20:
        raise click.UsageError("at most 20 tasks per move.")
    body = {"from_user_id": from_user, "to_user_id": to_user, "task_ids": list(task_ids), **_period(month)}
    data = client(obj).post(f"{BASE}/transfer/preview", json=body)
    show(obj, {**(data or {}), "applied": False, "where_to_act": TAB_ROUTE})


@workload_group.command("check",
                        help="Before assigning: each person's load in the task window before → after, leave, first free slot, alternatives. Writes nothing.")
@click.option("--task", "task_ids", multiple=True, help="Task id (repeat for several — their hours add up).")
@click.option("--project-id", default=None, help="For a task not created yet.")
@click.option("--user", "user_ids", multiple=True, help="Candidate user id (repeat). Default: the project's members.")
@click.option("--hours", type=float, default=None, help="Estimate of a task not created yet.")
@click.option("--due", default=None, help="Due date YYYY-MM-DD (a draft, or to try another date).")
@click.option("--start", default=None, help="Start date YYYY-MM-DD.")
@click.option("--add", "mode_add", is_flag=True, help="Joins the people already on the task (default: takes it over).")
@click.pass_obj
def workload_check(obj, task_ids, project_id, user_ids, hours, due, start, mode_add):
    """`POST /team-insights/assignment-check` — the same check every assignment screen runs.
    Relay it: who fits, who would go above the ceiling, the first free window, the
    alternatives. You never assign — the manager does, in the app."""
    if not task_ids and not project_id:
        raise click.UsageError("--task or --project-id is required.")
    body = {
        "task_ids": list(task_ids) or None,
        "project_id": project_id,
        "user_ids": list(user_ids) or None,
        "estimated_hours": hours,
        "due_date": due,
        "start_date": start,
        "mode": "add" if mode_add else "replace",
    }
    data = client(obj).post(f"{BASE}/assignment-check", json={k: v for k, v in body.items() if v is not None})
    show(obj, {**(data or {}), "applied": False, "where_to_act": TAB_ROUTE})


@workload_group.command("calendar",
                        help="Resource calendar: person × day — capacity, hours booked, leave, holidays (≤ 6 weeks).")
@click.option("--from", "from_", required=True, help="YYYY-MM-DD")
@click.option("--to", "to_", required=True, help="YYYY-MM-DD")
@click.option("--project-id", default=None)
@click.pass_obj
def workload_calendar(obj, from_, to_, project_id):
    data = client(obj).get(f"{BASE}/resource-calendar", params={"from": from_, "to": to_, "project_id": project_id})
    show(obj, data)


@workload_group.command("sprint-preview",
                        help="Who would take each unassigned sprint item (balanced / round robin) — a preview, writes nothing.")
@click.argument("sprint_id")
@click.option("--strategy", type=click.Choice(["balanced", "round_robin"]), default="balanced", show_default=True)
@click.pass_obj
def workload_sprint_preview(obj, sprint_id, strategy):
    data = client(obj).post(f"{BASE}/sprint-auto-assign/preview", json={"sprint_id": sprint_id, "strategy": strategy})
    show(obj, {**(data or {}), "applied": False,
               "note": "Applying is the manager's step in the sprint panel; the assistant cannot apply it."})


@workload_group.command("requests", help="Assignment requests: asked of me (inbox) or that I asked (outbox).")
@click.option("--box", type=click.Choice(["inbox", "outbox"]), default="inbox", show_default=True)
@click.pass_obj
def workload_requests(obj, box):
    show(obj, client(obj).get(f"{BASE}/assignment-requests", params={"box": box}))
