from __future__ import annotations

import click

from .output import emit


def _describe(cmd: click.Command, name: str) -> dict:
    node: dict = {"name": name, "help": (cmd.help or "").strip().split("\n")[0]}
    if isinstance(cmd, click.Group):
        node["commands"] = [_describe(c, n) for n, c in sorted(cmd.commands.items())]
    else:
        params = []
        for p in cmd.params:
            if p.name == "help":
                continue
            params.append({"name": p.name,
                           "kind": "argument" if isinstance(p, click.Argument) else "option",
                           "required": bool(getattr(p, "required", False)),
                           "type": getattr(p.type, "name", "text")})
        node["params"] = params
    return node


@click.command(name="catalog", help="Print the full command tree (use --json for agents).")
@click.pass_context
def catalog_command(ctx):
    root = ctx.find_root().command
    tree = _describe(root, "tornix")
    json_mode = (ctx.obj or {}).get("json", True)
    emit(tree, json_mode=json_mode)
