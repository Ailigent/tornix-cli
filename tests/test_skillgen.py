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


def test_agent_command_catalog_withholds_auth_and_api_key_lifecycle():
    import re

    commands = re.findall(r"^- `([^`]+)` —", _rendered(), re.MULTILINE)
    blocked = [
        command for command in commands
        if command.startswith("tornix api auth ")
        or command.startswith("tornix api api-keys ")
        or (command.startswith("tornix auth ") and command != "tornix auth whoami --json")
    ]
    assert blocked == []
    assert "tornix auth whoami --json" in commands
    assert "tornix auth login --json" not in commands


def test_agent_catalog_withholds_commands_that_accept_passwords():
    import re
    from tornix_cli.skillgen import agent_command_allowed

    withheld = (
        "tornix api company-admin members-create",
        "tornix api company-admin password",
        "tornix api company-admin-excel apply",
        "tornix api company-admin-talon talon-users-create",
        "tornix api company-admin-talon update",
        "tornix api company-admin-talon import",
        "tornix api users change-password",
        "tornix api users delete",
        "tornix api users delete-user",
        "tornix api users delete-google",
        "tornix api users delete-apple",
        "tornix api company-admin delete",
        "tornix api company-admin-talon delete",
        "tornix api email delete",
    )
    assert all(not agent_command_allowed(command) for command in withheld)

    allowed = (
        "tornix api company-admin members",
        "tornix api company-admin update",
        "tornix api company-admin-excel lookup",
        "tornix api company-admin-talon users",
        "tornix api company-admin-talon topup",
        "tornix api users capabilities",
        "tornix api email accounts",
        "tornix api email messages",
    )
    assert all(agent_command_allowed(command) for command in allowed)

    commands = re.findall(r"^- `([^`]+)` —", _rendered(), re.MULTILINE)
    assert not any(
        command.startswith(withheld_command + " --json")
        for command in commands for withheld_command in withheld
    )


def test_snapshot_password_request_fields_are_never_agent_commands():
    import click
    from tornix_cli.api_gen import build_api_group
    from tornix_cli.skillgen import agent_command_allowed
    from tornix_cli.spec import load_spec

    spec = load_spec()

    def has_password_field(schema, seen=frozenset()):
        if not isinstance(schema, dict):
            return False
        ref = schema.get("$ref")
        if ref:
            if not ref.startswith("#/") or ref in seen:
                return False
            target = spec
            for part in ref[2:].split("/"):
                target = target.get(part, {}) if isinstance(target, dict) else {}
            return has_password_field(target, seen | {ref})
        for name, child in (schema.get("properties") or {}).items():
            if "password" in name.lower() or has_password_field(child, seen):
                return True
        if has_password_field(schema.get("items"), seen):
            return True
        return any(
            has_password_field(child, seen)
            for key in ("allOf", "oneOf", "anyOf")
            for child in schema.get(key, [])
        )

    found = []
    for tag, group in build_api_group(spec).commands.items():
        if not isinstance(group, click.Group):
            continue
        for name, command in group.commands.items():
            operation = getattr(command, "_tornix_op", {})
            content = (operation.get("requestBody") or {}).get("content") or {}
            if any(
                has_password_field(media.get("schema", {}))
                for media in content.values()
            ):
                found.append((tag, name))
                assert not agent_command_allowed(f"tornix api {tag} {name}")
    assert len(found) >= 13


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


def test_generated_header_preserves_key_and_meeting_safety_rules():
    content = render_skill({"commands": []})
    assert "tornix api api-keys" in content
    assert "raw key only once" in content
    assert "tornix meetings room-create" in content
    assert "tornix calendar create" in content
    assert "anything with a time or an attendee" in content
    assert "its output may include human-only" in content
    assert "auth, API-key, password-bearing, and account/mailbox deletion operations above" in content
    assert "never provide credentials via command options or `--data`" in content
    assert "covers every backend operation" not in content


def test_generated_skill_preserves_identity_and_tenant_resolution():
    content = render_skill({"commands": []})
    assert "tornix auth whoami --json" in content
    assert "tornix config show --json" in content
    assert "never inspect raw config files or `.env`" in content
    assert "HERMES_HOME" in content
    assert "profile-specific `TORNIX_CONFIG`" in content
    assert "never use a shared/default config" in content
    assert "read-only `tornix api organizations list --json`" in content
    assert "match the returned caller" in content.lower()
    assert "explicit user-to-organization mapping" in content.lower()
    assert "If `org_id` is configured, verify it" in content
    assert "If it is absent, use only a single explicit" in content
    assert "choose the first" in content
    assert "item in the list" in content
    assert "stop before any" in content
    assert "further org-scoped data read or write" in content
    assert "Never invoke any `tornix auth …`" not in content
    assert "Never invoke `tornix auth login/logout/keys" in content


