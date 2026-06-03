from tornix_cli.errors import TornixError, EXIT


def test_exit_code_mapping():
    assert TornixError("nope", status=401).exit_code == EXIT.AUTH
    assert TornixError("bad", status=404).exit_code == EXIT.NOT_FOUND
    assert TornixError("bad", status=422).exit_code == EXIT.VALIDATION
    assert TornixError("slow", status=429).exit_code == EXIT.RATE_LIMIT
    assert TornixError("oops", status=500).exit_code == EXIT.GENERIC


def test_to_dict_shape():
    d = TornixError("denied", status=403, code="forbidden", hint="check scopes").to_dict()
    assert d == {"error": {"code": "forbidden", "message": "denied",
                           "status": 403, "hint": "check scopes"}}
