from __future__ import annotations

from ..output import emit


def show(obj: dict, data, columns: list[str] | None = None) -> None:
    emit(data, json_mode=obj.get("json", False), columns=columns)


def client(obj: dict):
    return obj["client"]
