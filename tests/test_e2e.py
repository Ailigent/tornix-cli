import json
import os
import subprocess

import pytest

E2E = os.environ.get("TORNIX_E2E") == "1"
pytestmark = pytest.mark.skipif(not E2E, reason="set TORNIX_E2E=1 with a stage key")


def run(*args):
    env = {**os.environ, "TORNIX_PROFILE": os.environ.get("TORNIX_PROFILE", "stage")}
    p = subprocess.run(["tornix", "--json", *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def test_whoami_live():
    code, out, err = run("auth", "whoami")
    assert code == 0, err
    body = json.loads(out)
    assert "email" in body or "id" in body


def test_catalog_live():
    code, out, _ = run("catalog")
    assert code == 0
    assert json.loads(out)["name"] == "tornix"


def test_projects_list_live():
    code, out, err = run("projects", "list", "--limit", "1")
    assert code == 0, err


def test_deep_research_pmo_shape():
    code, out, err = run("deep-research", "status?", "--source", "pmo")
    assert code == 0, err
    assert json.loads(out)["mode"] == "agent"
