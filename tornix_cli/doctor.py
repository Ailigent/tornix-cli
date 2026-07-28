from __future__ import annotations

import click

from .output import emit
from .spec import fetch_spec, load_spec

_HTTP = ("get", "post", "put", "patch", "delete")


def spec_operations(spec: dict) -> set[tuple[str, str]]:
    """Every (method, path) pair an OpenAPI document defines."""
    return {(m.lower(), p)
            for p, methods in (spec.get("paths") or {}).items()
            for m in methods if m.lower() in _HTTP}


def diff_specs(pinned: dict, live: dict) -> dict:
    """Compare the pinned snapshot against a live backend spec."""
    pinned_ops, live_ops = spec_operations(pinned), spec_operations(live)
    added = sorted([m, path] for m, path in live_ops - pinned_ops)
    removed = sorted([m, path] for m, path in pinned_ops - live_ops)
    return {"pinned_ops": len(pinned_ops), "live_ops": len(live_ops),
            "added": added, "removed": removed,
            "in_sync": not added and not removed}


@click.command("doctor", help="Diff the pinned OpenAPI snapshot against a live backend. "
                              "Exits non-zero on drift, so CI can gate on it.")
@click.option("--from", "src", default=None,
              help="Base URL to check against (defaults to the active profile).")
@click.pass_obj
def doctor_command(obj, src):
    base = src or obj["config"].api_url
    try:
        live = fetch_spec(base)
    except ValueError as e:
        raise click.UsageError(str(e))
    report = diff_specs(load_spec(), live)
    report["checked"] = base
    emit(report, json_mode=obj.get("json"))
    if not report["in_sync"]:
        raise SystemExit(1)
