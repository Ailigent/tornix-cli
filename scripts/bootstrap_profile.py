#!/usr/bin/env python3
"""Bootstrap a Tornix skill profile for the current CLI user.

Run: python3 scripts/bootstrap_profile.py [--out profiles/<email>.md]
Discovers: whoami (user id/email), orgs, projects, team members of the default
project — then writes a profile file from profiles/_template.md.
"""
import json, os, subprocess, sys, datetime

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"WARN: {' '.join(cmd)} failed: {r.stderr[:200]}", file=sys.stderr)
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None

def main():
    who = run(['tornix', 'auth', 'whoami', '--json'])
    if not who or not who.get('id'):
        print("ERROR: not authenticated. Run `tornix auth login` first.", file=sys.stderr)
        sys.exit(1)

    email = who.get('email') or who.get('id')
    uid = who['id']
    print(f"User: {email} ({uid})")

    orgs = run(['tornix', 'api', 'organizations', 'list', '--json']) or []
    print(f"Orgs ({len(orgs)}):")
    for o in orgs:
        print(f"  - {o.get('name')} ({o.get('id')})")

    projects = run(['tornix', 'projects', 'list', '--json']) or []
    print(f"Projects ({len(projects)}):")
    for p in projects[:15]:
        print(f"  - {p.get('name')} ({p.get('project_id')})")

    # pick default project: first one, or ask
    default = None
    if projects:
        default = projects[0]
        print(f"\nDefault project candidate: {default.get('name')} ({default.get('project_id')})")
        print("(edit the profile to change it)")

    # team members of the default project
    team = []
    if default:
        members = run(['tornix', 'api', 'projects', 'members', default['project_id'], '--json']) or []
        for m in members:
            team.append((m.get('user_id'), m.get('job_title_role_id')))

    out = "profiles/<email>.md"
    args = sys.argv[1:]
    if args and args[0] == '--out' and len(args) > 1:
        out = args[1]
    elif args:
        out = args[0]
    if out == "profiles/<email>.md":
        out = f"profiles/{email}.md"
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    default_id = default.get('project_id') if default else '?'
    default_name = default.get('name') if default else '?'
    org_name = orgs[0].get('name') if orgs else '?'
    org_id = orgs[0].get('id') if orgs else '?'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f"""---
user: {email}
user_id: {uid}
org: {org_name} ({org_id})
default_project: {default_name} ({default_id})
language: <language>
---

# Profile: {email}

## Identity
- user id: `{uid}`
- org: {org_name} `{org_id}`
- default project: {default_name} `{default_id}`

## Team (default project members)
| Member | user id | role id |
|---|---|---|
""")
        for uid2, rid in team:
            f.write(f"| <name> | `{uid2}` | `{rid}` |\n")
        f.write(f"""
## Conventions
- Language: <language>
- Default project = {default_name} when none named.
- <user-specific rules>

---
Generated {datetime.date.today().isoformat()} by scripts/bootstrap_profile.py.
""")
    print(f"\nProfile written: {out}")
    print("Fill in member names + language + conventions, then confirm the default project.")

if __name__ == '__main__':
    main()
