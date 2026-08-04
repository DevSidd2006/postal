from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from config.config import Config
from ui.components import LOGO_WIDTH, POSTAL_VERSION, Gutter, logo

WELCOME_TITLE = "Welcome to postal!"
HELP_TITLE = 'Use /help for commands'

BANNER_MIN_WIDTH = 2 + 2 + LOGO_WIDTH + 2 + len(WELCOME_TITLE)

KEY_HINTS = "ctrl+o expands tool output · ctrl+c interrupts · ctrl+d quits"


def _tilde(path: str) -> str:
    home = str(Path.home())
    return f"~{path[len(home):]}" if path.startswith(home) else path


def facts(config: Config) -> list[tuple[str, str]]:
    policy = config.approval
    rows = [
        ("Directory", _tilde(str(config.cwd))),
        ("Model", config.model_name),
        ("Approval", f"{policy.label}"),
        ("Version", POSTAL_VERSION),
    ]
    return [(label, value) for label, value in rows if value]


def render_banner(console: Console, config: Config) -> None:
    welcome = Table.grid(padding=(0, 0))
    welcome.add_row(Text(WELCOME_TITLE, style="highlight"))
    welcome.add_row(Text(HELP_TITLE, style="muted"))

    head = Table.grid(padding=(0, 2))
    head.add_column(vertical="middle")
    head.add_column(vertical="middle")
    head.add_row(logo(), welcome)

    table = Table.grid(padding=(0, 1))
    table.add_column(style="muted")
    table.add_column(style="subtitle")
    for label, value in facts(config):
        table.add_row(f"{label}:", value)

    console.print()
    if console.width >= BANNER_MIN_WIDTH:
        body = Table.grid(padding=(0, 0))
        body.add_row(head)
        body.add_row(Text())
        body.add_row(table)
        console.print(Gutter(body, style="border"))
    else:
        console.print(Text("postal", style="highlight"))
        console.print(table)
    console.print()
    console.print(Text(KEY_HINTS, style="border"))
