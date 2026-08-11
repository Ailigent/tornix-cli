from __future__ import annotations

import json as _json
import time as _time
import uuid as _uuid

import click

from ._helpers import client, show


@click.group(name="meetings", help="Meetings (curated).")
def meetings_group() -> None:
    pass


@meetings_group.command("list", help="List meetings (optionally by project).")
@click.option("--project", "project_id", default=None)
@click.pass_obj
def meetings_list(obj, project_id):
    params = {"project_id": project_id} if project_id else None
    show(obj, client(obj).get("/api/v1/meetings", params=params),
         columns=["id", "status", "started_at", "ended_at", "project_id"])


@meetings_group.command("get", help="Get a meeting by id.")
@click.argument("meeting_id")
@click.pass_obj
def meetings_get(obj, meeting_id):
    show(obj, client(obj).get(f"/api/v1/meetings/{meeting_id}"))


@meetings_group.command("transcript", help="Get a meeting's transcript.")
@click.argument("meeting_id")
@click.pass_obj
def meetings_transcript(obj, meeting_id):
    show(obj, client(obj).get(f"/api/v1/meetings/{meeting_id}/transcript"))


@meetings_group.command("minutes", help="Get a meeting's minutes.")
@click.argument("meeting_id")
@click.pass_obj
def meetings_minutes(obj, meeting_id):
    show(obj, client(obj).get(f"/api/v1/meetings/{meeting_id}/minutes"))


@meetings_group.command("action-items", help="Get a meeting's action items.")
@click.argument("meeting_id")
@click.pass_obj
def meetings_action_items(obj, meeting_id):
    show(obj, client(obj).get(f"/api/v1/meetings/{meeting_id}/action-items"))


# ── Meeting (video) rooms ─────────────────────────────────────────────────
# The frontend stores meeting rooms in the `video_rooms` table (via the
# data proxy). These curated commands wrap that table so rooms can be
# created/listed/deactivated from the CLI. The data proxy path is
# `/api/v1/data/{table}` (the same path `tornix data …` uses).

_TABLE = "video_rooms"


@meetings_group.command("room-create", help="Create a meeting (video) room in the org.")
@click.option("--name", required=True, help="Display name of the room.")
@click.option("--org", "organization_id", default=None,
              help="Organization id (defaults to active config org).")
@click.option("--max-participants", default=50, type=int, show_default=True)
@click.option("--is-public", is_flag=True, default=False)
@click.option("--auto-record", is_flag=True, default=False)
@click.option("--auto-accept-guests", is_flag=True, default=False)
@click.option("--feeds-backlog", is_flag=True, default=False)
@click.pass_obj
def meetings_room_create(obj, name, organization_id, max_participants,
                         is_public, auto_record, auto_accept_guests, feeds_backlog):
    """Insert a `video_rooms` row — the same table the frontend uses for
    meeting rooms. `room_name` follows the frontend convention."""
    org_id = organization_id or obj["config"].org_id
    user_id = None
    # Best-effort: current user id from the cached whoami
    try:
        me = client(obj).get("/api/v1/users/me")
        user_id = (me.get("user") or me).get("id")
    except Exception:
        pass

    room_name = f"room-{org_id}-{int(_time.time() * 1000)}-{_uuid.uuid4().hex[:6]}"
    body = {
        "name": name,
        "room_name": room_name,
        "organization_id": org_id,
        "max_participants": max_participants,
        "is_active": True,
        "is_public": is_public,
        "auto_record": auto_record,
        "auto_accept_guests": auto_accept_guests,
        "feeds_backlog": feeds_backlog,
    }
    if user_id:
        body["created_by"] = user_id

    show(obj, client(obj).post(f"/api/v1/data/{_TABLE}", json=body, envelope=True))


@meetings_group.command("room-list", help="List active meeting (video) rooms in the org.")
@click.option("--org", "organization_id", default=None,
              help="Organization id (defaults to active config org).")
@click.pass_obj
def meetings_room_list(obj, organization_id):
    org_id = organization_id or obj["config"].org_id
    params = {"organization_id": f"eq.{org_id}", "is_active": "eq.true"}
    show(obj, client(obj).get(f"/api/v1/data/{_TABLE}", params=params),
         columns=["id", "name", "is_active", "created_at"])


@meetings_group.command("room-delete", help="Deactivate/delete a meeting (video) room.")
@click.argument("room_id")
@click.option("--hard", is_flag=True, default=False,
              help="Hard-delete the row instead of deactivating.")
@click.pass_obj
def meetings_room_delete(obj, room_id, hard):
    params = {"id": f"eq.{room_id}"}
    if hard:
        show(obj, client(obj).delete(f"/api/v1/data/{_TABLE}", params=params))
    else:
        show(obj, client(obj).patch(f"/api/v1/data/{_TABLE}",
                                    params=params, json={"is_active": False}))