def test_scope_reference_generator_keeps_auth_guards_in_output():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/split_skill_scopes.py")
    spec = importlib.util.spec_from_file_location("split_skill_scopes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    core = module.render_core([
        ("tornix auth whoami", "Show the authenticated user"),
        ("tornix auth login", "Login"),
        ("tornix auth keys create", "Create key"),
        ("tornix projects list", "List projects"),
    ])
    api_auth = module.render_scope("auth", [("login", "Login"), ("me", "Current user")])
    api_keys = module.render_scope("api-keys", [("create", "Create key"), ("list", "List keys")])
    assert "tornix auth whoami --json" in core
    assert "tornix config show --json" in core
    assert "tornix api organizations list --json" in core
    assert "HERMES_HOME" in core
    assert "profile-specific `TORNIX_CONFIG`" in core
    assert "verify a configured `org_id`" in core.lower()
    assert "choose the first org" in core
    assert "tornix auth login --json" not in core
    assert "tornix auth keys create --json" not in core
    assert "tornix projects list --json" in core
    assert "only allowed `tornix auth` command" in core
    assert "Never invoke login/logout/keys" in core
    assert "Do not invoke any `tornix api auth …` command" in api_auth
    assert "`tornix auth whoami --json`" in api_auth
    assert "- `tornix api auth login --json`" not in api_auth
    assert "API key lifecycle" in api_keys
    assert "- `tornix api api-keys create --json`" not in api_keys


def test_scope_generator_withholds_password_commands_and_counts_visible_ops():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "split_skill_scopes", Path("scripts/split_skill_scopes.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ops = [
        ("members-create", "Add employee with password"),
        ("members", "List organization members"),
    ]
    rendered = module.render_scope("company-admin", ops)
    index = module.render_index({"company-admin": ops}, [])
    assert "members-create" not in rendered
    assert "members --json" in rendered
    assert "(1 commands)" in rendered
    assert "| company-admin | `references/scopes/company-admin.md` | 1 | List organization members |" in index
    assert "Available to agents: 1 API commands + 0 core commands across 1 API scopes" in index


def test_split_scope_command_writes_restricted_auth_and_key_refs(tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "split_skill_scopes", Path("scripts/split_skill_scopes.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "commands.md"
    source.write_text("\n".join([
        "- `tornix auth login --json` — Login",
        "- `tornix auth whoami --json` — Show caller",
        "- `tornix api auth login --json` — Login endpoint",
        "- `tornix api api-keys create --json` — Create key",
        "- `tornix api projects list --json` — List projects",
    ]) + "\n")
    scopes = tmp_path / "scopes"

    module.main(src=source, out_dir=scopes)

    core = (scopes / "core.md").read_text()
    auth = (scopes / "auth.md").read_text()
    keys = (scopes / "api-keys.md").read_text()
    index = source.read_text()
    assert "tornix auth whoami --json" in core
    assert "tornix auth login --json" not in core
    assert "tornix api auth login --json" not in auth
    assert "tornix api api-keys create --json" not in keys
    assert "| auth | `references/scopes/auth.md` | Restricted |" in index
    assert "| api-keys | `references/scopes/api-keys.md` | Restricted |" in index
    assert "Available to agents: 1 API commands + 1 core commands" in index
    before = {
        path: path.read_bytes()
        for path in (source, scopes / "core.md", scopes / "auth.md", scopes / "api-keys.md", scopes / "projects.md")
    }
    module.main(src=source, out_dir=scopes)
    assert all(path.read_bytes() == content for path, content in before.items())


def test_checked_in_scope_docs_match_guarded_generator():
    import importlib.util
    import re
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "split_skill_scopes", Path("scripts/split_skill_scopes.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    core_path = Path("skills/tornix/references/scopes/core.md")
    core = []
    for line in core_path.read_text().splitlines():
        match = re.match(r"^- `(.*?)` — (.*)$", line)
        if match:
            core.append((match.group(1).removesuffix(" --json"), match.group(2)))
    assert core_path.read_text() == module.render_core(core)

    auth_path = Path("skills/tornix/references/scopes/auth.md")
    ops = []
    for line in auth_path.read_text().splitlines():
        match = re.match(r"^- `tornix api auth ([a-z0-9-]+) --json` — (.*)$", line)
        if match:
            ops.append((match.group(1), match.group(2)))
    assert auth_path.read_text() == module.render_scope("auth", ops)

    api_keys_path = Path("skills/tornix/references/scopes/api-keys.md")
    key_ops = []
    for line in api_keys_path.read_text().splitlines():
        match = re.match(r"^- `tornix api api-keys ([a-z0-9-]+) --json` — (.*)$", line)
        if match:
            key_ops.append((match.group(1), match.group(2)))
    assert api_keys_path.read_text() == module.render_scope("api-keys", key_ops)


def test_readme_keeps_auth_credentials_out_of_command_arguments():
    from pathlib import Path

    readme = Path("README.md").read_text()
    assert "Credential setup is human-operator-only" in readme
    assert "Do not pass API keys, passwords, or OTPs as command-line arguments" in readme
    assert "--" + "password" not in readme
    assert "--" + "code" not in readme
    assert "tornix --json auth whoami" in readme


def test_checked_in_skill_docs_match_generator():
    from pathlib import Path

    generated = _rendered()
    assert Path("skills/tornix/SKILL.md").read_text() == generated
    assert Path("docs/COMMANDS.md").read_text() == generated
