"""Cost-scope tests for the generated `api cost ...` commands, using a
real-world-shaped construction baseline as fixture data: 41 monthly PV periods,
21 months of actuals (tests/fixtures/baseline_cost.json, fictional values).

The cost surface is generated-only (no curated `cost` group), so these pin the
exact method+path each command hits, the envelope unwrap, and that the PUT
pv-curve carries a realistic monthly curve verbatim via --data.
"""
import json
from pathlib import Path

import httpx
from click.testing import CliRunner

from tornix_cli.api_gen import build_api_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.spec import load_spec

BL = json.loads((Path(__file__).parent / "fixtures" / "baseline_cost.json").read_text())


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


def _grp():
    return build_api_group(load_spec())


def test_cost_evm_path_and_envelope():
    """EVM read: GET /projects/{id}/cost/evm, envelope unwrapped to the metrics."""
    # Realistic numbers: AC through month 21, PV cumulative at the same month.
    evm = {"bac": BL["bac"],
           "pv": BL["pv_cumulative"][len(BL["ac_monthly"]) - 1],
           "ac": round(sum(BL["ac_monthly"]), 2),
           "currency": "SAR"}
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": evm})

    # --data-date is a required query option (the EVM cutoff); use the last
    # month with actuals in the baseline.
    data_date = BL["months"][len(BL["ac_monthly"]) - 1] + "-01"
    r = CliRunner().invoke(_grp(), ["cost", "evm", "p1", "--data-date", data_date],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/projects/p1/cost/evm")
    assert data_date in seen["params"].values()
    assert json.loads(r.output) == evm


def test_cost_cashflow_path():
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        rows = [{"period": m, "planned": v}
                for m, v in zip(BL["months"][:3], BL["pv_monthly"][:3])]
        return httpx.Response(200, json={"data": rows})

    r = CliRunner().invoke(_grp(), ["cost", "cashflow", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/projects/p1/cost/cashflow")


def test_cost_estimates_path():
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(_grp(), ["cost", "estimates", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/projects/p1/cost/estimates")


def test_cost_pv_curve_is_the_read():
    """`api cost pv-curve` must be the GET (the DELETE lives at
    baseline-pv-curve-delete) — an agent reading the curve must not wipe it."""
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        seen["params"] = dict(req.url.params)
        curve = [{"period": m, "value": v}
                 for m, v in zip(BL["months"], BL["pv_monthly"])]
        return httpx.Response(200, json={"data": curve})

    # --baselineid is a required query option (which baseline's curve to read).
    r = CliRunner().invoke(_grp(), ["cost", "pv-curve", "p1", "--baselineid", "bl1"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/projects/p1/cost/baseline/pv-curve")
    assert "bl1" in seen["params"].values()
    assert len(json.loads(r.output)) == len(BL["months"])


def test_cost_pv_curve_put_carries_full_curve():
    """Setting the baseline: the PUT forwards a full real-shaped monthly curve
    verbatim through --data (the op has no requestBody in the spec, so --data is
    the only way to carry it — pinned by the universal write escape hatch)."""
    payload = {"curve": [{"period": m, "value": v}
                         for m, v in zip(BL["months"], BL["pv_monthly"])]}
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"ok": True}})

    r = CliRunner().invoke(
        _grp(),
        ["cost", "baseline-pv-curve-replace", "p1", "--data", json.dumps(payload)],
        obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("PUT", "/api/v1/projects/p1/cost/baseline/pv-curve")
    assert seen["body"] == payload
    assert len(seen["body"]["curve"]) == 41
    # Spot-check the data survived intact end-to-end (first month + BAC shape).
    assert seen["body"]["curve"][0] == {"period": "2024-05", "value": BL["pv_monthly"][0]}


def test_cost_periods_path():
    seen = {}

    def handler(req):
        seen["method"], seen["path"] = req.method, req.url.path
        return httpx.Response(200, json={"data": [{"period": m} for m in BL["months"]]})

    r = CliRunner().invoke(_grp(), ["cost", "periods", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/projects/p1/cost/periods")


def test_baseline_fixture_internal_consistency():
    """The fixture itself must stay coherent: cumulative PV is the running sum of
    monthly PV and ends at BAC."""
    run = 0.0
    for monthly, cum in zip(BL["pv_monthly"], BL["pv_cumulative"]):
        run += monthly
        assert abs(run - cum) < 1.0, f"cumulative drift at {cum}"
    assert abs(BL["pv_cumulative"][-1] - BL["bac"]) < 1.0
    assert len(BL["months"]) == len(BL["pv_monthly"]) == len(BL["pv_cumulative"])
    assert len(BL["ac_monthly"]) <= len(BL["months"])
