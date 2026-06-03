from __future__ import annotations

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
         columns=["id", "title", "scheduled_at", "status"])


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
