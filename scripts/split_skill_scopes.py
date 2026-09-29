#!/usr/bin/env python3
"""Split the generated commands.md into per-scope reference files.

Reads references/commands.md (the `tornix skill generate` dump) and writes:
  references/scopes/core.md          — top-level commands (auth, config, data, projects, tasks, ...)
  references/scopes/<tag>.md         — one file per `tornix api <tag>` scope
  references/commands.md            — replaced with a compact INDEX (scope -> file -> when to use)
"""
import os
import re
from collections import OrderedDict

from tornix_cli.skillgen import agent_command_allowed

SRC = os.path.expanduser('~/.hermes/skills/tornix/references/commands.md')
OUT_DIR = os.path.expanduser('~/.hermes/skills/tornix/references/scopes')

API_RE = re.compile(r'^- `tornix api ([a-z0-9-]+) ([a-z0-9-]+) --json` — (.*)$')
TOP_RE = re.compile(r'^- `tornix ([a-z0-9-]+)(?: [a-z0-9-]+)* --json` — (.*)$')
RESTRICTED_API_SCOPES = {
    'auth': 'Authentication, recovery, password, OTP, and device-session operations are user-controlled.',
    'api-keys': 'API key lifecycle is user-controlled; raw key material must never be exposed to the agent.',
}
INDEX_MARKER = '<!-- split-skill-scopes-index -->'


def render_core(core):
    lines = [
        '# Core commands (top-level)',
        '',
        'Top-level `tornix` commands — auth, config, data proxy, projects, tasks, file, meetings, deep-research.',
        '',
        '> **Profile-scoped config:** on multi-profile hosts, use `HERMES_HOME` or an explicit',
        '> profile-specific `TORNIX_CONFIG`; never use a shared/default config. Stop if neither is available.',
        '> **Caller and organization safety:** before the first data request in each session, run',
        '> `tornix auth whoami --json` and `tornix config show --json`; list memberships with',
        '> `tornix api organizations list --json`. Verify a configured `org_id` is in those memberships.',
        '> If it is absent, use only one explicit profile-to-org mapping and verify that membership;',
        '> if none or ambiguous, stop; never guess or choose the first org.',
        '> `whoami` is the only allowed `tornix auth` command. Never invoke login/logout/keys.',
        '> Password-bearing account creation, password reset, account and connected-mailbox deletion, and import commands are human-only and withheld;',
        '> never pass passwords via command options or `--data`.',
        '> `config show` is safe (it reveals `has_key`, not the key); never inspect raw config files or `.env`.',
        '',
    ]
    allowed_core = [(cmd, desc) for cmd, desc in core if agent_command_allowed(cmd)]
    lines.extend(f'- `{cmd} --json` — {desc}' for cmd, desc in allowed_core)
    lines.extend(['', f'({len(allowed_core)} available commands; auth and credential lifecycle operations withheld)', ''])
    return '\n'.join(lines)


def _agent_ops(tag, ops):
    return [(op, desc) for op, desc in ops if agent_command_allowed(f'tornix api {tag} {op}')]


def render_scope(tag, ops):
    if tag == 'auth':
        return '\n'.join([
            '# Restricted scope: `tornix api auth`',
            '',
            '> **Restricted:** Do not invoke any `tornix api auth …` command from the agent.',
            '> This scope includes login, OTP/recovery, user/password changes, and device-session operations.',
            '> For identity validation use only `tornix auth whoami --json`; credential and session changes are user-controlled.',
            '',
        ])
    if tag == 'api-keys':
        return '\n'.join([
            '# Restricted scope: `tornix api api-keys`',
            '',
            '> **Restricted:** API key lifecycle is user-controlled. Do not list, inspect, create, update, revoke, or delete keys from the agent.',
            '> API-key creation can reveal a raw key only once. Never copy, print, store, or transmit key secrets.',
            '',
        ])
    visible_ops = _agent_ops(tag, ops)
    if not visible_ops:
        return '\n'.join([
            f'# Restricted scope: `tornix api {tag}`',
            '',
            '> **Restricted:** This scope contains only human-operated credential or password actions.',
            '',
        ])
    lines = [f'# `tornix api {tag}` — {len(visible_ops)} commands', '']
    lines.extend(f'- `tornix api {tag} {op} --json` — {desc}' for op, desc in visible_ops)
    lines.extend(['', f'({len(visible_ops)} commands)', ''])
    return '\n'.join(lines)


