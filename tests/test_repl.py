from tornix_cli.repl import parse_line


def test_parse_line_quotes():
    assert parse_line('projects create --name "Big Villa"') == \
        ["projects", "create", "--name", "Big Villa"]


def test_parse_line_blank():
    assert parse_line("   ") == []
