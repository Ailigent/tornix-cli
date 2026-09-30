import json
from collections import Counter
from pathlib import Path

import unittest

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


def test_fetch_spec_normalizes_exporter_global_prefix(monkeypatch):
    import tornix_cli.spec as s

    raw = {
        "openapi": "3.0.0",
        "paths": {
            "/projects": {"get": {"operationId": "projects_list"}},
            "/api/v1/health": {"get": {"operationId": "health"}},
            "/rest/v1/{table}": {"get": {"operationId": "rest_get"}},
            "/storage/v1/object/list/{bucket}": {"get": {"operationId": "storage_list"}},
            "/api/credits/consume": {"post": {"operationId": "credits_consume"}},
        },
    }

    class Response:
        def json(self):
            return raw

    monkeypatch.setattr(s.httpx, "get", lambda url, timeout: Response())
    spec = s.fetch_spec("https://backend.example")

    assert "/api/v1/projects" in spec["paths"]
    assert "/api/v1/health" in spec["paths"]
    assert "/rest/v1/{table}" in spec["paths"]
    assert "/storage/v1/object/list/{bucket}" in spec["paths"]
    assert "/api/credits/consume" in spec["paths"]
    assert "/projects" not in spec["paths"]


def test_normalize_spec_paths_merges_aliases_and_rejects_conflicts():
    from tornix_cli.spec import normalize_spec_paths

    merged = normalize_spec_paths({"paths": {
        "/projects": {"get": {"operationId": "list"}},
        "/api/v1/projects": {"post": {"operationId": "create"}},
    }})
    assert set(merged["paths"]["/api/v1/projects"]) == {"get", "post"}

    with unittest.TestCase().assertRaisesRegex(ValueError, "conflicting OpenAPI paths"):
        normalize_spec_paths({"paths": {
            "/projects": {"get": {"operationId": "old"}},
            "/api/v1/projects": {"get": {"operationId": "different"}},
        }})


def test_normalize_spec_paths_validates_input_and_compatibility_boundaries():
    from tornix_cli.spec import normalize_spec_paths

    for paths in ({"projects": {"get": {}}}, {"/projects": None}):
        with unittest.TestCase().assertRaises(ValueError):
            normalize_spec_paths({"paths": paths})

    normalized = normalize_spec_paths({"paths": {
        "/api/credits": {},
        "/api/credits/{id}": {},
        "/api/credits-extra": {},
        "/rest/v1": {},
        "/rest/v10/rows": {},
        "/storage/v1/object": {},
    }})
    assert "/api/credits" in normalized["paths"]
    assert "/api/credits/{id}" in normalized["paths"]
    assert "/api/v1/api/credits-extra" in normalized["paths"]
    assert "/rest/v1" in normalized["paths"]
    assert "/api/v1/rest/v10/rows" in normalized["paths"]
    assert "/storage/v1/object" in normalized["paths"]


def test_doctor_diff_normalizes_exporter_paths_against_snapshot():
    from tornix_cli.doctor import diff_specs

    pinned = {"paths": {
        "/api/v1/projects": {"get": {}},
        "/rest/v1/{table}": {"get": {}},
        "/api/credits/consume": {"post": {}},
    }}
    exporter_style = {"paths": {
        "/projects": {"get": {}},
        "/rest/v1/{table}": {"get": {}},
        "/api/credits/consume": {"post": {}},
    }}

    report = diff_specs(pinned, exporter_style)

    assert report["in_sync"]
    assert report["pinned_ops"] == report["live_ops"] == 3


def test_doctor_command_accepts_exporter_style_live_spec(monkeypatch):
    from types import SimpleNamespace
    from click.testing import CliRunner
    import tornix_cli.doctor as doctor

    pinned = {"paths": {"/api/v1/projects": {"get": {}}}}
    exporter_style = {"paths": {"/projects": {"get": {}}}}
    monkeypatch.setattr(doctor, "load_spec", lambda: pinned)
    monkeypatch.setattr(doctor, "fetch_spec", lambda base: exporter_style)
    obj = {"config": SimpleNamespace(api_url="https://backend.example"), "json": True}

    result = CliRunner().invoke(doctor.doctor_command, [], obj=obj)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["in_sync"]