def render_index(scopes, core):
    lines = [
        INDEX_MARKER,
        '',
        '# Tornix command reference — modular index',
        '',
        'Commands are split per backend scope. Load ONLY the file matching your task '
        '(via skill_view file_path) — do not load the whole tree.',
        '',
        '## Core (top-level)',
        '- `references/scopes/core.md` — config, data proxy, projects, tasks, file, meetings, deep-research, rpc, catalog, skill',
        '',
        '## API scopes (one file per tag)',
        '| Scope | File | # | Use when |',
        '|---|---|---:|---|',
    ]
    tags = list(scopes)
    for restricted_tag in RESTRICTED_API_SCOPES:
        if restricted_tag not in tags:
            tags.append(restricted_tag)
    for tag in tags:
        visible_ops = _agent_ops(tag, scopes.get(tag, []))
        if tag in RESTRICTED_API_SCOPES:
            hint = RESTRICTED_API_SCOPES[tag]
            lines.append(f'| {tag} | `references/scopes/{tag}.md` | Restricted | {hint} |')
            continue
        if not visible_ops:
            lines.append(
                f'| {tag} | `references/scopes/{tag}.md` | Restricted | '
                'Credential or password actions are user-controlled. |'
            )
            continue
        first_desc = visible_ops[0][1].strip()
        hint = first_desc.split('.')[0].split(' — ')[0][:70]
        lines.append(f'| {tag} | `references/scopes/{tag}.md` | {len(visible_ops)} | {hint} |')
    api_count = sum(
        len(_agent_ops(tag, ops))
        for tag, ops in scopes.items()
        if tag not in RESTRICTED_API_SCOPES
    )
    core_count = sum(1 for cmd, _ in core if agent_command_allowed(cmd))
    scope_count = sum(
        1 for tag in tags
        if tag not in RESTRICTED_API_SCOPES and _agent_ops(tag, scopes.get(tag, []))
    )
    lines.append(
        f'\nAvailable to agents: {api_count} API commands + {core_count} core commands '
        f'across {scope_count} API scopes; authentication, API-key, password-bearing, and account/mailbox deletion operations are withheld.'
    )
    return '\n'.join(lines) + '\n'


def main(src=SRC, out_dir=OUT_DIR):
    source = open(src, encoding='utf-8').read()
    if INDEX_MARKER in source:
        print(f'index already split; unchanged: {src}')
        return
    lines = source.splitlines()
    scopes = OrderedDict()   # tag -> list of (op, desc)
    core = []                # list of (cmd, desc)
    for ln in lines:
        m = API_RE.match(ln)
        if m:
            tag, op, desc = m.group(1), m.group(2), m.group(3)
            scopes.setdefault(tag, []).append((op, desc))
            continue
        m = TOP_RE.match(ln)
        if m:
            # extract the full command between backticks, drop the --json flag
            cmd = ln.split('`')[1].replace(' --json', '').strip()
            core.append((cmd, m.group(2)))

    os.makedirs(out_dir, exist_ok=True)

    # --- core.md: top-level commands ---
    with open(os.path.join(out_dir, 'core.md'), 'w', encoding='utf-8') as f:
        f.write(render_core(core))

    # --- per-scope files; sensitive scopes are always written as policy-only refs ---
    tags = list(scopes)
    for restricted_tag in RESTRICTED_API_SCOPES:
        if restricted_tag not in tags:
            tags.append(restricted_tag)
    for tag in tags:
        with open(os.path.join(out_dir, f'{tag}.md'), 'w', encoding='utf-8') as f:
            f.write(render_scope(tag, scopes.get(tag, [])))

    # --- index (replaces the full command dump) ---
    with open(src, 'w', encoding='utf-8') as f:
        f.write(render_index(scopes, core))

    available_core = sum(1 for cmd, _ in core if agent_command_allowed(cmd))
    print(f'core: {available_core}/{len(core)} agent commands -> scopes/core.md')
    for tag in tags:
        visible_ops = _agent_ops(tag, scopes.get(tag, []))
        if tag in RESTRICTED_API_SCOPES or not visible_ops:
            print(f'{tag}: restricted policy reference -> scopes/{tag}.md')
        else:
            print(f'{tag}: {len(visible_ops)}/{len(scopes[tag])} agent commands -> scopes/{tag}.md')
    print(f'index written to {src}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src', default=SRC, help='Generated commands markdown input/output path')
    parser.add_argument('--out-dir', default=OUT_DIR, help='Per-scope output directory')
    args = parser.parse_args()
    main(args.src, args.out_dir)
