from __future__ import annotations

import sys

import click

from .api_gen import build_api_group
from .auth import auth_group
from .catalog import catalog_command
from .client import TornixClient
from .commands.approvals import approvals_group
from .commands.deep_research import deep_research_command
from .commands.meetings import meetings_group
from .commands.projects import projects_group
from .commands.tasks import tasks_group
from .config import PROFILES, Config
from .data import data_group, rpc_command
from .errors import EXIT, TornixError
from .output import add_json_option, emit, emit_error
from .repl import run_repl
from .spec import fetch_spec, load_spec


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Machine-readable JSON output.")
@click.option("--profile", default=None, help="Config profile (prod|stage).")
@click.option("--org", default=None, help="Organization id (X-Organization-ID).")
@click.version_option()
@click.pass_context
def cli(ctx: click.Context, json_mode: bool, profile: str | None, org: str | None) -> None:
    """Tornix CLI — agent-native interface for app.tornix.ai."""
    cfg = Config.load()
    if profile:
        cfg.profile = profile
        cfg.api_url = PROFILES.get(profile, cfg.api_url)
    if org:
        cfg.org_id = org
    ctx.obj = {"config": cfg, "client": TornixClient(cfg), "json": json_mode}
    if ctx.invoked_subcommand is None:
        run_repl(cli, ctx.obj)


@cli.group(name="config", help="Manage configuration.")
def config_group() -> None:
    pass


@config_group.command("show")
@click.pass_obj
def config_show(obj):
    c: Config = obj["config"]
    emit({"profile": c.profile, "api_url": c.api_url, "org_id": c.org_id,
          "has_key": bool(c.api_key)}, json_mode=obj.get("json"))


@config_group.command("org")
@click.argument("org_id")
@click.pass_obj
def config_org(obj, org_id):
    c: Config = obj["config"]
    c.org_id = org_id
    c.save()
    emit({"org_id": org_id}, json_mode=obj.get("json"))


@cli.command("gen", help="Refresh the pinned OpenAPI snapshot from a backend.")
@click.option("--from", "src", default=None, help="Base URL (defaults to active profile).")
@click.pass_obj
def gen(obj, src):
    import json
    from pathlib import Path
    base = src or obj["config"].api_url
    spec = fetch_spec(base)
    path = Path(__file__).parent / "generated" / "_spec.json"
    path.write_text(json.dumps(spec))
    emit({"refreshed": True, "paths": len(spec.get("paths", {}))}, json_mode=obj.get("json"))


@cli.command("skill")
@click.argument("action", type=click.Choice(["generate"]))
@click.pass_context
def skill(ctx, action):
    from pathlib import Path

    from .catalog import _describe
    from .skillgen import render_skill

    catalog = _describe(ctx.find_root().command, "tornix")
    out = Path(__file__).resolve().parent.parent / "skills" / "tornix" / "SKILL.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_skill(catalog))
    emit({"written": str(out)}, json_mode=(ctx.obj or {}).get("json", True))


# Assemble layers
cli.add_command(auth_group)
cli.add_command(catalog_command)
cli.add_command(data_group)
cli.add_command(rpc_command)
cli.add_command(deep_research_command)
cli.add_command(projects_group)
cli.add_command(tasks_group)
cli.add_command(approvals_group)
cli.add_command(meetings_group)
cli.add_command(build_api_group(load_spec()))

# Uniform `--json` on every subcommand (works before or after the subcommand).
add_json_option(cli)


def main() -> None:
    try:
        cli(standalone_mode=False)
    except TornixError as e:
        sys.exit(emit_error(e, json_mode="--json" in sys.argv))
    except click.ClickException as e:
        e.show()
        sys.exit(EXIT.USAGE)
    except click.exceptions.Abort:
        sys.exit(EXIT.GENERIC)


if __name__ == "__main__":
    main()
