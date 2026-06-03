from __future__ import annotations

import click


@click.group()
@click.version_option()
def cli() -> None:
    """Tornix CLI — agent-native interface for app.tornix.ai."""


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
