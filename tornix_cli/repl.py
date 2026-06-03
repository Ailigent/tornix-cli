from __future__ import annotations

import shlex

import click

BANNER = r"""
  ████████╗ ██████╗ ██████╗ ███╗   ██╗██╗██╗  ██╗
     ██║   ██║   ██║██╔══██╗████╗  ██║██║ ╚███╔╝
     ██║   ██║   ██║██████╔╝██╔██╗ ██║██║ ██╔██╗
     ██║   ╚██████╔╝██║  ██║██║ ╚████║██║██╔╝ ██╗
  Tornix CLI · REPL — type `help`, `exit` to quit.
"""


def parse_line(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    return shlex.split(line)


def run_repl(cli: click.Group, obj: dict) -> None:
    try:
        import readline  # noqa: F401  (enables history/editing)
    except Exception:
        pass
    click.echo(BANNER)
    while True:
        try:
            line = input("tornix> ")
        except (EOFError, KeyboardInterrupt):
            click.echo()
            return
        args = parse_line(line)
        if not args:
            continue
        if args[0] in ("exit", "quit"):
            return
        try:
            cli.main(args=args, obj=obj, standalone_mode=False)
        except click.ClickException as e:
            e.show()
        except SystemExit:
            pass
        except Exception as e:  # keep the REPL alive
            click.secho(f"error: {e}", fg="red")
