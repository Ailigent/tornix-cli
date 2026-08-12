#!/usr/bin/env python3
"""Split the generated commands.md into per-scope reference files.

Reads references/commands.md (the `tornix skill generate` dump) and writes:
  references/scopes/core.md          — top-level commands (auth, config, data, projects, tasks, ...)
  references/scopes/<tag>.md         — one file per `tornix api <tag>` scope
  references/commands.md            — replaced with a compact INDEX (scope -> file -> when to use)
"""
import re, sys, os
from collections import OrderedDict

SRC = os.path.expanduser('~/.hermes/skills/tornix/references/commands.md')
OUT_DIR = os.path.expanduser('~/.hermes/skills/tornix/references/scopes')

API_RE = re.compile(r'^- `tornix api ([a-z0-9-]+) ([a-z0-9-]+) --json` — (.*)$')
TOP_RE = re.compile(r'^- `tornix ([a-z0-9-]+)(?: [a-z0-9-]+)* --json` — (.*)$')

def main():
    lines = open(SRC, encoding='utf-8').read().splitlines()
    scopes = OrderedDict()   # tag -> list of (op, desc)
    core = []                # list of (cmd, desc)
    header = []
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
            continue
        header.append(ln)

    os.makedirs(OUT_DIR, exist_ok=True)

    # --- core.md: top-level commands ---
    with open(os.path.join(OUT_DIR, 'core.md'), 'w', encoding='utf-8') as f:
        f.write('# Core commands (top-level)\n\n')
        f.write('Top-level `tornix` commands — auth, config, data proxy, projects, tasks, file, meetings, deep-research.\n\n')
        for cmd, desc in core:
            f.write(f'- `{cmd} --json` — {desc}\n')
        f.write(f'\n({len(core)} commands)\n')

    # --- per-scope files ---
    for tag, ops in scopes.items():
        with open(os.path.join(OUT_DIR, f'{tag}.md'), 'w', encoding='utf-8') as f:
            f.write(f'# `tornix api {tag}` — {len(ops)} commands\n\n')
            for op, desc in ops:
                f.write(f'- `tornix api {tag} {op} --json` — {desc}\n')
            f.write(f'\n({len(ops)} commands)\n')

    # --- index (replaces commands.md) ---
    with open(SRC, 'w', encoding='utf-8') as f:
        f.write('# Tornix command reference — modular index\n\n')
        f.write('Commands are split per backend scope. Load ONLY the file matching your task '
                '(via skill_view file_path) — do not load the whole tree.\n\n')
        f.write('## Core (top-level)\n')
        f.write('- `references/scopes/core.md` — auth, config, data proxy, projects, tasks, file, meetings, deep-research, rpc, catalog, skill\n\n')
        f.write('## API scopes (one file per tag)\n')
        f.write('| Scope | File | # | Use when |\n|---|---|---:|---|\n')
        for tag, ops in scopes.items():
            first_desc = ops[0][1].strip()
            # shorten the "use when" hint to the first sentence
            hint = first_desc.split('.')[0].split(' — ')[0][:70]
            f.write(f'| {tag} | `references/scopes/{tag}.md` | {len(ops)} | {hint} |\n')
        f.write(f'\nTotal: {sum(len(v) for v in scopes.values())} api commands + {len(core)} core commands across {len(scopes)} scopes.\n')

    print(f'core: {len(core)} commands -> scopes/core.md')
    for tag, ops in scopes.items():
        print(f'{tag}: {len(ops)} -> scopes/{tag}.md')
    print(f'index written to {SRC}')

if __name__ == '__main__':
    main()
