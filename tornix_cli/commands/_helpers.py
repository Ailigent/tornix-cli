from __future__ import annotations

from ..output import emit_result


def show(obj: dict, data, columns: list[str] | None = None) -> None:
    emit_result(obj, data, columns=columns)


def client(obj: dict):
    return obj["client"]
