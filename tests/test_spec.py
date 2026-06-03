import json
from pathlib import Path
from tornix_cli.spec import load_spec, classify_tags, operations_by_tag

FIX = Path(__file__).parent / "fixtures" / "spec_min.json"


def test_classify_excludes_and_folds():
    spec = json.loads(FIX.read_text())
    cls = classify_tags(spec)
    assert "projects" in cls["generate"]
    assert "PostgREST Compatibility" in cls["fold"]
    assert "mcp" in cls["exclude"]


def test_operations_by_tag():
    spec = json.loads(FIX.read_text())
    ops = operations_by_tag(spec)
    ids = {o["operationId"] for o in ops["projects"]}
    assert ids == {"projects_list", "projects_create", "projects_get"}


def test_load_spec_pinned(tmp_path, monkeypatch):
    import tornix_cli.spec as s
    monkeypatch.setattr(s, "PINNED_SPEC", FIX)
    assert load_spec()["openapi"] == "3.0.0"
