from __future__ import annotations

import click

from ..orgs import ALL, fetch_orgs, is_uuid, resolve_org, token_org_claim
from ._helpers import client, show


@click.group(name="orgs", help="Organizations you belong to (use with the global --org).")
def orgs_group() -> None:
    pass


@orgs_group.command("list", help="List your organizations (id, name, role); `current` marks the open one.")
@click.pass_obj
def orgs_list(obj):
    cl = client(obj)
    cfg = obj["config"]
    orgs = fetch_orgs(cl)
    cur = cfg.org_id
    if cur and cur.lower() == ALL:
        cur = None
    elif cur and not is_uuid(cur):
        cur = resolve_org(orgs, cur)
    cur = cur or token_org_claim(cfg.token) or token_org_claim(cfg.api_key)
    show(obj, [{"id": o["id"], "name": o["name"], "role": o["role"], "current": o["id"] == cur}
               for o in orgs], columns=["id", "name", "role", "current"])
