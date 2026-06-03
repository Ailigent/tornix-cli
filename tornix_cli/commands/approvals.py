from __future__ import annotations

import click

from ._helpers import client, show


@click.group(name="approvals", help="Approvals (curated). Decisions act on workflow steps.")
def approvals_group() -> None:
    pass


@approvals_group.command("list")
@click.option("--status", default="pending")
@click.pass_obj
def approvals_list(obj, status):
    show(obj, client(obj).get("/api/v1/approvals/requests", params={"status": status}),
         columns=["id", "type", "status", "requested_by"])


@approvals_group.command("get")
@click.argument("request_id")
@click.pass_obj
def approvals_get(obj, request_id):
    show(obj, client(obj).get(f"/api/v1/approvals/requests/{request_id}"))


@approvals_group.command("approve")
@click.argument("step_id")
@click.option("--note", default=None)
@click.pass_obj
def approvals_approve(obj, step_id, note):
    body = {"note": note} if note else {}
    show(obj, client(obj).post(f"/api/v1/approvals/steps/{step_id}/approve", json=body or None))


@approvals_group.command("reject")
@click.argument("step_id")
@click.option("--note", default=None)
@click.pass_obj
def approvals_reject(obj, step_id, note):
    body = {"note": note} if note else {}
    show(obj, client(obj).post(f"/api/v1/approvals/steps/{step_id}/reject", json=body or None))
