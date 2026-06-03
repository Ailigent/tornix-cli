from tornix_cli.skillgen import render_skill


def test_render_skill_has_frontmatter_and_groups():
    catalog = {"name": "tornix", "commands": [
        {"name": "projects", "help": "Projects", "commands": [
            {"name": "list", "help": "List projects", "params": []}]},
        {"name": "deep-research", "help": "Research", "params": []},
    ]}
    md = render_skill(catalog)
    assert md.startswith("---")
    assert "name: tornix" in md
    assert "tornix projects list" in md
    assert "--json" in md
