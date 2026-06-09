"""GATED read-only staging probes of the cost scope against a live project
with real cost data (these tests NEVER write).

    TORNIX_E2E=1 TORNIX_PROFILE=stage \
    TORNIX_COST_E2E_PROJECT="<project name>" pytest tests/test_cost_e2e.py -v

Skips (not fails) if TORNIX_COST_E2E_PROJECT is unset or absent from the org.
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

E2E = os.environ.get("TORNIX_E2E") == "1"
pytestmark = pytest.mark.skipif(not E2E, reason="set TORNIX_E2E=1 with a stage key")

TARGET = os.environ.get("TORNIX_COST_E2E_PROJECT")


def run(*args):
    env = {**os.environ, "TORNIX_PROFILE": os.environ.get("TORNIX_PROFILE", "stage")}
    p = subprocess.run(["tornix", "--json", *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def _rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "rows", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                return v
        return [payload]
    return []


def _target_id():
    if not TARGET:
        pytest.skip("set TORNIX_COST_E2E_PROJECT to a project name with cost data")
    code, out, err = run("projects", "list", "--limit", "100")
    assert code == 0, f"projects list failed: {err or out}"
    for r in _rows(json.loads(out)):
        if isinstance(r, dict) and r.get("name") == TARGET:
            return r.get("project_id") or r.get("id")
    pytest.skip(f"{TARGET!r} not present in this org")


def test_cost_reads_respond():
    """Every cost read endpoint answers for the target project (read-only).
    pv-curve is omitted: it requires a --baselineid we cannot assume exists."""
    pid = _target_id()
    for cmd in (["api", "cost", "evm", pid, "--data-date", "2026-06-01"],
                ["api", "cost", "cashflow", pid],
                ["api", "cost", "estimates", pid],
                ["api", "cost", "periods", pid]):
        code, out, err = run(*cmd)
        assert code == 0, f"{' '.join(cmd[1:])} failed: {err or out}"
        payload = json.loads(out) if out.strip() else None
        assert isinstance(payload, (dict, list)), f"{cmd[2]}: unexpected payload {type(payload)}"


def test_evm_values_are_sane():
    """If EVM metrics exist they must be non-negative and internally plausible."""
    pid = _target_id()
    code, out, err = run("api", "cost", "evm", pid, "--data-date", "2026-06-01")
    assert code == 0, err or out
    evm = json.loads(out) if out.strip() else {}
    if not isinstance(evm, dict):
        pytest.skip("evm payload is not an object")
    nums = {k: v for k, v in evm.items()
            if isinstance(v, (int, float)) and k.lower() in
            ("bac", "pv", "ev", "ac", "eac", "etc", "planned_value",
             "earned_value", "actual_cost", "budget_at_completion")}
    for k, v in nums.items():
        assert v >= 0, f"negative EVM metric {k}={v}"
