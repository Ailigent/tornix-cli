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


# ── agent surface resync (2026-07) ────────────────────────────────────────

def _rendered():
    from tornix_cli.__main__ import cli
    from tornix_cli.catalog import _describe
    from tornix_cli.skillgen import render_skill
    return render_skill(_describe(cli, "tornix"))


def test_generated_skill_covers_the_new_backend_domains():
    content = _rendered()
    for domain in ("agile", "governance", "templates", "memory", "twin", "search"):
        assert f"tornix api {domain} " in content, f"SKILL.md missing {domain}"


def test_generated_skill_advertises_no_numeric_suffix_names():
    import re
    content = _rendered()
    bad = re.findall(r"`tornix api [\w-]+ ([\w-]*-\d) ", content)
    assert bad == [], f"SKILL.md advertises meaningless command names: {bad}"


def test_generated_skill_uses_the_real_api_key_prefix():
    """Live keys are `tnx_`-prefixed; the docs said `tk_`, which sends agents and
    users looking for a key format that does not exist."""
    content = _rendered()
    assert "tk_" not in content
