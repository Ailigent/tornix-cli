from __future__ import annotations

import json
import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .errors import TornixError

_console = Console()
_err_console = Console(stderr=True)


def _set_json(ctx, param, value):
    """Eager option callback: flip the shared ctx.obj into JSON mode."""
    if value and isinstance(ctx.obj, dict):
        ctx.obj["json"] = True
    return value


def _set_jsonl(ctx, param, value):
    """Eager option callback: JSON-lines mode (implies JSON)."""
    if value and isinstance(ctx.obj, dict):
        ctx.obj["json"] = True
        ctx.obj["jsonl"] = True
    return value


def emit_result(obj: dict, data: Any, columns: list[str] | None = None) -> None:
    """Emit honoring the shared context's json / jsonl flags."""
    emit(data, json_mode=obj.get("json", False), jsonl=obj.get("jsonl", False), columns=columns)


def add_json_option(group: "click.Group") -> None:
    """Recursively give every subcommand uniform eager `--json` / `--jsonl` flags so they
    work both before (`tornix --json projects list`) and after (`tornix projects list --json`)
    the subcommand. expose_value=False keeps them out of command signatures."""
    for cmd in group.commands.values():
        opts = {o for p in cmd.params if isinstance(p, click.Option) for o in p.opts}
        if "--json" not in opts:
            cmd.params.append(click.Option(["--json"], is_flag=True, expose_value=False,
                                           callback=_set_json,
                                           help="Machine-readable JSON output."))
        if "--jsonl" not in opts:
            cmd.params.append(click.Option(["--jsonl"], is_flag=True, expose_value=False,
                                           callback=_set_jsonl,
                                           help="JSON-lines output (one row per line)."))
        if isinstance(cmd, click.Group):
            add_json_option(cmd)


def emit(data: Any, *, json_mode: bool = False, jsonl: bool = False,
         columns: list[str] | None = None) -> None:
    if json_mode:
        if jsonl and isinstance(data, list):
            for row in data:
                sys.stdout.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        else:
            sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n")
        return
    _render_human(data, columns)


def _render_human(data: Any, columns: list[str] | None) -> None:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        cols = columns or list(data[0].keys())[:8]
        table = Table(show_lines=False)
        for c in cols:
            table.add_column(str(c))
        for row in data:
            table.add_row(*[_fmt(row.get(c)) for c in cols])
        _console.print(table)
    elif data is None:
        _console.print("[dim](no content)[/dim]")
    elif isinstance(data, (dict, list)):
        _console.print_json(data=data)
    else:
        _console.print(data)


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def emit_error(err: TornixError, *, json_mode: bool = False) -> int:
    if json_mode:
        _err_console.file.write(json.dumps(err.to_dict(), ensure_ascii=False) + "\n")
    else:
        line = f"[red]error[/red]: {err.message}"
        if err.status:
            line += f" [dim](HTTP {err.status})[/dim]"
        _err_console.print(line)
        if err.hint:
            _err_console.print(f"[yellow]hint[/yellow]: {err.hint}")
    return err.exit_code
