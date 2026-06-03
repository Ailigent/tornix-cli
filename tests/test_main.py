from click.testing import CliRunner
from tornix_cli.__main__ import cli


def test_help_lists_layers():
    r = CliRunner().invoke(cli, ["--help"])
    assert r.exit_code == 0
    for name in ("auth", "config", "catalog", "data", "rpc", "api", "deep-research"):
        assert name in r.output


def test_global_json_flag_sets_obj():
    r = CliRunner().invoke(cli, ["--json", "catalog"], obj=None)
    assert r.exit_code == 0
    assert r.output.lstrip().startswith("{")
