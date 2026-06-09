"""GATED live-staging reproduction for the 'create one project -> 2 untitled appear' bug.

Run against a real stage backend with a stage API key:

    TORNIX_E2E=1 TORNIX_PROFILE=stage pytest tests/test_projects_e2e.py -v

Findings from auditing the CLI (tornix_cli/commands/projects.py + client.py):
  - `tornix projects create --name X` builds body {"name": X} and calls POST
    /api/v1/projects EXACTLY ONCE. No loop, no retry of the dispatched request.
  - httpx.HTTPTransport(retries=N) only retries connection-ESTABLISHMENT failures
    (ConnectError/ConnectTimeout); it never re-sends an already-sent POST whose
    response merely times out. So the CLI itself cannot duplicate the POST.
Therefore, if extra blank-name projects appear, the duplication is server-side.
This test reproduces/exposes the observable bug end-to-end either way: create ONE
named project, then assert the live org gained exactly ONE project with that name
and ZERO new blank-named ("untitled") projects.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid

import pytest

E2E = os.environ.get("TORNIX_E2E") == "1"
pytestmark = pytest.mark.skipif(not E2E, reason="set TORNIX_E2E=1 with a stage key")


def run(*args):
    """Invoke the installed CLI in JSON mode against the stage profile."""
    env = {**os.environ, "TORNIX_PROFILE": os.environ.get("TORNIX_PROFILE", "stage")}
    p = subprocess.run(
        ["tornix", "--json", *args], capture_output=True, text=True, env=env
    )
    return p.returncode, p.stdout, p.stderr


def _rows(payload):
    """Normalize a list payload across envelope shapes.

    The client unwraps {"data": [...]} (client.py), so --json usually yields a
    bare list, but stay robust to {"data": [...]} and {"items": [...]} too.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "rows", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                return v
        # A single-object envelope -> treat as one row.
        return [payload]
    return []


def _list_projects():
    # Wide window: the backend default page is small (20), which would make the
    # before/after diff blind to pre-existing rows beyond page 1.
    code, out, err = run("projects", "list", "--limit", "100")
    assert code == 0, f"projects list failed: {err or out}"
    return _rows(json.loads(out) if out.strip() else [])


def _is_blank(name) -> bool:
    """A project counts as 'untitled' if its name is None / empty / whitespace."""
    return name is None or (isinstance(name, str) and name.strip() == "")


def _id_of(row):
    # The projects payload keys the id as "project_id" (verified against the live
    # stage backend); keep id/_id/uuid as fallbacks for other shapes.
    if isinstance(row, dict):
        return row.get("project_id") or row.get("id") or row.get("_id") or row.get("uuid")
    return None


def _name_of(row):
    if isinstance(row, dict):
        return row.get("name")
    return None


def _delete_project(pid) -> None:
    """Best-effort delete. Primary path is the generated DELETE command; fall back
    to the generic data escape hatch on the projects table itself (deleting only
    the organization_projects link row would orphan the project invisibly)."""
    if not pid:
        return
    code, _out, err = run("api", "projects", "delete", str(pid))
    if code != 0:
        run("data", "delete", "projects", "--eq", f"project_id={pid}")


def test_create_single_project_no_untitled_spawned():
    """Reproduce the bug: creating ONE named project must add exactly ONE project
    (with that exact name) and ZERO blank-named projects to the live org."""
    unique = "cli-e2e-" + uuid.uuid4().hex[:8]

    # 1) Snapshot existing state.
    before = _list_projects()
    before_ids = {_id_of(r) for r in before if _id_of(r) is not None}
    preexisting_blanks = [
        (_id_of(r), _name_of(r)) for r in before if _is_blank(_name_of(r))
    ]

    created_new_ids: list = []
    try:
        # 2) Create exactly ONE project. Register its id for cleanup straight
        # from the create response, independent of the list diff below.
        code, out, err = run("projects", "create", "--name", unique)
        assert code == 0, f"create failed: {err or out}"
        created = json.loads(out) if out.strip() else {}
        created_id = _id_of(created) if isinstance(created, dict) else None
        if created_id:
            created_new_ids.append(created_id)

        # 3) Re-list and diff to find genuinely NEW projects.
        after = _list_projects()
        new_rows = [r for r in after if _id_of(r) not in before_ids and _id_of(r) is not None]
        created_new_ids += [_id_of(r) for r in new_rows]

        # 4a) Surface any NEW blank-named projects -- the bug signature.
        new_blanks = [
            (_id_of(r), repr(_name_of(r))) for r in new_rows if _is_blank(_name_of(r))
        ]
        # 4b) Surface the named match.
        named_matches = [r for r in new_rows if _name_of(r) == unique]

        assert not new_blanks, (
            f"BUG REPRODUCED: creating one project '{unique}' spawned "
            f"{len(new_blanks)} extra blank-named (untitled) project(s): "
            f"{new_blanks}. All new project ids/names this run: "
            f"{[(_id_of(r), repr(_name_of(r))) for r in new_rows]}. "
            f"(pre-existing blanks, not counted: {preexisting_blanks})"
        )
        assert len(named_matches) == 1, (
            f"expected exactly ONE new project named '{unique}', "
            f"found {len(named_matches)}; all new: "
            f"{[(_id_of(r), repr(_name_of(r))) for r in new_rows]}"
        )
        assert len(new_rows) == 1, (
            f"creating one project added {len(new_rows)} new projects "
            f"(expected exactly 1): "
            f"{[(_id_of(r), repr(_name_of(r))) for r in new_rows]}"
        )
    finally:
        # 5) CLEANUP -- always, even on assertion failure. Delete the created
        # project and ANY new (untitled or otherwise) projects this run spawned.
        for pid in dict.fromkeys(created_new_ids):  # dedupe, preserve order
            _delete_project(pid)


def test_create_then_list_shows_name():
    """Lighter check: create a uniquely-named project and confirm a single list
    surfaces that exact name. Robust to envelope shapes."""
    unique = "cli-e2e-" + uuid.uuid4().hex[:8]
    before_ids = {_id_of(r) for r in _list_projects() if _id_of(r) is not None}

    new_id = None
    try:
        code, out, err = run("projects", "create", "--name", unique)
        assert code == 0, f"create failed: {err or out}"
        created = json.loads(out) if out.strip() else {}
        # Cleanup id comes from the create response, not the list match, so the
        # project cannot leak if the list assertion below fails.
        new_id = _id_of(created) if isinstance(created, dict) else None

        rows = _list_projects()
        match = next((r for r in rows if _name_of(r) == unique), None)
        assert match is not None, (
            f"created project '{unique}' not found in list; "
            f"names seen: {[_name_of(r) for r in rows]}"
        )
        new_id = new_id or _id_of(match)
        # Sanity: the matched id should be genuinely new.
        assert _id_of(match) not in before_ids, f"matched id {_id_of(match)!r} was not new"
    finally:
        if new_id is not None:
            _delete_project(new_id)
