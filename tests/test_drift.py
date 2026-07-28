"""The curated overlay is hand-written and nothing else ties it back to the
spec — which is why it silently rotted when the backend shipped. This is the
guard: a curated command that calls a path the spec does not define is a test
failure, not a 404 discovered in production."""
import re
from pathlib import Path

import pytest

from tornix_cli.spec import load_spec

SRC = Path(__file__).resolve().parent.parent / "tornix_cli"
CURATED = sorted(SRC.glob("commands/*.py")) + [SRC / "auth.py"]

CALL = re.compile(r"""\.(get|post|put|patch|delete)\(\s*f?["']([^"']+)["']""")


def _normalize(path: str) -> str:
    """f-string interpolations and spec placeholders both collapse to {}, so
    `{project_id}` matches the spec's `{projectId}`."""
    return re.sub(r"\{[^}]+\}", "{}", path)


@pytest.mark.parametrize("source", CURATED, ids=lambda p: p.name)
def test_curated_commands_only_call_paths_the_spec_defines(source):
    spec = load_spec()
    by_norm = {}
    for p in spec["paths"]:
        by_norm.setdefault(_normalize(p), p)

    missing = []
    for method, path in CALL.findall(source.read_text()):
        if not path.startswith("/api/"):
            continue
        real = by_norm.get(_normalize(path))
        if real is None or method not in spec["paths"][real]:
            missing.append(f"{method.upper()} {path}")
    assert not missing, f"{source.name} calls paths absent from the pinned spec: {missing}"


def test_the_guard_actually_catches_a_stale_path(tmp_path):
    """Guard the guard: a file calling a bogus path must fail the check."""
    spec = load_spec()
    by_norm = {_normalize(p): p for p in spec["paths"]}
    stale = tmp_path / "stale.py"
    stale.write_text('client.get("/api/v1/definitely-not-a-real-endpoint")\n')
    found = [p for _, p in CALL.findall(stale.read_text())
             if p.startswith("/api/") and _normalize(p) not in by_norm]
    assert found, "the drift regex must detect a bogus curated path"
