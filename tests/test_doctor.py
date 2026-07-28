"""Unit tests for the spec-drift diff behind `tornix doctor`."""
from tornix_cli.doctor import diff_specs, spec_operations

PINNED = {"paths": {
    "/api/v1/a": {"get": {}},
    "/api/v1/gone": {"post": {}},
}}
LIVE = {"paths": {
    "/api/v1/a": {"get": {}},
    "/api/v1/new": {"put": {}},
}}


def test_spec_operations_extracts_method_path_pairs():
    assert spec_operations(PINNED) == {("get", "/api/v1/a"), ("post", "/api/v1/gone")}


def test_spec_operations_ignores_non_http_keys():
    spec = {"paths": {"/x": {"get": {}, "parameters": [], "summary": "n/a"}}}
    assert spec_operations(spec) == {("get", "/x")}


def test_spec_operations_tolerates_an_empty_document():
    assert spec_operations({}) == set()


def test_diff_specs_reports_added_and_removed():
    d = diff_specs(PINNED, LIVE)
    assert d["added"] == [["put", "/api/v1/new"]]
    assert d["removed"] == [["post", "/api/v1/gone"]]
    assert d["pinned_ops"] == 2 and d["live_ops"] == 2
    assert d["in_sync"] is False


def test_diff_specs_in_sync_when_identical():
    d = diff_specs(PINNED, PINNED)
    assert d["added"] == [] and d["removed"] == [] and d["in_sync"] is True


def test_doctor_reports_drift_and_exits_nonzero(monkeypatch):
    import httpx
    from click.testing import CliRunner

    from tornix_cli.client import TornixClient
    from tornix_cli.config import Config
    from tornix_cli.doctor import doctor_command

    monkeypatch.setattr("tornix_cli.doctor.fetch_spec", lambda base, **kw: LIVE)
    monkeypatch.setattr("tornix_cli.doctor.load_spec", lambda: PINNED)
    cfg = Config(api_url="https://x.test")
    obj = {"config": cfg,
           "client": TornixClient(cfg, transport=httpx.MockTransport(
               lambda r: httpx.Response(200, json={}))),
           "json": True}
    r = CliRunner().invoke(doctor_command, [], obj=obj)
    assert r.exit_code != 0, "drift must be a non-zero exit so CI can gate on it"
    assert "/api/v1/new" in r.output


def test_doctor_exits_zero_when_in_sync(monkeypatch):
    import httpx
    from click.testing import CliRunner

    from tornix_cli.client import TornixClient
    from tornix_cli.config import Config
    from tornix_cli.doctor import doctor_command

    monkeypatch.setattr("tornix_cli.doctor.fetch_spec", lambda base, **kw: PINNED)
    monkeypatch.setattr("tornix_cli.doctor.load_spec", lambda: PINNED)
    cfg = Config(api_url="https://x.test")
    obj = {"config": cfg,
           "client": TornixClient(cfg, transport=httpx.MockTransport(
               lambda r: httpx.Response(200, json={}))),
           "json": True}
    r = CliRunner().invoke(doctor_command, [], obj=obj)
    assert r.exit_code == 0, r.output
