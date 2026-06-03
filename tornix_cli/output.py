from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from .errors import TornixError

_console = Console()
_err_console = Console(stderr=True)


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
