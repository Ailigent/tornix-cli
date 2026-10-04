"""`tornix workload` — the agent reads the server's ONE Workload figure.

Guards three things: the numbers are relayed, never re-derived; a lower bound
stays a lower bound ("≥"), never an exact-looking number; and there is no
command that moves a task.
"""
import json

import httpx
from click.testing import CliRunner

from tornix_cli.__main__ import cli
from tornix_cli.client import TornixClient
from tornix_cli.commands.workload import workload_group
from tornix_cli.config import Config

ORG = "11111111-1111-1111-1111-111111111111"
SARA = "22222222-2222-2222-2222-222222222222"
OMAR = "33333333-3333-3333-3333-333333333333"
TASK = "44444444-4444-4444-4444-444444444444"

W_SARA = {"pct": 137.1, "status": "lower_bound", "band": "over", "capacity_hours": 210,
          "logged_hours": 24, "remaining_hours": 264, "open_tasks": 17, "overdue_tasks": 4,
          "unestimated_tasks": 2, "approximate_tasks": 0, "period_start": "2026-10-01",
          "period_end": "2026-10-31", "weeks": []}
W_OMAR = {**W_SARA, "pct": 23.0, "status": "measured", "band": "available", "logged_hours": 0,
          "remaining_hours": 48.3, "overdue_tasks": 0, "unestimated_tasks": 0}


def _run(args, handler):
    cfg = Config(api_url="https://x.test", api_key="tk", org_id=ORG)
    obj = {"config": cfg, "client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}
    res = CliRunner().invoke(workload_group, args, obj=obj, catch_exceptions=False)
    return res, json.loads(res.output) if res.output.strip().startswith(("{", "[")) else None


def _recorder():
    calls = []

    def handler(req):
        calls.append({"method": req.method, "path": req.url.path, "query": dict(req.url.params),
                      "body": json.loads(req.content) if req.content else None})
        p = req.url.path
        if p == "/api/v1/team-insights/workload":
            return httpx.Response(200, json={"data": {
                "viewer": "admin", "scope": "team", "projects": [],
                "thresholds": {"available_below_pct": 60, "balanced_max_pct": 90, "high_max_pct": 110,
                               "over_overdue_tasks": 3, "receiver_max_after_pct": 90},
                "members": [{"user_id": SARA, "name": "Sara", "job_title": None, "workload": W_SARA},
                            {"user_id": OMAR, "name": "Omar", "job_title": None, "workload": W_OMAR}]}})
        if p == f"/api/v1/team-insights/workload/{SARA}/tasks":
            return httpx.Response(200, json={"data": {"user_id": SARA, "workload": W_SARA, "tasks": [{"id": TASK}]}})
        if p == "/api/v1/team-insights/transfer/preview":
            return httpx.Response(200, json={"data": {"moving_hours": 16, "warnings": [],
                                                      "from": {"before_pct": 137.1, "after_pct": 129.5}}})
        if p == "/api/v1/team-insights":
            return httpx.Response(200, json={"data": {"viewer": "admin", "insights": [{
                "kind": "rebalance", "subject": {"user_id": SARA, "name": "Sara"}, "workload": W_SARA,
                "plan": {"tasks": [{"task": {"id": TASK, "name": "Task 2", "remaining_hours": 16},
                                    "owner_before_pct": 137.1, "owner_after_pct": 129.5,
                                    "candidate": {"person": {"user_id": OMAR, "name": "Omar"},
                                                  "workload_pct": 23, "after_pct": 30.6,
                                                  "skill": {"status": "no_requirements"}},
                                    "reasons": [{"key": "overdue"}]}], "excluded": []}}]}})
        return httpx.Response(404, json={"message": f"unexpected {req.method} {p}"})

    return calls, handler


def test_team_relays_the_server_figure_without_recomputing():
    calls, h = _recorder()
    res, out = _run(["team"], h)
    assert res.exit_code == 0
    sara, omar = out["members"]
    assert sara["workload_pct"] == 137.1 and sara["band"] == "over"
    assert omar["workload_pct"] == 23.0 and omar["exact"] is True
    assert omar["free_hours"] == round(210 - 48.3, 1)
    assert calls[0]["path"] == "/api/v1/team-insights/workload"


def test_lower_bound_stays_a_lower_bound():
    _, h = _recorder()
    _, out = _run(["team"], h)
    sara = out["members"][0]
    assert sara["exact"] is False and sara["status"] == "lower_bound"
    assert sara["figure"].startswith("≥ 137%")


def test_band_filter_and_period():
    calls, h = _recorder()
    _, out = _run(["team", "--band", "available", "--month", "2026-11"], h)
    assert [m["name"] for m in out["members"]] == ["Omar"]
    assert calls[0]["query"]["month"] == "2026-11"
    res, _ = _run(["team", "--month", "2026-13"], h)
    assert res.exit_code != 0


def test_person_and_suggestions_come_from_the_engine():
    calls, h = _recorder()
    _, out = _run(["person", SARA], h)
    assert out["workload"]["workload_pct"] == 137.1 and out["tasks"][0]["id"] == TASK
    _, out = _run(["suggestions"], h)
    move = out["insights"][0]["moves"][0]
    assert move["to_id"] == OMAR and move["receiver_before_after"] == [23, 30.6]


def test_preview_writes_nothing_and_says_so():
    calls, h = _recorder()
    _, out = _run(["preview", "--from", SARA, "--to", OMAR, "--task", TASK], h)
    assert out["applied"] is False
    assert [c["path"] for c in calls] == ["/api/v1/team-insights/transfer/preview"]


def test_no_command_can_move_a_task():
    names = set(workload_group.commands)
    assert names == {"team", "person", "suggestions", "preview", "check", "calendar", "sprint-preview", "requests"}
    assert not any(n in names for n in ("transfer", "reassign", "move", "undo", "apply", "accept", "assign"))
    assert "workload" in cli.commands


def test_check_calendar_and_sprint_preview_only_read():
    calls = []

    def handler(req):
        calls.append((req.method, req.url.path, json.loads(req.content) if req.content else None, dict(req.url.params)))
        return httpx.Response(200, json={"data": {"people": [], "alternatives": [], "proposals": []}})

    res, out = _run(["check", "--task", TASK, "--user", OMAR, "--due", "2026-10-20"], handler)
    assert res.exit_code == 0 and out["applied"] is False
    assert calls[-1][1] == "/api/v1/team-insights/assignment-check"
    assert calls[-1][2] == {"task_ids": [TASK], "user_ids": [OMAR], "due_date": "2026-10-20", "mode": "replace"}
    res, out = _run(["calendar", "--from", "2026-10-04", "--to", "2026-10-17"], handler)
    assert calls[-1][1] == "/api/v1/team-insights/resource-calendar" and calls[-1][3]["from"] == "2026-10-04"
    res, out = _run(["sprint-preview", TASK, "--strategy", "round_robin"], handler)
    assert calls[-1][1] == "/api/v1/team-insights/sprint-auto-assign/preview" and out["applied"] is False
    res, _ = _run(["check"], handler)
    assert res.exit_code != 0
    # nothing here ever calls a write route
    assert all(not p.endswith(("/transfer", "/reassign", "/apply", "/accept", "/cancel", "/propose")) for _, p, _, _ in calls)
