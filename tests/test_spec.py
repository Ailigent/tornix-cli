import json
from pathlib import Path
from tornix_cli.spec import load_spec, classify_tags, is_excluded_op, operations_by_tag

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
    assert ids == {"projects_list", "projects_get"}
    assert {o["operationId"] for o in ops["widgets"]} == {"widgets_create"}


def test_is_excluded_op_superseded_by_method_path():
    """SUPERSEDED_OPS keys on wire coordinates (method, path) — NOT operationId —
    so a `tornix gen` spec refresh that renames controllers cannot silently
    resurrect the empty-body create commands."""
    assert is_excluded_op({"_method": "post", "_path": "/api/v1/projects"})
    assert is_excluded_op({"_method": "post",
                           "_path": "/api/v1/projects/{projectId}/tasks"})
    # Same paths with other methods stay generated.
    assert not is_excluded_op({"_method": "get", "_path": "/api/v1/projects"})
    assert not is_excluded_op({"_method": "get",
                               "_path": "/api/v1/projects/{projectId}/tasks"})
    # Webhook/callback paths remain excluded.
    assert is_excluded_op({"_method": "post", "_path": "/api/v1/livekit/webhook"})


def test_load_spec_pinned(tmp_path, monkeypatch):
    import tornix_cli.spec as s
    monkeypatch.setattr(s, "PINNED_SPEC", FIX)
    assert load_spec()["openapi"] == "3.0.0"


# ── backend resync (2026-07) ──────────────────────────────────────────────

def test_pinned_spec_is_current_prod_surface():
    spec = load_spec()
    ops = [(m, p) for p, ms in spec["paths"].items() for m in ms
           if m in ("get", "post", "put", "patch", "delete")]
    assert len(spec["paths"]) == 968
    assert len(ops) == 1257


def test_pinned_spec_covers_the_new_backend_tags():
    tags = {(op.get("tags") or ["misc"])[0]
            for ms in load_spec()["paths"].values() for op in ms.values()
            if isinstance(op, dict)}
    for new in ("agile", "governance", "templates", "memory", "twin",
                "request-board", "search", "bim", "pre-project",
                "access-requests", "app-versions", "link-preview", "data"):
        assert new in tags, f"missing new backend tag: {new}"


def test_dead_super_agent_proxy_ops_are_gone():
    assert "/api/v1/ai/super-agent/*" not in load_spec()["paths"]