def test_gen_writes_normalized_exporter_paths(tmp_path, monkeypatch):
    import tornix_cli.__main__ as entry
    import tornix_cli.spec as spec_module
    from click.testing import CliRunner
    from types import SimpleNamespace

    raw = {
        "openapi": "3.0.0",
        "paths": {
            "/projects": {"get": {"operationId": "projects_list"}},
            "/rest/v1/{table}": {"get": {"operationId": "rest_get"}},
        },
    }

    class Response:
        def json(self):
            return raw

    monkeypatch.setattr(spec_module.httpx, "get", lambda url, timeout: Response())
    package_dir = tmp_path / "package"
    (package_dir / "generated").mkdir(parents=True)
    monkeypatch.setattr(entry, "__file__", str(package_dir / "__main__.py"))
    obj = {"config": SimpleNamespace(api_url="https://backend.example"), "client": object()}

    result = CliRunner().invoke(entry.cli, ["--json", "gen"], obj=obj)

    assert result.exit_code == 0, result.output
    generated = json.loads((package_dir / "generated" / "_spec.json").read_text())
    assert "/api/v1/projects" in generated["paths"]
    assert "/rest/v1/{table}" in generated["paths"]
    assert "/projects" not in generated["paths"]


# ── Talon backend resync (2026-09) ────────────────────────────────────────

def test_pinned_spec_matches_github_talon_surface():
    spec = load_spec()
    ops = [(m, p) for p, ms in spec["paths"].items() for m in ms
           if m.lower() in ("get", "post", "put", "patch", "delete")]
    assert len(spec["paths"]) == 1361
    assert len(ops) == 1738
    method_entries = Counter(method.upper() for path_item in spec["paths"].values()
                             for method in path_item)
    assert method_entries == Counter({
        "DELETE": 161, "GET": 665, "HEAD": 15, "OPTIONS": 14,
        "PATCH": 97, "POST": 669, "PUT": 146, "SEARCH": 14,
    })
    assert sum(method_entries.values()) == 1781


def test_pinned_spec_covers_the_new_backend_tags():
    tags = {tag for ms in load_spec()["paths"].values() for op in ms.values()
            if isinstance(op, dict) for tag in op.get("tags", [])}
    assert len(tags) == 96
    for new in ("agile", "governance", "templates", "memory", "twin",
                "request-board", "search", "bim", "pre-project",
                "access-requests", "app-versions", "link-preview", "data",
                "ai-context", "collaborations", "company-admin", "company-admin-excel",
                "company-admin-talon", "credit-hub", "erp", "forecast", "graphql",
                "insights", "lessons", "linked-instances", "navigation",
                "procurement-price-anomalies", "procurement-scoring", "snagging",
                "ui-permissions"):
        assert new in tags, f"missing Talon backend tag: {new}"


def test_pinned_spec_includes_talon_app_version_routes():
    paths = load_spec()["paths"]
    assert "/api/v1/app-versions/push-targets" in paths
    assert "/api/v1/app-versions/receive" in paths
    assert "/api/v1/app-versions/{id}/push" in paths


def test_pinned_spec_preserves_global_prefix_exceptions():
    paths = load_spec()["paths"]
    assert "/api/v1/projects" in paths
    assert "/rest/v1/{table}" in paths
    assert "/storage/v1/object/list/{bucket}" in paths
    assert "/api/credits/consume" in paths
    assert all(path.startswith(("/api/v1/", "/rest/v1/", "/storage/v1/", "/api/credits/"))
               for path in paths)


def test_dead_super_agent_proxy_ops_are_gone():
    assert "/api/v1/ai/super-agent/*" not in load_spec()["paths"]


def test_pinned_spec_carries_the_bim_register_4d_5d_surface():
    """BIM phases 1-3 (register, 4D, 5D) are what an agent reads the model through."""
    paths = load_spec()["paths"]
    for route in ("/api/v1/bim/register/elements", "/api/v1/bim/register/summary",
                  "/api/v1/bim/register/elements/{id}", "/api/v1/bim/locations",
                  "/api/v1/bim/models/{id}/cde-history", "/api/v1/bim/4d/summary",
                  "/api/v1/bim/4d/sequence", "/api/v1/bim/4d/lookahead",
                  "/api/v1/bim/5d/summary", "/api/v1/bim/5d/elements",
                  "/api/v1/bim/5d/quantities", "/api/v1/bim/5d/progress-rules",
                  "/api/v1/bim/5d/elements/{id}/cost"):
        assert route in paths, route
