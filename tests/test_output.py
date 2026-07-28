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


# ── resilient columns (2026-07 resync) ────────────────────────────────────
# `projects list` rendered empty `id`/`progress` columns after the backend
# renamed those fields to `project_id`/`success_rate`. A requested column the
# payload does not have must not render as a column of blanks.

def test_missing_requested_columns_are_dropped(capsys):
    rows = [{"project_id": "p1", "name": "TaskFlow", "success_rate": 42}]
    emit(rows, columns=["id", "name", "progress"])
    out = capsys.readouterr().out
    assert "name" in out and "TaskFlow" in out
    assert "progress" not in out


def test_all_columns_missing_falls_back_to_payload_keys(capsys):
    rows = [{"project_id": "p1", "success_rate": 42}]
    emit(rows, columns=["id", "progress"])
    out = capsys.readouterr().out
    assert "project_id" in out and "p1" in out


def test_present_columns_are_still_honored_in_order(capsys):
    rows = [{"b": 2, "a": 1}]
    emit(rows, columns=["a", "b"])
    out = capsys.readouterr().out
    assert out.index("a") < out.index("b")


def test_column_present_in_only_a_later_row_is_kept(capsys):
    rows = [{"name": "A"}, {"name": "B", "status": "ACTIVE"}]
    emit(rows, columns=["name", "status"])
    out = capsys.readouterr().out
    assert "status" in out and "ACTIVE" in out
