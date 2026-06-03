import json
from tornix_cli.output import emit, emit_error
from tornix_cli.errors import TornixError


def test_emit_json(capsys):
    emit({"a": 1}, json_mode=True)
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_emit_jsonl(capsys):
    emit([{"a": 1}, {"a": 2}], json_mode=True, jsonl=True)
    lines = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(x) for x in lines] == [{"a": 1}, {"a": 2}]


def test_emit_error_json(capsys):
    code = emit_error(TornixError("boom", status=404, code="nf"), json_mode=True)
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["status"] == 404
    assert code == 4
