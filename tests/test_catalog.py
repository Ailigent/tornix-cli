import json
from click.testing import CliRunner
from tornix_cli.__main__ import cli


def test_catalog_json_lists_groups():
    r = CliRunner().invoke(cli, ["catalog", "--json"], obj={"json": True})
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    names = {c["name"] for c in data["commands"]}
    assert {"auth", "data", "rpc", "api", "deep-research"} <= names
